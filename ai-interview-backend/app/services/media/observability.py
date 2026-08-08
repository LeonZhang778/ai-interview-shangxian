"""媒体工具箱轻量可观测性工具。"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("media.observability")


def hash_user_id(user_id: Optional[int]) -> Optional[str]:
    """对用户 ID 做稳定脱敏，避免日志直接暴露用户标识。"""
    if user_id is None:
        return None
    return hashlib.sha256(str(user_id).encode("utf-8")).hexdigest()[:16]


def build_media_event_payload(
    *,
    event: str,
    task_id: Optional[int] = None,
    file_id: Optional[int] = None,
    user_id: Optional[int] = None,
    trace_id: Optional[str] = None,
    tool_name: Optional[str] = None,
    percent: Optional[int] = None,
    duration_ms: Optional[int] = None,
    error_code: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "media-tools",
        "event": event,
    }
    if task_id is not None:
        payload["task_id"] = task_id
    if file_id is not None:
        payload["file_id"] = file_id
    if user_id is not None:
        payload["user_id_hash"] = hash_user_id(user_id)
    if trace_id:
        payload["trace_id"] = trace_id
    if tool_name:
        payload["tool_name"] = tool_name
    if percent is not None:
        payload["percent"] = percent
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms
    if error_code:
        payload["error_code"] = error_code
    if extra:
        payload.update(extra)
    return payload


def log_media_event(level: str = "info", **kwargs: Any) -> dict[str, Any]:
    """输出结构化媒体事件日志，并返回实际 payload 供事件表复用。"""
    payload = build_media_event_payload(**kwargs)
    log_fn = getattr(logger, level, logger.info)
    log_fn("MEDIA_EVENT: %s", json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return payload


def log_media_metric(name: str, value: float, labels: Optional[dict[str, Any]] = None) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "media-tools",
        "metric": name,
        "value": value,
        "labels": labels or {},
    }
    logger.info("MEDIA_METRIC: %s", json.dumps(payload, ensure_ascii=False, sort_keys=True))


def log_media_alert(name: str, severity: str = "warning", **kwargs: Any) -> None:
    extra = dict(kwargs.pop("extra", {}) or {})
    extra.setdefault("severity", severity)
    payload = build_media_event_payload(event=name, extra=extra, **kwargs)
    logger.error("MEDIA_ALERT: %s", json.dumps(payload, ensure_ascii=False, sort_keys=True))
