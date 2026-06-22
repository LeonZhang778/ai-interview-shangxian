import json
import logging
from decimal import Decimal
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.interview import Interview
from app.models.interview_message import InterviewMessage
from app.models.resume import Resume
from app.services.client.ai_service import AIService
from app.exceptions.http_exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)

# LangGraph 面试状态机（编译一次，全局复用）
from app.graphs.interview_graph import build_interview_graph, interview_graph_stream
interview_graph = build_interview_graph()


class InterviewService:

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

        parsed_resume = json.loads(resume.parsed_content)

        # 通过 AI 生成面试题目
        questions = await AIService.generate_questions(
            parsed_resume=parsed_resume,
            target_position=target_position,
            difficulty=difficulty,
            count=total_questions
        )

        # 创建面试记录
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
        db.add(interview)
        await db.commit()
        await db.refresh(interview)

        # 保存第一道题作为面试官消息
        first_question = questions[0]["question"]
        msg = InterviewMessage(
            interview_id=interview.id,
            role="interviewer",
            content=first_question,
            question_index=0
        )
        db.add(msg)
        await db.commit()

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
        if interview.status == "completed":
            raise ValidationError(message="面试已结束")

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
        })

        result = graph_result["result"]
        if result.get("error"):
            raise NotFoundError(message=result["error"])
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
        if interview.status == "completed":
            yield f"data: {json.dumps({'type': 'error', 'content': '面试已结束'})}\n\n"
            return

        # 流式执行图（evaluate 节点内部 LLM token 通过 queue 实时输出）
        async for event in interview_graph_stream({
            "interview_id": interview_id,
            "user_id": user_id,
            "answer": answer,
            "db": db,
            "chunk_queue": None,  # 由 interview_graph_stream 注入
            "current_question": "",
            "parsed_resume": {},
            "chat_history": [],
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
        }):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

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

        report = {}
        if interview.report:
            try:
                report = json.loads(interview.report)
            except json.JSONDecodeError:
                report = {}

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
            "total_questions": interview.total_questions
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

        report = {}
        if interview.report:
            try:
                report = json.loads(interview.report)
            except json.JSONDecodeError:
                report = {}

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

        # 通过 AI 生成面试题
        questions = await AIService.generate_questions_from_experience(
            title=experience.title,
            company=experience.company,
            position=experience.position,
            content=experience.content,
            count=question_count
        )

        # 创建面试记录
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
        db.add(interview)
        await db.commit()
        await db.refresh(interview)

        # 保存第一道题
        first_question = questions[0]["question"]
        msg = InterviewMessage(
            interview_id=interview.id,
            role="interviewer",
            content=first_question,
            question_index=0
        )
        db.add(msg)
        await db.commit()

        return {
            "interview_id": interview.id,
            "first_question": first_question,
            "question_index": 0,
            "total_questions": len(questions)
        }


interview_service = InterviewService()
