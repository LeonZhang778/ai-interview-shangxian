"""面试报告后台生成任务。

最后一个问题提交后，请求线程只写「评分 + status=completed + report_status=pending」就返回，
报告的 LLM 调用（几十秒）交给这里。这样 SSE 的 done 事件不必再等报告，
用户看到的是「面试结束、报告生成中」，而不是长时间不动的思考光标。
"""

import logging

from app.core.async_runner import run_async
from app.core.celery_app import celery_app
from app.db.session import async_session
from app.services.client.interview_report_service import interview_report_service

logger = logging.getLogger(__name__)


@celery_app.task(
    name="interview.generate_report",
    bind=True,
    # 只在异常时重试，且次数有限：报告失败通常是 LLM 瞬时抖动，重试一次多半能成；
    # 次数再多也没意义，而且此时用户已经在报告页看到「重新生成」入口了。
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def generate_interview_report_task(self, interview_id: int):
    # 经 run_async 跑在进程常驻事件循环上，避免逐任务开关循环导致
    # DB/AI/Redis 单例连接池跨循环复用报错（同 resume_tasks 说明）。
    return run_async(_generate_report(interview_id))


async def _generate_report(interview_id: int):
    async with async_session() as db:
        try:
            return await interview_report_service.generate_for_interview(db, interview_id)
        except Exception as exc:
            # 先落「失败」再抛出：抛出交给 Celery 重试，而失败标记让前端立刻有反馈，
            # 不至于在重试等待期间一直显示「生成中」。重试成功后会被改回 ready。
            logger.error("[report][task] 报告生成失败: interview_id=%s err=%s", interview_id, exc)
            await interview_report_service.mark_failed(interview_id)
            raise
