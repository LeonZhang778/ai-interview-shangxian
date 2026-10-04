import json
import logging
from decimal import Decimal
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.config import settings
from app.models.interview import Interview
from app.models.interview_message import InterviewMessage
from app.models.resume import Resume
from app.services.client.ai_service import AIService
from app.db.session import transaction
from app.exceptions.http_exceptions import NotFoundError, ValidationError
from app.utils.utils import safe_parse_json

logger = logging.getLogger(__name__)

# LangGraph 面试状态机（模块级单例，已挂载节点级可观测性）
from app.graphs.interview_graph import interview_graph, interview_graph_stream


class InterviewService:

    @staticmethod
    def _first_question_text(questions: Any) -> str:
        """校验 AI 出题结果并取出首题文本。

        AI 偶尔会返回空数组、纯字符串或 {"questions": [...]} 这类非预期形状。
        以前是建完面试记录（已 commit）之后才取 questions[0]["question"]，
        异常发生在落库之后 —— 于是留下一条没有问题、永远无法继续的 in_progress 面试，
        它占着并发额度，用户只能自己去列表里删掉。现在改成在建记录之前就失败。
        """
        if not isinstance(questions, list) or not questions:
            raise ValidationError(message="题目生成失败，请重试")
        first = questions[0]
        text = first.get("question") if isinstance(first, dict) else first
        if not isinstance(text, str) or not text.strip():
            raise ValidationError(message="题目生成失败，请重试")
        return text

    @staticmethod
    async def _persist_new_interview(
        db: AsyncSession,
        interview: Interview,
        first_question: str,
    ) -> None:
        """面试记录与首题消息在同一个事务里落库。

        此前是两次 commit（先建面试记录刷新出主键，再写首题消息）。两次之间进程若中断
        —— 部署重启、内存不足被 kill（服务器只有 1.6Gi 内存）—— 就会留下上面那种孤儿面试。
        """
        async with transaction(db):
            db.add(interview)
            # flush 而非 commit：先拿到自增主键给首题消息用，但事务不结束
            await db.flush()
            db.add(
                InterviewMessage(
                    interview_id=interview.id,
                    role="interviewer",
                    content=first_question,
                    question_index=0,
                )
            )

    @staticmethod
    async def _assert_concurrent_limit(db: AsyncSession, user_id: int) -> None:
        """限制单个用户「同时进行中」的面试数量。

        必须在调用 AI 生成题目之前检查：否则每次超限请求都会先白花一次 LLM 调用，
        然后才把请求拒掉。用户放弃的面试会一直停在 in_progress，所以提示里要给出去路
        （完成它，或从列表里删掉）。
        """
        count = await db.scalar(
            select(func.count())
            .select_from(Interview)
            .where(Interview.user_id == user_id, Interview.status == "in_progress")
        )
        if (count or 0) >= settings.MAX_CONCURRENT_INTERVIEWS:
            raise ValidationError(
                message=(
                    f"同时进行的面试最多 {settings.MAX_CONCURRENT_INTERVIEWS} 场，"
                    "请先完成或删除已有的面试"
                )
            )

    @staticmethod
    async def start_interview(
        db: AsyncSession,
        user_id: int,
        resume_id: int,
        target_position: str,
        difficulty: str,
        total_questions: int
    ) -> Dict:
        """开始新的面试会话"""
        # 验证简历是否存在且已解析
        query = select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == user_id
        )
        result = await db.execute(query)
        resume = result.scalar_one_or_none()

        if not resume:
            raise NotFoundError(message="简历不存在")
        if resume.status != "completed":
            raise ValidationError(message="简历尚未解析完成")

        parsed_resume = safe_parse_json(resume.parsed_content, {})

        # 并发上限：放在 AI 出题之前，避免超限请求白花一次 LLM 调用
        await InterviewService._assert_concurrent_limit(db, user_id)

        # 通过 AI 生成面试题目
        questions = await AIService.generate_questions(
            parsed_resume=parsed_resume,
            target_position=target_position,
            difficulty=difficulty,
            count=total_questions
        )

        # 先校验题目形状，再建记录：顺序反了会产生孤儿面试
        first_question = InterviewService._first_question_text(questions)

        # 创建面试记录（与首题消息同事务落库）
        interview = Interview(
            user_id=user_id,
            resume_id=resume_id,
            target_position=target_position,
            difficulty=difficulty,
            total_questions=total_questions,
            current_question_index=0,
            questions_data=questions,
            status="in_progress"
        )
        await InterviewService._persist_new_interview(db, interview, first_question)

        return {
            "interview_id": interview.id,
            "first_question": first_question,
            "question_index": 0,
            "total_questions": total_questions
        }

    @staticmethod
    async def submit_answer(
        db: AsyncSession,
        user_id: int,
        interview_id: int,
        answer: str
    ) -> Dict:
        """提交当前题目的回答并获取 AI 评估（通过 LangGraph 执行）"""
        # 前置校验
        query = select(Interview).where(
            Interview.id == interview_id,
            Interview.user_id == user_id
        )
        result = await db.execute(query)
        interview = result.scalar_one_or_none()

        if not interview:
            raise NotFoundError(message="面试记录不存在")
        duplicate = await InterviewService._get_duplicate_submission_result(db, interview, answer)
        if duplicate:
            return duplicate
        if interview.status == "completed":
            raise ValidationError(message="面试已结束")

        # thread_id 沿用「面试ID:题号」。当前编译图未挂 checkpointer，该配置是惰性的；
        # 幂等由入口的 _get_duplicate_submission_result 与 save_results_node 的守卫保证。
        thread_id = f"iv:{interview_id}:{interview.current_question_index}"

        # 执行图
        graph_result = await interview_graph.ainvoke({
            "interview_id": interview_id,
            "user_id": user_id,
            "answer": answer,
            "db": db,
            # 以下字段由 load_context 节点填充
            "current_question": "",
            "parsed_resume": {},
            "chat_history": [],
            "history_summary": None,
            "questions": [],
            "current_index": 0,
            "target_position": "",
            "resume_id": None,
            "experience_id": None,
            # 以下字段由 evaluate / generate_next 节点填充
            "evaluation": {},
            "score": 0.0,
            "feedback": "",
            "skip_type": None,
            "next_question": None,
            "is_finished": False,
            "overall_score": 0.0,
            "error": None,
            "result": {},
        }, config={"configurable": {"thread_id": thread_id}})

        result = graph_result["result"]
        if result.get("error"):
            if result["error"] == "面试记录不存在":
                raise NotFoundError(message=result["error"])
            raise ValidationError(message=result["error"])
        return result

    @staticmethod
    async def submit_answer_stream(
        db: AsyncSession,
        user_id: int,
        interview_id: int,
        answer: str
    ):
        """流式提交回答 - 通过 LangGraph + asyncio.Queue 实现实时 token 流"""
        # 前置校验
        query = select(Interview).where(
            Interview.id == interview_id,
            Interview.user_id == user_id
        )
        result = await db.execute(query)
        interview = result.scalar_one_or_none()

        if not interview:
            yield f"data: {json.dumps({'type': 'error', 'content': '面试记录不存在'})}\n\n"
            return
        duplicate = await InterviewService._get_duplicate_submission_result(db, interview, answer)
        if duplicate:
            yield f"data: {json.dumps({'type': 'done', **duplicate}, ensure_ascii=False)}\n\n"
            return
        if interview.status == "completed":
            yield f"data: {json.dumps({'type': 'error', 'content': '面试已结束'})}\n\n"
            return

        # thread_id 同上（惰性配置，见 submit_answer）
        thread_id = f"iv:{interview_id}:{interview.current_question_index}"

        # 流式执行图（evaluate 节点内部 LLM token 通过 queue 实时输出）
        # 兜底：任何未预期异常都必须转换成 error 事件发给前端，
        # 绝不能让生成器直接抛异常中断，否则前端收不到终态、永久卡在思考态。
        try:
            async for event in interview_graph_stream({
                "interview_id": interview_id,
                "user_id": user_id,
                "answer": answer,
                "db": db,
                "chunk_queue": None,  # 由 interview_graph_stream 注入
                "current_question": "",
                "parsed_resume": {},
                "chat_history": [],
                "history_summary": None,
                "questions": [],
                "current_index": 0,
                "target_position": "",
                "resume_id": None,
                "experience_id": None,
                "evaluation": {},
                "score": 0.0,
                "feedback": "",
                "skip_type": None,
                "next_question": None,
                "is_finished": False,
                "overall_score": 0.0,
                "error": None,
                "result": {},
            }, thread_id=thread_id):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"[submit_answer_stream] 流式执行异常: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': f'评估服务异常，请重试：{e}'}, ensure_ascii=False)}\n\n"

    @staticmethod
    async def _get_duplicate_submission_result(
        db: AsyncSession,
        interview: Interview,
        answer: str
    ) -> Dict | None:
        """兼容无幂等键的旧前端：相同答案重试上一题时返回已有结果。"""
        questions = interview.questions_data or []
        if not isinstance(questions, list):
            return None
        current_index = interview.current_question_index or 0
        previous_index = current_index - 1
        if previous_index < 0:
            return None

        result = await db.execute(
            select(InterviewMessage)
            .where(
                InterviewMessage.interview_id == interview.id,
                InterviewMessage.role == "candidate",
                InterviewMessage.question_index == previous_index,
            )
            .order_by(InterviewMessage.id.desc())
            .limit(1)
        )
        message = result.scalars().first()
        if not message or message.content != answer:
            return None

        is_finished = interview.status == "completed" or current_index >= len(questions)
        next_question = None
        if not is_finished:
            question = questions[current_index]
            next_question = question.get("question") if isinstance(question, dict) else str(question)
        duplicate = {
            "score": float(message.score) if message.score is not None else 0.0,
            "feedback": message.feedback or "",
            "question_index": previous_index,
            "is_finished": is_finished,
            "next_question": next_question,
            "idempotent": True,
        }
        if is_finished:
            duplicate["overall_score"] = float(interview.overall_score or 0)
        return duplicate

    @staticmethod
    async def get_report(
        db: AsyncSession,
        user_id: int,
        interview_id: int
    ) -> Dict:
        """获取面试评估报告"""
        query = select(Interview).where(
            Interview.id == interview_id,
            Interview.user_id == user_id
        )
        result = await db.execute(query)
        interview = result.scalar_one_or_none()

        if not interview:
            raise NotFoundError(message="面试记录不存在")
        if interview.status != "completed":
            raise ValidationError(message="面试尚未完成")

        report = safe_parse_json(interview.report, {})

        return {
            "interview_id": interview.id,
            "overall_score": float(interview.overall_score) if interview.overall_score else 0,
            "total_questions": interview.total_questions,
            "report": report
        }

    @staticmethod
    async def get_interviews(
        db: AsyncSession,
        user_id: int
    ) -> Dict:
        """获取用户的所有面试记录"""
        query = select(Interview).where(
            Interview.user_id == user_id
        ).order_by(Interview.created_at.desc())
        result = await db.execute(query)
        interviews = result.scalars().all()

        items = [
            {
                "interview_id": i.id,
                "target_position": i.target_position,
                "difficulty": i.difficulty,
                "overall_score": float(i.overall_score) if i.overall_score else None,
                "total_questions": i.total_questions,
                "status": i.status,
                "created_at": i.created_at.isoformat() if i.created_at else None
            }
            for i in interviews
        ]

        return {
            "total": len(items),
            "items": items
        }

    @staticmethod
    async def get_interview_messages(
        db: AsyncSession,
        user_id: int,
        interview_id: int
    ) -> List[Dict]:
        """获取面试的所有对话消息"""
        # 验证面试归属权
        interview_query = select(Interview).where(
            Interview.id == interview_id,
            Interview.user_id == user_id
        )
        interview_result = await db.execute(interview_query)
        interview = interview_result.scalar_one_or_none()
        if not interview:
            raise NotFoundError(message="面试记录不存在")

        query = select(InterviewMessage).where(
            InterviewMessage.interview_id == interview_id
        ).order_by(InterviewMessage.id)
        result = await db.execute(query)
        messages = result.scalars().all()

        return {
            "items": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "question_index": m.question_index,
                    "score": float(m.score) if m.score else None,
                    "feedback": m.feedback,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in messages
            ],
            "total_questions": interview.total_questions,
            # 回传面试状态：前端据此判断面试是否已结束。
            # 若最后一题的 done 事件因流中断而丢失，或用户刷新/重进页面，
            # 前端仍能依据 status=completed 恢复到“面试结束→查看报告”态，
            # 避免永久卡在问答页无法进入报告。
            "status": interview.status,
            "current_question_index": interview.current_question_index,
        }

    @staticmethod
    async def delete_interview(
        db: AsyncSession,
        user_id: int,
        interview_id: int
    ) -> Dict:
        """删除面试记录及其关联的对话消息"""
        from sqlalchemy import delete as sql_delete

        query = select(Interview).where(
            Interview.id == interview_id,
            Interview.user_id == user_id
        )
        result = await db.execute(query)
        interview = result.scalar_one_or_none()

        if not interview:
            raise NotFoundError(message="面试记录不存在")

        # 先删除关联的对话消息
        await db.execute(
            sql_delete(InterviewMessage).where(InterviewMessage.interview_id == interview_id)
        )
        # 再删除面试记录
        await db.delete(interview)
        await db.commit()

        return {"message": "面试记录已删除"}

    @staticmethod
    async def delete_interview_admin(
        db: AsyncSession,
        interview_id: int
    ) -> Dict:
        """管理员删除面试记录（不校验用户归属）"""
        from sqlalchemy import delete as sql_delete

        interview = await db.get(Interview, interview_id)
        if not interview:
            raise NotFoundError(message="面试记录不存在")

        await db.execute(
            sql_delete(InterviewMessage).where(InterviewMessage.interview_id == interview_id)
        )
        await db.delete(interview)
        await db.commit()

        return {"message": "面试记录已删除"}

    @staticmethod
    async def share_interview(
        db: AsyncSession,
        user_id: int,
        interview_id: int
    ) -> Dict:
        """生成面试分享链接"""
        import secrets
        from datetime import datetime

        query = select(Interview).where(
            Interview.id == interview_id,
            Interview.user_id == user_id
        )
        result = await db.execute(query)
        interview = result.scalar_one_or_none()

        if not interview:
            raise NotFoundError(message="面试记录不存在")
        if interview.status != "completed":
            raise ValidationError(message="面试尚未完成，无法分享")

        # 如果已有分享token，直接返回
        if interview.is_shared and interview.share_token:
            return {
                "share_token": interview.share_token,
                "is_shared": True,
                "shared_at": interview.shared_at.isoformat() if interview.shared_at else None
            }

        # 生成新的分享token
        interview.share_token = secrets.token_urlsafe(24)[:32]
        interview.is_shared = True
        interview.shared_at = datetime.utcnow()
        await db.commit()

        return {
            "share_token": interview.share_token,
            "is_shared": True,
            "shared_at": interview.shared_at.isoformat()
        }

    @staticmethod
    async def unshare_interview(
        db: AsyncSession,
        user_id: int,
        interview_id: int
    ) -> Dict:
        """取消面试分享"""
        query = select(Interview).where(
            Interview.id == interview_id,
            Interview.user_id == user_id
        )
        result = await db.execute(query)
        interview = result.scalar_one_or_none()

        if not interview:
            raise NotFoundError(message="面试记录不存在")

        interview.is_shared = False
        interview.share_token = None
        interview.shared_at = None
        await db.commit()

        return {"message": "已取消分享", "is_shared": False}

    @staticmethod
    async def get_shared_report(
        db: AsyncSession,
        share_token: str
    ) -> Dict:
        """通过分享token获取面试报告（公开接口）"""
        query = select(Interview).where(
            Interview.share_token == share_token,
            Interview.is_shared == True,
            Interview.status == "completed"
        )
        result = await db.execute(query)
        interview = result.scalar_one_or_none()

        if not interview:
            raise NotFoundError(message="分享链接无效或已失效")

        report = safe_parse_json(interview.report, {})

        return {
            "interview_id": interview.id,
            "overall_score": float(interview.overall_score) if interview.overall_score else 0,
            "total_questions": interview.total_questions,
            "target_position": interview.target_position,
            "difficulty": interview.difficulty,
            "created_at": interview.created_at.isoformat() if interview.created_at else None,
            "report": report
        }

    @staticmethod
    async def start_practice_from_experience(
        db: AsyncSession,
        user_id: int,
        experience_id: int,
        question_count: int = 5
    ) -> Dict:
        """基于面经创建模拟面试"""
        from app.models.experience import Experience

        experience = await db.get(Experience, experience_id)
        if not experience or experience.status != "published":
            raise NotFoundError(message="面经不存在")

        # 并发上限：同样放在 AI 出题之前
        await InterviewService._assert_concurrent_limit(db, user_id)

        # 通过 AI 生成面试题
        questions = await AIService.generate_questions_from_experience(
            title=experience.title,
            company=experience.company,
            position=experience.position,
            content=experience.content,
            count=question_count
        )

        # 先校验题目形状，再建记录（total_questions 也依赖它是非空列表）
        first_question = InterviewService._first_question_text(questions)

        # 创建面试记录（与首题消息同事务落库）
        interview = Interview(
            user_id=user_id,
            resume_id=None,
            experience_id=experience_id,
            target_position=f"{experience.company} - {experience.position}",
            difficulty="medium",
            total_questions=len(questions),
            current_question_index=0,
            questions_data=questions,
            status="in_progress"
        )
        await InterviewService._persist_new_interview(db, interview, first_question)

        return {
            "interview_id": interview.id,
            "first_question": first_question,
            "question_index": 0,
            "total_questions": len(questions)
        }


interview_service = InterviewService()
