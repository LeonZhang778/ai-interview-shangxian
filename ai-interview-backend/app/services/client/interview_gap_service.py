"""岗位描述与简历差距分析服务。"""

import json
import logging
import re
from typing import Any, Dict, Optional

from app.services.client.ai_service import AIService
from app.services.common.redis import redis_client
from app.services.common.setting_service import get_setting_bool

logger = logging.getLogger(__name__)

MAX_JOB_DESCRIPTION_LENGTH = 20000
ANALYSIS_VERSION = 1


def empty_gap_analysis() -> Dict[str, Any]:
    return {
        "schema_version": ANALYSIS_VERSION,
        "overall_match_score": 0,
        "responsibilities": [],
        "required_skills": [],
        "preferred_skills": [],
        "resume_gaps": [],
        "question_plan": [],
        "limitations": [],
    }


def normalize_job_description(value: Optional[str]) -> str:
    if not value:
        return ""
    # 保留段落换行，同时压缩复制 JD 常见的重复空格和空行。
    text = re.sub(r"[ \t]+", " ", value.replace("\r\n", "\n")).strip()
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:MAX_JOB_DESCRIPTION_LENGTH]


def _list(value: Any, limit: int = 20) -> list:
    return value[:limit] if isinstance(value, list) else []


def _bounded_int(value: Any, default: int = 1, minimum: int = 1, maximum: int = 3) -> int:
    try:
        return max(minimum, min(maximum, int(value)))
    except (TypeError, ValueError):
        return default


def normalize_gap_analysis(value: Any) -> Dict[str, Any]:
    """把模型输出限制为前端和报告可以安全消费的结构。"""
    if not isinstance(value, dict):
        return empty_gap_analysis()

    result = empty_gap_analysis()
    try:
        score = float(value.get("overall_match_score", 0))
        result["overall_match_score"] = max(0, min(100, round(score)))
    except (TypeError, ValueError):
        pass

    result["responsibilities"] = _list(value.get("responsibilities"))
    for field in ("required_skills", "preferred_skills"):
        items = []
        for item in _list(value.get(field)):
            if not isinstance(item, dict) or not str(item.get("name", "")).strip():
                continue
            status = item.get("resume_status")
            if status not in {"matched", "partial", "missing", "unknown"}:
                status = "unknown"
            try:
                confidence = max(0.0, min(1.0, float(item.get("confidence", 0))))
            except (TypeError, ValueError):
                confidence = 0.0
            items.append({
                "name": str(item["name"]).strip()[:120],
                "priority": str(item.get("priority", "medium"))[:20],
                "resume_status": status,
                "evidence": [str(x)[:300] for x in _list(item.get("evidence"), 5)],
                "confidence": round(confidence, 2),
            })
        result[field] = items

    result["resume_gaps"] = [
        {
            "skill": str(item.get("skill", "")).strip()[:120],
            "gap_type": str(item.get("gap_type", "missing"))[:40],
            "severity": str(item.get("severity", "medium"))[:20],
            "reason": str(item.get("reason", ""))[:500],
            "practice_action": str(item.get("practice_action", ""))[:500],
        }
        for item in _list(value.get("resume_gaps"))
        if isinstance(item, dict) and str(item.get("skill", "")).strip()
    ]
    result["question_plan"] = [
        {
            "skill": str(item.get("skill", "")).strip()[:120],
            "requirement_type": str(item.get("requirement_type", "required"))[:20],
            "focus": str(item.get("focus", ""))[:300],
            "question_type": str(item.get("question_type", "technical"))[:30],
            "priority": str(item.get("priority", "medium"))[:20],
            "question_count": _bounded_int(item.get("question_count", 1)),
        }
        for item in _list(value.get("question_plan"))
        if isinstance(item, dict) and str(item.get("skill", "")).strip()
    ]
    result["limitations"] = [str(x)[:300] for x in _list(value.get("limitations"), 10)]
    return result


class InterviewGapService:
    @staticmethod
    async def enabled() -> bool:
        return await get_setting_bool("job_gap_analysis_enabled", True)

    @staticmethod
    async def analyze(
        parsed_resume: Dict[str, Any], target_position: str, job_description: Optional[str]
    ) -> tuple[str, Optional[Dict[str, Any]]]:
        jd = normalize_job_description(job_description)
        if not jd:
            return "not_requested", None
        try:
            if not await InterviewGapService.enabled():
                return "disabled", None
            cache_content = json.dumps(
                {
                    "version": ANALYSIS_VERSION,
                    "target_position": (target_position or "").strip(),
                    "job_description": jd,
                    "resume": parsed_resume or {},
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            cached = await redis_client.get_llm_cache("job_gap", cache_content)
            if cached:
                return "ready", normalize_gap_analysis(cached)
            result = await AIService.analyze_job_gap(parsed_resume, target_position, jd)
            normalized = normalize_gap_analysis(result)
            await redis_client.set_llm_cache("job_gap", cache_content, normalized, ttl=3600)
            return "ready", normalized
        except Exception as exc:
            logger.warning("岗位差距分析失败，将回退通用面试: %s", exc)
            return "failed", empty_gap_analysis()


interview_gap_service = InterviewGapService()
