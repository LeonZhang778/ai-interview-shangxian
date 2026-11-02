"""面试报告的独立生成服务。

为什么要有这个模块：报告生成原本被塞在 `save_results_node` 里，与最后一题的评分写入、
`status=completed` 处在同一个事务中。后果是 SSE 的 done 事件必须等报告写完才能发，
用户盯着「AI 思考中」等几十秒；同时报告一旦生成失败（LLM 抖动），整个提交也跟着受影响。

现在拆成两条独立路径：
    1) 请求内：写评分 + `status=completed` + `report_status=pending`，立即返回；
    2) 请求外：Celery 任务调用本服务，重建问答数据 → 生成报告 → 落库 → 后置副作用。

本模块同时负责「把生成请求投递出去」这件事（含入队失败时的同步降级），
供 save_results_node（首次生成）与 get_report / regenerate 接口（自愈重试）共用。
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import Interview
from app.models.interview_message import InterviewMessage
from app.models.resume import Resume
from app.services.client.ai_service import AIService
from app.utils.utils import safe_parse_json

logger = logging.getLogger(__name__)

# 报告状态
STATUS_READY = "ready"
STATUS_PENDING = "pending"
STATUS_FAILED = "failed"

# 「卡住」判定：pending / failed 超过这个时长仍未推进，才允许被再次投递。
# 目的是给自动重试加节流 —— 否则用户每刷新一次报告页就会往队列里塞一个任务。
STALE_SECONDS = 90

# 用户手动点「重新生成」的最小间隔：主动操作要即时响应，但仍需挡住连点。
MANUAL_MIN_INTERVAL_SECONDS = 30


class InterviewReportService:

    @staticmethod
    def build_skill_coverage(interview: Interview, qa_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """把岗位技能、简历证据和面试题得分合并成稳定的报告数据。"""
        analysis = interview.gap_analysis or {}
        skills = []
        for requirement_type, key in (("required", "required_skills"), ("preferred", "preferred_skills")):
            for item in analysis.get(key, []) if isinstance(analysis, dict) else []:
                if isinstance(item, dict) and item.get("name"):
                    skills.append((requirement_type, item))

        questions = interview.questions_data if isinstance(interview.questions_data, list) else []
        coverage = []
        for requirement_type, skill in skills:
            name = str(skill["name"])
            indices = [
                index for index, question in enumerate(questions)
                if isinstance(question, dict) and str(question.get("target_skill", "")).strip().lower() == name.lower()
            ]
            scores = [
                qa_data[index]["score"]
                for index in indices
                if index < len(qa_data) and qa_data[index].get("score") is not None
            ]
            gaps = [
                item for item in analysis.get("resume_gaps", [])
                if isinstance(item, dict) and str(item.get("skill", "")).lower() == name.lower()
            ] if isinstance(analysis, dict) else []
            coverage.append({
                "skill": name,
                "requirement_type": requirement_type,
                "resume_status": skill.get("resume_status", "unknown"),
                "interview_score": round(sum(scores) / len(scores), 1) if scores else None,
                "question_indices": indices,
                "evidence": (skill.get("evidence") or [""])[0],
                "recommendation": (gaps[0].get("practice_action", "") if gaps else ""),
            })
        return coverage

    # 把模块级常量同时挂到类上，调用方（interview_service）可以按
    # `interview_report_service.MANUAL_MIN_INTERVAL_SECONDS` 这样引用，
    # 不必额外 import 模块级名字；两者是同一个值。
    STALE_SECONDS = STALE_SECONDS
    MANUAL_MIN_INTERVAL_SECONDS = MANUAL_MIN_INTERVAL_SECONDS

    # ------------------------------------------------------------------
    # 调度：把生成请求投递出去
    # ------------------------------------------------------------------

    @staticmethod
    def enqueue(interview_id: int) -> bool:
        """把报告生成投递到 Celery。返回是否投递成功（不抛异常）。"""
        try:
            from app.schedule.jobs.report_tasks import generate_interview_report_task

            generate_interview_report_task.delay(interview_id)
            return True
        except Exception as exc:  # broker 不可用 / 序列化失败
            logger.warning(
                "[report] 报告任务入队失败，将由调用方决定是否同步降级: "
                "interview_id=%s err=%s",
                interview_id,
                exc,
            )
            return False

    @staticmethod
    async def dispatch(db: AsyncSession, interview_id: int) -> bool:
        """投递报告生成；入队失败则**同步降级生成**，保证用户总能拿到报告。

        降级路径只在 broker（Redis）不可用时触发。它会把调用方的请求拖慢几十秒 ——
        但相比「面试做完了却永远没有报告」，这个代价是值得的。注意降级时仍走同一个
        session，且 generate_for_interview 内部自带幂等（已 ready 则跳过）。
        """
        if InterviewReportService.enqueue(interview_id):
            return True
        logger.warning(
            "[report] 入队失败，改为在当前请求内同步生成: interview_id=%s", interview_id
        )
        try:
            await InterviewReportService.generate_for_interview(db, interview_id)
            return True
        except Exception as exc:
            logger.error(
                "[report] 同步降级生成报告同样失败: interview_id=%s err=%s",
                interview_id,
                exc,
                exc_info=True,
            )
            return False

    @staticmethod
    async def request_regeneration(
        db: AsyncSession,
        interview: Interview,
        *,
        min_interval_seconds: int = STALE_SECONDS,
    ) -> str:
        """在「报告未就绪」时请求（重新）生成，返回请求后的状态。

        用一条带条件的 UPDATE 同时完成三件事，避免「先读后写」在并发下重复投递：
            - 抢占：只有仍处于 pending / failed 的行才会被更新（原子性由数据库保证）；
            - 节流：距今 min_interval_seconds 内已被请求过的行直接跳过；
            - 打点：把 report_status 重置为 pending 并顺带刷新 updated_at。
        UPDATE 命中（rowcount=1）才投递任务，因此并发的两次刷新最多只有一次真正入队。
        """
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=min_interval_seconds)
        statement = (
            update(Interview)
            .where(
                Interview.id == interview.id,
                Interview.report_status.in_((STATUS_PENDING, STATUS_FAILED)),
                Interview.updated_at < cutoff,
            )
            .values(report_status=STATUS_PENDING, updated_at=func.now())
            .returning(Interview.id)
        )
        claimed = (await db.execute(statement)).first()
        # UPDATE 即使没命中也会开启事务，统一提交以释放连接
        await db.commit()

        if claimed is None:
            # 没抢到：要么刚被请求过（等一会儿即可），要么已被别的请求抢先投递。
            # 能走到这里说明报告本来就没就绪，对外统一表现为「生成中」。
            return STATUS_PENDING

        InterviewReportService.enqueue(interview.id)
        return STATUS_PENDING

    # ------------------------------------------------------------------
    # 生成
    # ------------------------------------------------------------------

    @staticmethod
    async def _load_resume_context(db: AsyncSession, interview: Interview) -> Dict[str, Any]:
        """加载简历/面经上下文（与 load_context_node 的口径保持一致）。"""
        if interview.resume_id:
            resume = await db.get(Resume, interview.resume_id)
            if resume:
                return safe_parse_json(resume.parsed_content, {})
            return {}
        if interview.experience_id:
            from app.models.experience import Experience

            experience = await db.get(Experience, interview.experience_id)
            if experience:
                return {
                    "summary": f"面经：{experience.title}",
                    "skills": [experience.company, experience.position],
                }
        return {}

    @staticmethod
    async def build_qa_data(db: AsyncSession, interview: Interview) -> List[Dict[str, Any]]:
        """从库里重建「题目 + 回答 + 评分 + 评语」列表。

        改造前这份数据是在请求内手写的：已落库的题从 DB 读，当前这题因为还没 commit
        而显式补进映射（当时的注释是「避免报告漏掉最后一题」）。挪到后台后不存在这个
        时序问题 —— 最后一题在投递任务之前就已经提交，直接从库读即可。
        未作答的题保留占位（与旧行为一致），报告里会显示为「未回答」。
        """
        rows = await db.execute(
            select(InterviewMessage).where(
                InterviewMessage.interview_id == interview.id,
                InterviewMessage.role == "candidate",
                InterviewMessage.score.isnot(None),
            )
        )
        answers_by_index: Dict[int, Dict[str, Any]] = {}
        for message in rows.scalars().all():
            if message.question_index is None or message.score is None:
                continue
            answers_by_index[int(message.question_index)] = {
                "answer": message.content,
                "score": float(message.score),
                "feedback": message.feedback or "",
            }
            if message.score_details:
                answers_by_index[int(message.question_index)]["evaluation"] = message.score_details

        questions = interview.questions_data or []
        if not isinstance(questions, list):
            questions = []

        qa_data = []
        for index, question in enumerate(questions):
            question_text = (
                question.get("question", str(question)) if isinstance(question, dict) else str(question)
            )
            answered = answers_by_index.get(index)
            qa_item = {
                "question": question_text,
                "answer": answered["answer"] if answered else "未回答",
                "score": answered["score"] if answered else 0,
                "feedback": answered["feedback"] if answered else "",
            }
            if answered and answered.get("evaluation"):
                qa_item["evaluation"] = answered["evaluation"]
            qa_data.append(qa_item)
        return qa_data

    @staticmethod
    async def generate_for_interview(db: AsyncSession, interview_id: int) -> Dict[str, Any]:
        """生成并落库报告，随后执行「面试结果回流」的两个后置副作用。

        幂等键是 `report_status == ready 且 report 非空`：重复投递（Celery 智能重试、
        用户手动重试、入队降级）到第二次进来时会直接跳过，不会重复调用 LLM。
        """
        interview = await db.get(Interview, interview_id)
        if not interview:
            return {"interview_id": interview_id, "status": "skipped", "reason": "not_found"}
        if interview.status != "completed":
            return {"interview_id": interview_id, "status": "skipped", "reason": "not_completed"}
        if (interview.report_status or STATUS_READY) == STATUS_READY and interview.report:
            return {"interview_id": interview_id, "status": "skipped", "reason": "already_ready"}

        qa_data = await InterviewReportService.build_qa_data(db, interview)
        parsed_resume = await InterviewReportService._load_resume_context(db, interview)

        report = await AIService.generate_report(
            parsed_resume=parsed_resume,
            target_position=interview.target_position,
            questions_and_scores=qa_data,
        )
        report["question_scores"] = []
        for index, item in enumerate(qa_data):
            question_score = {
                "question": item["question"],
                "score": item["score"],
                "feedback": item.get("feedback", ""),
            }
            if isinstance(item.get("evaluation"), dict) and item["evaluation"].get("dimension_scores"):
                question_score["answer"] = item.get("answer", "")
                question_score["evaluation"] = item["evaluation"]
            if (
                isinstance(interview.questions_data, list)
                and index < len(interview.questions_data)
                and isinstance(interview.questions_data[index], dict)
                and interview.questions_data[index].get("target_skill")
            ):
                question_score["target_skill"] = interview.questions_data[index]["target_skill"]
            report["question_scores"].append(question_score)
        report["skill_coverage"] = InterviewReportService.build_skill_coverage(interview, qa_data)
        report["gap_summary"] = [
            item.get("practice_action") or item.get("reason") or item.get("skill")
            for item in (interview.gap_analysis or {}).get("resume_gaps", [])
            if isinstance(item, dict)
        ][:8]

        structured_evaluations = [
            item.get("evaluation")
            for item in qa_data
            if isinstance(item.get("evaluation"), dict)
            and item["evaluation"].get("dimension_scores")
            and not item["evaluation"].get("fallback")
        ]
        if structured_evaluations:
            dimension_values: Dict[str, List[float]] = {}
            dimension_details: Dict[str, Dict[str, Any]] = {}
            for evaluation in structured_evaluations:
                for dimension in evaluation.get("dimension_scores", []):
                    key = dimension.get("key")
                    if not key:
                        continue
                    dimension_values.setdefault(key, []).append(float(dimension.get("score", 0)))
                    detail = dimension_details.setdefault(
                        key,
                        {"evidence": [], "missing_evidence": [], "improvement_actions": [], "evidence_coverage": []},
                    )
                    detail["evidence"].extend(dimension.get("evidence", []))
                    detail["missing_evidence"].extend(dimension.get("missing_evidence", []))
                    detail["improvement_actions"].extend(dimension.get("improvement_actions", []))
                if evaluation.get("evidence_coverage") is not None:
                    for detail in dimension_details.values():
                        detail["evidence_coverage"].append(float(evaluation["evidence_coverage"]))
            report["dimension_scores"] = {
                key: round(sum(values) / len(values), 1)
                for key, values in dimension_values.items()
                if values
            }
            for key, detail in dimension_details.items():
                detail["evidence"] = detail["evidence"][:20]
                detail["missing_evidence"] = detail["missing_evidence"][:20]
                detail["improvement_actions"] = list(dict.fromkeys(detail["improvement_actions"]))[:10]
                detail["evidence_coverage"] = (
                    round(sum(detail["evidence_coverage"]) / len(detail["evidence_coverage"]), 2)
                    if detail["evidence_coverage"] else 0
                )
            report["dimension_details"] = dimension_details
            report["rubric_version"] = interview.scoring_rubric_version or structured_evaluations[0].get("rubric_version")

        interview.report = json.dumps(report, ensure_ascii=False)
        interview.report_status = STATUS_READY
        await db.commit()

        logger.info("[report] 报告已生成: interview_id=%s", interview_id)

        # 后置副作用：原先在 save_results_node 的提交之后执行，现在随报告一起搬到后台。
        # 两者各自独立容错 —— 笔记草稿失败不应该连累薄弱点统计。
        await InterviewReportService._run_post_report_side_effects(db, interview)

        return {"interview_id": interview_id, "status": "generated"}

    @staticmethod
    async def _run_post_report_side_effects(db: AsyncSession, interview: Interview) -> None:
        """报告生成后的回流：学习笔记草稿 + 薄弱点统计。两者都依赖已落库的 report。"""
        target_position = interview.target_position or "AI 面试"

        try:
            from app.services.client.learning_note_service import learning_note_service

            await learning_note_service.generate_from_interview(
                db=db,
                user_id=interview.user_id,
                interview_id=interview.id,
                note_type="review",
                title=f"{target_position} 面试复盘",
                visibility="private",
            )
        except Exception as exc:
            logger.warning("[report] 自动生成学习笔记草稿失败: interview_id=%s err=%s", interview.id, exc)

        try:
            from app.services.client.weakness_service import weakness_service

            await weakness_service.record_from_interview(
                db=db,
                user_id=interview.user_id,
                interview_id=interview.id,
            )
        except Exception as exc:
            logger.warning("[report] 记录薄弱点统计失败: interview_id=%s err=%s", interview.id, exc)

    @staticmethod
    async def mark_failed(interview_id: int) -> None:
        """把仍在生成中的报告标记为失败，让前端出现「重新生成」入口。

        条件里排除 ready，避免「重试失败但上一次已成功写库」时把好状态改坏。
        用独立会话：调用它的地方正处于异常处理路径，原会话可能已被回滚。
        """
        try:
            from app.db.session import async_session

            async with async_session() as db:
                await db.execute(
                    update(Interview)
                    .where(
                        Interview.id == interview_id,
                        Interview.report_status != STATUS_READY,
                    )
                    .values(report_status=STATUS_FAILED, updated_at=func.now())
                )
                await db.commit()
        except Exception as exc:
            logger.error("[report] 标记报告失败状态时出错: interview_id=%s err=%s", interview_id, exc)


interview_report_service = InterviewReportService()
