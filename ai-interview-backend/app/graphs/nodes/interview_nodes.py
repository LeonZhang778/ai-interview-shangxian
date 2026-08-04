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

from app.models.interview import Interview
from app.models.interview_message import InterviewMessage
from app.models.resume import Resume
from app.services.client.ai_service import AIService
from app.utils.utils import safe_parse_json

logger = logging.getLogger(__name__)


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
        parsed_resume = safe_parse_json(resume.parsed_content, {})
        resume_id = interview.resume_id
    elif interview.experience_id:
        from app.models.experience import Experience
        exp = await db.get(Experience, interview.experience_id)
        if exp:
            parsed_resume = {"summary": f"面经：{exp.title}", "skills": [exp.company, exp.position]}
            experience_id = interview.experience_id

    # 获取对话历史
    msg_query = select(InterviewMessage).where(
        InterviewMessage.interview_id == interview_id
    ).order_by(InterviewMessage.id)
    msg_result = await db.execute(msg_query)
    messages = msg_result.scalars().all()
    chat_history = [{"role": m.role, "content": m.content} for m in messages]

    # 当前题目
    current_index = interview.current_question_index
    questions = interview.questions_data
    current_question = questions[current_index]["question"]

    return {
        "current_question": current_question,
        "parsed_resume": parsed_resume,
        "chat_history": chat_history,
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

    # Level 0: 低质量/坦诚跳过回答直接基础评分，避免浪费 AI 调用
    pre_result = AIService.pre_score(answer)
    if pre_result is not None:
        score, skip_type = pre_result
        feedback = AIService.pre_score_feedback(skip_type)
        if chunk_queue:
            await chunk_queue.put(feedback)
        return {
            "evaluation": {"score": score, "feedback": feedback, "follow_up": False, "pre_scored": True},
            "score": score,
            "feedback": feedback,
            "skip_type": skip_type,
        }

    # Level 1: 尝试流式 AI 评估
    last_error = None
    try:
        full_text = ""
        async for chunk in AIService.evaluate_answer_stream(
            question=current_question,
            answer=answer,
            resume_context=parsed_resume,
            chat_history=chat_history,
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
            "next_question": questions[next_index]["question"],
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

    interview = await db.get(Interview, interview_id)

    # 保存候选人回答
    candidate_msg = InterviewMessage(
        interview_id=interview_id,
        role="candidate",
        content=answer,
        question_index=current_index,
        score=Decimal(str(score)),
        feedback=feedback[:200],
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
        next_question = questions[current_index + 1]["question"]

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
            await notification_service.create_notification(
                db=db,
                user_id=user_id,
                title="面试已完成",
                content=f"你的「{state['target_position']}」面试已结束，得分 {overall_score} 分，点击查看报告",
                notification_type="interview",
                related_id=interview_id,
                related_type="interview",
                commit=False,
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
