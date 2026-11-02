"""
面试流程图节点实现

每个节点接收 InterviewState，返回部分状态更新。
错误处理在节点内部完成（降级/兜底），不依赖图的条件路由。
"""

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.interview import Interview
from app.models.interview_message import InterviewMessage
from app.models.resume import Resume
from app.services.client.ai_service import AIService
from app.services.client.evaluation_service import DEFAULT_RUBRIC, evaluation_service
from app.services.client.interview_report_service import interview_report_service
from app.services.common.interview_metrics import interview_metrics
from app.utils.utils import safe_parse_json

logger = logging.getLogger(__name__)


def _runtime_value(state: dict, runtime, key: str):
    """Read request-only dependencies from runtime, with test compatibility fallback."""
    if runtime is not None:
        context = runtime.context
        if isinstance(context, dict):
            return context.get(key)
        return getattr(context, key, None)
    return state.get(key)


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

async def load_context_node(state: dict, runtime=None) -> dict:
    """从 DB 加载面试上下文（简历/面经 + 对话历史 + 题目列表）"""
    db: AsyncSession = _runtime_value(state, runtime, "db")
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

    question_item = questions[current_index]
    question_metadata = question_item if isinstance(question_item, dict) else {}
    # 新面试在创建时已锁定 Rubric；历史面试没有快照时使用内置 legacy 兼容版本，
    # 避免每道题重新查询 system_settings，也避免旧面试因配置库暂时不可达而阻塞。
    scoring_rubric = interview.scoring_rubric or evaluation_service.validate_rubric(DEFAULT_RUBRIC)

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
        "scoring_rubric": scoring_rubric,
        "question_metadata": question_metadata,
    }


# ---------------------------------------------------------------------------
# 节点 2：评估回答
# ---------------------------------------------------------------------------

async def evaluate_node(state: dict, runtime=None) -> dict:
    """评估候选人回答，带三级容错 + 流式输出"""
    # 如果上游已出错，短路跳过
    if state.get("error"):
        return {"score": 0.0, "feedback": "", "evaluation": {}}

    answer = state["answer"]
    current_question = state["current_question"]
    parsed_resume = state["parsed_resume"]
    chat_history = state["chat_history"]
    chunk_queue = _runtime_value(state, runtime, "chunk_queue")  # 可选：用于流式输出
    rubric = state.get("scoring_rubric") or evaluation_service.validate_rubric(DEFAULT_RUBRIC)
    question_metadata = state.get("question_metadata") or {}

    # Level 1: 尝试流式结构化 AI 评估。marker 后的 JSON 不推给前端。
    last_error = None
    try:
        full_text = ""
        pending = ""
        marker = "__EVALUATION_JSON__"
        marker_seen = False
        async for chunk in AIService.evaluate_answer_stream(
            question=current_question,
            answer=answer,
            resume_context=parsed_resume,
            chat_history=chat_history,
            history_summary=state.get("history_summary"),
            rubric=rubric,
            question_metadata=question_metadata,
        ):
            full_text += chunk
            if chunk_queue:
                pending += chunk
                if not marker_seen and marker in pending:
                    prefix, pending = pending.split(marker, 1)
                    if prefix:
                        await chunk_queue.put(prefix)
                    marker_seen = True
                elif not marker_seen and len(pending) > len(marker) + 4:
                    safe_length = len(pending) - len(marker) - 4
                    await chunk_queue.put(pending[:safe_length])
                    pending = pending[safe_length:]

        feedback_text, raw_evaluation = AIService.extract_structured_evaluation(full_text)
        if "dimension_scores" in raw_evaluation:
            evaluation = evaluation_service.validate_model_output(
                raw_evaluation,
                rubric=rubric,
                answer=answer,
                category=question_metadata.get("category"),
            )
        elif "score" in raw_evaluation:
            evaluation = evaluation_service.from_legacy_score(
                raw_evaluation["score"],
                rubric=rubric,
                category=question_metadata.get("category"),
                feedback=feedback_text,
            )
        else:
            raise ValueError("结构化评分缺少 dimension_scores")
        if chunk_queue and not marker_seen and feedback_text:
            await chunk_queue.put(feedback_text)
        return {
            "evaluation": evaluation,
            "score": evaluation["score"],
            "feedback": evaluation["feedback"] or feedback_text,
        }
    except Exception as e:
        last_error = str(e)
        logger.warning("[evaluate_node] 结构化 AI 评估失败: %s", e)

    # Level 2-3: 共享降级逻辑
    fallback_result = AIService._fallback_evaluate(answer)
    fallback_evaluation = evaluation_service.fallback(
        rubric=rubric,
        answer=answer,
        category=question_metadata.get("category"),
        feedback=fallback_result["feedback"],
        fallback_level=fallback_result.get("fallback_level", 3),
        skip_type=fallback_result.get("skip_type"),
        score_override=fallback_result.get("score"),
    )
    interview_metrics.increment("evaluation_fallback_total")
    interview_metrics.increment(
        f"evaluation_fallback_level_{fallback_result.get('fallback_level', 3)}"
    )
    if chunk_queue:
        await chunk_queue.put(fallback_result["feedback"])
    return {
        "evaluation": {**fallback_evaluation, "error": last_error},
        "score": fallback_evaluation["score"],
        "feedback": fallback_result["feedback"],
        "skip_type": fallback_result.get("skip_type"),
    }


# ---------------------------------------------------------------------------
# 节点 3：生成下一题 / 标记完成
# ---------------------------------------------------------------------------

async def generate_next_node(state: dict, runtime=None) -> dict:
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

async def save_results_node(state: dict, runtime=None) -> dict:
    """保存评估结果、推进面试进度、生成报告、发送通知"""
    # 如果上游已出错，返回错误结果
    if state.get("error"):
        return {"result": {"error": state["error"]}}

    db: AsyncSession = _runtime_value(state, runtime, "db")
    interview_id = state["interview_id"]
    user_id = state["user_id"]
    current_index = state["current_index"]
    is_finished = state["is_finished"]
    score = state["score"]
    feedback = state["feedback"]
    score_details = state.get("evaluation") or None
    questions = state["questions"]
    answer = state["answer"]

    # 幂等守卫：同一题（interview_id + question_index）已存在评分则跳过写入，
    # 避免网络重试导致的重复存分、重复生成报告。
    # 注意这是「先查后写」，并发下本身不是原子操作（两个请求可能同时查不到），
    # 真正的兜底是 interview_messages 上的唯一索引 uq_interview_message_question。
    idem_query = select(InterviewMessage).where(
        InterviewMessage.interview_id == interview_id,
        InterviewMessage.role == "candidate",
        InterviewMessage.question_index == current_index,
    )
    idem_result = await db.execute(idem_query)
    existing = idem_result.scalar_one_or_none()
    if existing:
        interview_metrics.increment("idempotent_submission_total")
        logger.warning(
            f"[save_results] 幂等跳过：第 {current_index} 题已存在评分，"
            f"避免重复写入（score={existing.score}）"
        )
        return {
            "result": {
                "score": float(existing.score) if existing.score is not None else 0.0,
                "feedback": existing.feedback or "",
                "evaluation": existing.score_details or {},
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
        interview_metrics.increment("idempotent_submission_total")
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
        score_details=score_details,
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

        # 报告改为**后台生成**（见 interview_report_service 的模块说明）：
        # 这里只落「就绪标记」，与 status / overall_score 在同一个事务里，
        # 保证前端看到 status=completed 时必定同时看到 pending —— 不存在
        # 「已完成却没有任何报告标记」的中间态。报告的 LLM 调用搬到 Celery 后，
        # SSE 的 done 事件不必再等那几十秒静默。
        interview.report_status = "pending"
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

    try:
        await db.commit()
    except IntegrityError:
        # 并发重复提交：唯一约束 uq_interview_message_question 拦下了后到的那个请求。
        # 回滚后按「本题已存在」返回，让前端拿到与首次提交一致的结果，而不是 500。
        # 注意：回滚会过期 ORM 对象，异步下再读它的属性会触发隐式 IO 报错，
        # 所以下面重新查一次，不复用上面的 interview / candidate_msg。
        await db.rollback()
        existing = await _load_answered_message(db, interview_id, current_index)
        if existing is None:
            raise
        logger.warning(
            "[save_results] 并发重复提交被唯一约束拦下，按幂等返回："
            f"interview_id={interview_id} index={current_index}"
        )
        interview_metrics.increment("idempotent_submission_total")
        return {
            "result": {
                "score": float(existing.score) if existing.score is not None else 0.0,
                "feedback": existing.feedback or "",
                "evaluation": existing.score_details or {},
                "question_index": current_index,
                "is_finished": is_finished,
                "next_question": state.get("next_question"),
                "idempotent": True,
            },
            "overall_score": 0.0,
        }

    # 面试完成通知
    if is_finished:
        # 先发通知：内容只依赖上面算好的 overall_score，与报告无关，
        # 放在报告投递之前可以避免被「入队失败后的同步降级」拖住几十秒。
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

        # 投递报告生成。原先生成学习笔记草稿与薄弱点统计也在这里同步调用，
        # 现在随报告一起搬进 Celery（两者都以 report 为输入，报告没写完时读到的
        # 是空报告）—— 顺序上必须晚于报告落库，见 interview_report_service。
        await interview_report_service.dispatch(db, interview_id)

    # 组装最终结果
    result = {
        "score": score,
        "feedback": feedback,
        "evaluation": score_details or {},
        "question_index": current_index,
        "is_finished": is_finished,
        "next_question": state.get("next_question"),
    }
    if is_finished:
        result["overall_score"] = overall_score

    return {"result": result, "overall_score": overall_score}


async def _load_answered_message(
    db: AsyncSession,
    interview_id: int,
    question_index: int,
) -> InterviewMessage | None:
    """读取某题已存在的候选人回答（唯一约束拦下并发重复提交后用它组装幂等结果）。"""
    result = await db.execute(
        select(InterviewMessage)
        .where(
            InterviewMessage.interview_id == interview_id,
            InterviewMessage.role == "candidate",
            InterviewMessage.question_index == question_index,
        )
        .order_by(InterviewMessage.id.desc())
        .limit(1)
    )
    return result.scalars().first()


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
        "evaluation": message.score_details or {},
        "question_index": question_index,
        "is_finished": is_finished,
        "next_question": None if is_finished else _get_question_text(questions, current_index),
        "idempotent": True,
    }
    if is_finished:
        duplicate["overall_score"] = float(interview.overall_score or 0)
    return duplicate
