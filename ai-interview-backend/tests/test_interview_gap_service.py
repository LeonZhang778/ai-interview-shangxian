import asyncio
import importlib

gap_module = importlib.import_module("app.services.client.interview_gap_service")
from app.services.client.interview_gap_service import (
    InterviewGapService,
    normalize_gap_analysis,
    normalize_job_description,
)


def test_normalize_job_description_keeps_content_bounded():
    value = "  Python   后端\r\n\r\n\r\n  Redis  "
    assert normalize_job_description(value) == "Python 后端\n\nRedis"
    assert len(normalize_job_description("x" * 30000)) == 20000


def test_normalize_gap_analysis_handles_malformed_fields():
    result = normalize_gap_analysis(
        {
            "overall_match_score": "120",
            "required_skills": [
                {
                    "name": " PostgreSQL ",
                    "resume_status": "invalid",
                    "confidence": "bad",
                    "evidence": "not-a-list",
                }
            ],
            "resume_gaps": [{"skill": "Redis", "question_count": "bad"}],
            "question_plan": [{"skill": "Redis", "question_count": "bad"}],
        }
    )

    assert result["overall_match_score"] == 100
    assert result["required_skills"][0]["resume_status"] == "unknown"
    assert result["required_skills"][0]["confidence"] == 0
    assert result["question_plan"][0]["question_count"] == 1


def test_analyze_failure_does_not_block_interview(monkeypatch):
    async def enabled():
        return True

    async def broken(*args, **kwargs):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(InterviewGapService, "enabled", enabled)
    monkeypatch.setattr(gap_module.AIService, "analyze_job_gap", broken)
    monkeypatch.setattr(gap_module.redis_client, "get_llm_cache", lambda *a, **k: asyncio.sleep(0, result=None))

    async def no_write(*args, **kwargs):
        return None

    monkeypatch.setattr(gap_module.redis_client, "set_llm_cache", no_write)
    status, analysis = asyncio.run(
        gap_module.interview_gap_service.analyze(
            {"skills": ["Python"]}, "后端开发", "需要 Python 和 Redis"
        )
    )

    assert status == "failed"
    assert analysis["resume_gaps"] == []
