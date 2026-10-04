"""
面试流程图节点实现

每个节点接收 InterviewState，返回部分状态更新。
错误处理在节点内部完成（降级/兜底），不依赖图的条件路由。
"""

import json
import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.interview import Interview
from app.models.interview_message import InterviewMessage
from app.models.resume import Resume
from app.services.client.ai_service import AIService
from app.utils.utils import safe_parse_json

logger = logging.getLogger(__name__)


def _get_question_text(questions: list, index: int) -> str | None:
    if index < 0 or index >= len(questions):
        return None
    item = questions[index]
    if isinstance(item, dict):
        text = item.get("question")
    else:
        text = str(item)
    return text.strip() if isinstance(text, str) and text.strip() else None


# ---------------------------------------------------------------------------
# 节点 1：加载上下文
# ---------------------------------------------------------------------------

async def load_context_node(state: dict) -> dict:
    """从 DB 加载面试上下文（简历/面经 + 对话历史 + 题目列表）"""
    db: AsyncSession = state["db"]
    interview_id = state["interview_id"]

    interview = await db.get(Interview, interview_id)
    if not interview:
        return {"error": "面试记录不存在"}

# 获取上下文（简历或面经）
    parsed_resume = {}
    resume_id = None
    experience_id = None

    if interview.resume_id:
        resume_query = select(Resume).where(Resume.id == interview.resume_id)
        resume_result = await db.execute(resume_query)
        resume = resume_result.scalar_one_or_none()
        if not resume:
            return {"error": "简历不存在或已删除"}
        parsed_resume = safe_parse_json(resume.parsed_content, {})
        resume_id = interview.resume_id
    elif interview.experience_id:
        from app.models.experience import Experience
        exp = await db.get(Experience, interview.experience_id)
        if exp:
            parsed_resume = {"summary": f"面经：{exp.title}", "skills": [exp.company, exp.position]}
            experience_id = interview.experience_id

    # 获取对话历史（长期记忆：外部化于 DB，按面试归属查询防越权）
    msg_query = select(InterviewMessage).where(
        InterviewMessage.interview_id == interview_id
    ).order_by(InterviewMessage.id)
    msg_result = await db.execute(msg_query)
    messages = msg_result.scalars().all()
    chat_history = [{"role": m.role, "content": m.content} for m in messages]

    # 会话记忆压缩（记忆压缩）：历史过长时，对较早部分做 LLM 摘要，
    # 仅保留近期若干轮原文，控制注入 prompt 的 token 量。
    history_summary = None
    RECENT_KEEP = 4
    if len(chat_history) > settings.AI_MEMORY_SUMMARY_THRESHOLD:
        older = chat_history[:-RECENT_KEEP]
        recent = chat_history[-RECENT_KEEP:]
        try:
            history_summary = await AIService.summarize_history(older)
        except Exception as e:
            logger.warning(f"[load_context] 历史摘要失败，退回完整历史: {e}")
            recent = chat_history
        chat_history = recent

    # 当前题目
    current_index = interview.current_question_index or 0
    questions = interview.questions_data or []
    if not isinstance(questions, list):
        return {"error": "面试题目数据异常，请重新开始面试"}
    current_question = _get_question_text(questions, current_index)
    if current_question is None:
        return {"error": "面试题目数据异常，请重新开始面试"}

    return {
        "current_question": current_question,
        "parsed_resume": parsed_resume,
        "chat_history": chat_history,
        "history_summary": history_summary,
        "questions": questions,
        "current_index": current_index,
        "target_position": interview.target_position,
        "resume_id": resume_id,
        "experience_id": experience_id,
    }


# ---------------------------------------------------------------------------
# 节点 2：评估回答
# ---------------------------------------------------------------------------

async def evaluate_node(state: dict) -> dict:
    """评估候选人回答，带三级容错 + 流式输出"""
    import asyncio
    import re

    # 如果上游已出错，短路跳过
    if state.get("error"):
        return {"score": 0.0, "feedback": "", "evaluation": {}}

    answer = state["answer"]
    current_question = state["current_question"]
    parsed_resume = state["parsed_resume"]
    chat_history = state["chat_history"]
    chunk_queue = state.get("chunk_queue")  # 可选：用于流式输出

    # 评分语义统一交给 AI 按提示词判断：坦诚跳过给 4-5 / 2-3 分等分档规则
    # 已写入 EVALUATE_STREAM_SYSTEM。此处刻意不做关键词预判——正常技术回答里的
    # “不会 / 跳过 / 不清楚”会被子串匹配误判成坦诚跳过，直接给 4 分且完全不调用 AI。

    # Level 1: 尝试流式 AI 评估
    last_error = None
    try:
        full_text = ""
        async for chunk in AIService.evaluate_answer_stream(
            question=current_question,
            answer=answer,
            resume_context=parsed_resume,
            chat_history=chat_history,
            history_summary=state.get("history_summary"),
        ):
            full_text += chunk
            # 实时把 LLM token 推到队列，供外层 SSE 流式输出
            if chunk_queue:
                await chunk_queue.put(chunk)

        # 从流式文本中提取评分
        feedback = full_text.strip()
        json_match = re.search(r'\{[^}]*"score"\s*:\s*([\d.]+)[^}]*\}', full_text)
        score = 5.0
        if json_match:
            try:
                score = float(json_match.group(1))
                feedback = re.sub(r'```json\s*\{[^}]*\}\s*```', '', feedback).strip()
                feedback = re.sub(r'\{[^}]*"score"[^}]*\}', '', feedback).strip()
            except (ValueError, IndexError):
                pass

        score = AIService.post_process_score(score, answer)
        return {
            "evaluation": {"score": score, "feedback": feedback, "follow_up": False},
            "score": score,
            "feedback": feedback,
        }
    except Exception as e:
        last_error = str(e)
        logger.warning(f"[evaluate_node] AI 评估失败: {e}")

    # Level 2-3: 共享降级逻辑
    fallback_result = AIService._fallback_evaluate(answer)
    if chunk_queue:
        await chunk_queue.put(fallback_result["feedback"])
    return {
        "evaluation": {
            "score": fallback_result["score"],
            "feedback": fallback_result["feedback"],
            "follow_up": False,
            "fallback": True,
            "error": last_error,
        },
        "score": fallback_result["score"],
        "feedback": fallback_result["feedback"],
        "skip_type": fallback_result.get("skip_type"),
    }


# ---------------------------------------------------------------------------
# 节点 3：生成下一题 / 标记完成
# ---------------------------------------------------------------------------

async def generate_next_node(state: dict) -> dict:
    """判断是否最后一题，生成下一题或标记面试结束"""
    if state.get("error"):
        return {"is_finished": False, "next_question": None}

    current_index = state["current_index"]
    questions = state["questions"]

    next_index = current_index + 1
    is_finished = next_index >= len(questions)

    if is_finished:
        return {
            "is_finished": True,
            "next_question": None,
            "overall_score": 0.0,  # 由 save_results 计算
        }
    else:
        return {
            "is_finished": False,
            "next_question": _get_question_text(questions, next_index),
        }


# ---------------------------------------------------------------------------
# 节点 4：保存结果到 DB
# ---------------------------------------------------------------------------

async def save_results_node(state: dict) -> dict:
    """保存评估结果、推进面试进度、生成报告、发送通知"""
    # 如果上游已出错，返回错误结果
    if state.get("error"):
        return {"result": {"error": state["error"]}}

    db: AsyncSession = state["db"]
    interview_id = state["interview_id"]
    user_id = state["user_id"]
    current_index = state["current_index"]
    is_finished = state["is_finished"]
    score = state["score"]
    feedback = state["feedback"]
    questions = state["questions"]
    answer = state["answer"]

    # 幂等守卫：同一题（interview_id + question_index）已存在评分则跳过写入，
    # 避免网络重试导致的重复存分、重复生成报告。
    # 依赖 thread_id + 检查点确保断点续传只续跑未完成节点；此处兜底防止重复提交。
    idem_query = select(InterviewMessage).where(
        InterviewMessage.interview_id == interview_id,
        InterviewMessage.role == "candidate",
        InterviewMessage.question_index == current_index,
    )
    idem_result = await db.execute(idem_query)
    existing = idem_result.scalar_one_or_none()
    if existing:
        logger.warning(
            f"[save_results] 幂等跳过：第 {current_index} 题已存在评分，"
            f"避免重复写入（score={existing.score}）"
        )
        return {
            "result": {
                "score": float(existing.score) if existing.score is not None else 0.0,
                "feedback": existing.feedback or "",
                "question_index": current_index,
                "is_finished": is_finished,
                "next_question": state.get("next_question"),
                "idempotent": True,
            },
            "overall_score": 0.0,
        }

    interview = await db.get(Interview, interview_id)
    if not interview:
        return {"result": {"error": "面试记录不存在"}}

    duplicate_result = await _get_existing_answer_result(
        db=db,
        interview=interview,
        question_index=current_index,
        answer=answer,
        questions=questions,
    )
    if duplicate_result:
        return {"result": duplicate_result, "overall_score": duplicate_result.get("overall_score", 0.0)}

    if interview.current_question_index != current_index:
        return {"result": {"error": "面试进度已更新，请刷新后继续"}}

    next_question = None
    if not is_finished:
        next_question = _get_question_text(questions, current_index + 1)
        if next_question is None:
            return {"result": {"error": "面试题目数据异常，请重新开始面试"}}

    # 保存候选人回答
    # feedback 字段为 Text 无长度限制，保留完整评语（此前截断 200 字会导致
    # 前端重新拉取历史时评语残缺；评语是面试官对本题的核心反馈，必须完整）。
    candidate_msg = InterviewMessage(
        interview_id=interview_id,
        role="candidate",
        content=answer,
        question_index=current_index,
        score=Decimal(str(score)),
        feedback=feedback,
    )
    db.add(candidate_msg)

    overall_score = 0.0

    if is_finished:
        # 面试结束
        interview.status = "completed"
        interview.current_question_index = current_index + 1

        # 计算加权平均分
        score_query = select(InterviewMessage).where(
            InterviewMessage.interview_id == interview_id,
            InterviewMessage.role == "candidate",
            InterviewMessage.score.isnot(None),
        )
        score_result = await db.execute(score_query)
        scored_msgs = score_result.scalars().all()
        answers_by_index = {}
        for msg in scored_msgs:
            if msg.question_index is None or msg.score is None:
                continue
            answers_by_index[int(msg.question_index)] = {
                "answer": msg.content,
                "score": float(msg.score),
                "feedback": msg.feedback or "",
            }

        # 当前回答还未 commit，显式写入映射，避免报告漏掉最后一题或依赖 autoflush。
        answers_by_index[current_index] = {
            "answer": answer,
            "score": float(score),
            "feedback": feedback,
        }

        all_scores = [item["score"] for item in answers_by_index.values()]

        overall_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
        interview.overall_score = Decimal(str(overall_score))

        # 生成评估报告
        qa_data = []
        for i, q in enumerate(questions):
            question_text = q.get("question", str(q)) if isinstance(q, dict) else str(q)
            answer_info = answers_by_index.get(i)
            qa_data.append({
                "question": question_text,
                "answer": answer_info["answer"] if answer_info else "未回答",
                "score": answer_info["score"] if answer_info else 0,
                "feedback": answer_info["feedback"] if answer_info else "",
            })

        try:
            report = await AIService.generate_report(
                parsed_resume=state["parsed_resume"],
                target_position=state["target_position"],
                questions_and_scores=qa_data,
            )
            report["question_scores"] = [
                {"question": qa["question"], "score": qa["score"], "feedback": qa.get("feedback", "")}
                for qa in qa_data
            ]
            interview.report = json.dumps(report, ensure_ascii=False)
        except Exception as e:
            logger.error(f"报告生成失败: {e}")
            interview.report = json.dumps(
                {"summary": "报告生成失败", "strengths": [], "weaknesses": [], "suggestions": []}
            )
    else:
        # 进入下一题
        interview.current_question_index = current_index + 1

        # 保存下一题作为面试官消息
        interviewer_msg = InterviewMessage(
            interview_id=interview_id,
            role="interviewer",
            content=next_question,
            question_index=current_index + 1,
        )
        db.add(interviewer_msg)

    await db.commit()

    # 面试完成通知
    if is_finished:
        try:
            from app.services.client.notification_service import notification_service
            await notification_service.enqueue_notification(
                db=db,
                user_id=user_id,
                title="面试已完成",
                content=f"你的「{state['target_position']}」面试已结束，得分 {overall_score} 分，点击查看报告",
                notification_type="interview",
                related_id=interview_id,
                related_type="interview",
            )
        except Exception as e:
            logger.warning(f"发送面试完成通知失败: {e}")

        # 面试结果回流：自动生成学习笔记草稿（review 复盘类型）
        # 失败不影响主流程，仅记录警告
        try:
            from app.services.client.learning_note_service import learning_note_service
            await learning_note_service.generate_from_interview(
                db=db,
                user_id=user_id,
                interview_id=interview_id,
                note_type="review",
                title=f"{state['target_position']} 面试复盘",
                visibility="private",
            )
        except Exception as e:
            logger.warning(f"自动生成学习笔记草稿失败: {e}")

        # 错题本仪表盘：记录本次面试报告中的薄弱点。
        try:
            from app.services.client.weakness_service import weakness_service
            await weakness_service.record_from_interview(
                db=db,
                user_id=user_id,
                interview_id=interview_id,
            )
        except Exception as e:
            logger.warning(f"记录薄弱点统计失败: {e}")

    # 组装最终结果
    result = {
        "score": score,
        "feedback": feedback,
        "question_index": current_index,
        "is_finished": is_finished,
        "next_question": state.get("next_question"),
    }
    if is_finished:
        result["overall_score"] = overall_score

    return {"result": result, "overall_score": overall_score}


async def _get_existing_answer_result(
    db: AsyncSession,
    interview: Interview,
    question_index: int,
    answer: str,
    questions: list,
) -> dict | None:
    result = await db.execute(
        select(InterviewMessage)
        .where(
            InterviewMessage.interview_id == interview.id,
            InterviewMessage.role == "candidate",
            InterviewMessage.question_index == question_index,
        )
        .order_by(InterviewMessage.id.desc())
        .limit(1)
    )
    message = result.scalars().first()
    if not message or message.content != answer:
        return None

    current_index = interview.current_question_index or 0
    is_finished = interview.status == "completed" or current_index >= len(questions)
    duplicate = {
        "score": float(message.score) if message.score is not None else 0.0,
        "feedback": message.feedback or "",
        "question_index": question_index,
        "is_finished": is_finished,
        "next_question": None if is_finished else _get_question_text(questions, current_index),
        "idempotent": True,
    }
    if is_finished:
        duplicate["overall_score"] = float(interview.overall_score or 0)
    return duplicate
