"""
后台媒体任务管理 API。

管理员只能查看任务元数据、重试失败任务和终止未完成任务。
"""

import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.backoffice.deps import get_current_admin
from app.common.audit import log_audit
from app.core.celery_app import celery_app
from app.db.session import get_db
from app.exceptions.http_exceptions import APIException, NotFoundError
from app.models.admin import Admin
from app.models.media_tool import MediaFile, MediaTask
from app.schemas.response import ApiResponse
from app.services.media import MediaEventRepository, MediaFileRepository, MediaTaskRepository

logger = logging.getLogger(__name__)

router = APIRouter()


def _parse_input_file_ids(value: Any) -> list[int]:
    if isinstance(value, list):
        return [int(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return [int(item) for item in parsed]
    return []


def _serialize_file_meta(file_record: Optional[MediaFile]) -> Optional[dict]:
    if not file_record:
        return None
    return {
        "id": file_record.id,
        "user_id": file_record.user_id,
        "original_name": file_record.original_name,
        "media_type": file_record.media_type,
        "source_format": file_record.source_format,
        "size_bytes": file_record.size_bytes,
        "duration_ms": file_record.duration_ms,
        "created_at": file_record.created_at.isoformat() if file_record.created_at else None,
        "expires_at": file_record.expires_at.isoformat() if file_record.expires_at else None,
    }


async def _serialize_admin_task(db: AsyncSession, task: MediaTask) -> dict:
    input_file_ids = _parse_input_file_ids(task.input_file_ids)
    output_file = None
    if task.output_file_id:
        output_file = await MediaFileRepository.get_by_id_admin(db, task.output_file_id)

    return {
        "id": task.id,
        "user_id": task.user_id,
        "tool_code": task.tool_name,
        "status": task.status,
        "progress": task.progress,
        "input_file_ids": input_file_ids,
        "output_file": _serialize_file_meta(output_file),
        "error_code": task.error_code,
        "error_message": task.error_message,
        "retry_count": task.retry_count,
        "celery_task_id": task.celery_task_id,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }


@router.get("")
async def list_media_tasks_admin(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    tool_code: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None, ge=1),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """管理员查询媒体任务列表。"""
    result = await MediaTaskRepository.list_admin(
        db,
        page=page,
        size=size,
        status=status,
        tool_name=tool_code,
        user_id=user_id,
    )
    items = [await _serialize_admin_task(db, task) for task in result["items"]]
    return ApiResponse.success(
        data={
            "items": items,
            "total": result["total"],
            "page": result["page"],
            "size": result["size"],
            "has_more": result["has_more"],
        }
    )


@router.post("/{task_id}/retry")
async def retry_media_task_admin(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """管理员重试失败媒体任务。"""
    task = await MediaTaskRepository.retry_task_admin(db, task_id)
    try:
        from app.schedule.jobs.media_tasks import process_media_task

        celery_result = process_media_task.delay(task.id)
        await MediaTaskRepository.update_status(
            db=db,
            task_id=task.id,
            status="pending",
            celery_task_id=celery_result.id,
        )
        task.celery_task_id = celery_result.id
    except Exception as exc:
        logger.exception("后台媒体任务重试提交失败: task_id=%s", task.id)
        await MediaTaskRepository.update_status(
            db=db,
            task_id=task.id,
            status="failed",
            error_code="CELERY_SUBMIT_FAILED",
            error_message="后台任务重新提交失败，请稍后重试",
        )
        raise APIException(code=10503, message="后台任务重新提交失败，请稍后重试", status_code=503) from exc

    await MediaEventRepository.create(
        db=db,
        task_id=task.id,
        user_id=task.user_id,
        event_name="task_admin_retry",
        payload_json={"admin_id": current_admin.id, "retry_count": task.retry_count},
    )
    await log_audit(
        db,
        current_admin.id,
        "retry",
        "media_task",
        task.id,
        f"重试媒体任务: task_id={task.id}, user_id={task.user_id}",
    )
    return ApiResponse.success(
        data={"task_id": task.id, "status": task.status, "retry_count": task.retry_count},
        message="任务已重新提交",
    )


@router.post("/{task_id}/terminate")
async def terminate_media_task_admin(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """管理员终止 pending/processing 媒体任务。"""
    task = await MediaTaskRepository.get_by_id_admin(db, task_id)
    if not task:
        raise NotFoundError(message="任务不存在")
    celery_task_id = task.celery_task_id
    if celery_task_id:
        try:
            celery_app.control.revoke(celery_task_id, terminate=True, signal="SIGTERM")
        except Exception:
            logger.warning("Celery revoke 失败，将仅标记任务为 cancelled: task_id=%s", task.id, exc_info=True)

    task = await MediaTaskRepository.terminate_task_admin(db, task_id)
    await MediaEventRepository.create(
        db=db,
        task_id=task.id,
        user_id=task.user_id,
        event_name="task_admin_terminated",
        payload_json={"admin_id": current_admin.id, "celery_task_id": celery_task_id},
    )
    await log_audit(
        db,
        current_admin.id,
        "terminate",
        "media_task",
        task.id,
        f"终止媒体任务: task_id={task.id}, user_id={task.user_id}",
    )
    return ApiResponse.success(data={"task_id": task.id, "status": task.status}, message="任务已终止")
