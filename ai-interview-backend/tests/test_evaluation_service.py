import pytest

from app.services.client.evaluation_service import (
    DEFAULT_RUBRIC,
    InvalidEvaluationError,
    EvaluationService,
)


def _rubric():
    return EvaluationService.validate_rubric(DEFAULT_RUBRIC)


def test_rubric_weights_are_normalized():
    rubric = EvaluationService.validate_rubric(
        {
            "version": "test-v1",
            "scale": {"min_score": 1, "max_score": 10},
            "dimensions": [
                {"key": "a", "name": "A", "weight": 2, "required_evidence": []},
                {"key": "b", "name": "B", "weight": 1, "required_evidence": []},
            ],
        }
    )
    assert sum(item["weight"] for item in rubric["dimensions"]) == pytest.approx(1.0)
    assert rubric["dimensions"][0]["weight"] == pytest.approx(2 / 3)


def test_structured_evaluation_computes_score_and_verifies_quote():
    rubric = _rubric()
    answer = "我会把热点数据放到 Redis 里，减少数据库查询。"
    raw = {
        "rubric_version": "backend-v1",
        "feedback": "能够说明缓存的基本用途。",
        "confidence": 0.8,
        "dimension_scores": [
            {
                "key": dimension["key"],
                "score": 8,
                "rationale": "回答覆盖了部分要求。",
                "evidence": [
                    {
                        "criterion_key": dimension["required_evidence"][0]["key"],
                        "quote": answer,
                        "claim": "回答提供了直接证据。",
                        "support": "direct",
                    }
                ],
                "missing_criteria": [],
                "improvement_actions": [],
            }
            for dimension in rubric["dimensions"]
        ],
    }
    result = EvaluationService.validate_model_output(raw, rubric, answer, "technical")
    assert result["score"] == pytest.approx(8.0)
    assert result["dimension_scores"][0]["evidence"][0]["verified"] is True
    assert result["dimension_scores"][0]["evidence"][0]["start"] == 0


def test_invalid_quote_becomes_missing_evidence():
    rubric = _rubric()
    answer = "我会使用 Redis。"
    raw = {
        "confidence": 0.5,
        "dimension_scores": [
            {
                "key": dimension["key"],
                "score": 6,
                "rationale": "一般。",
                "evidence": [
                    {
                        "criterion_key": dimension["required_evidence"][0]["key"],
                        "quote": "候选人使用了 Kafka",
                        "claim": "无效引用",
                        "support": "direct",
                    }
                ],
            }
            for dimension in rubric["dimensions"]
        ],
    }
    result = EvaluationService.validate_model_output(raw, rubric, answer, "technical")
    assert result["dimension_scores"][0]["evidence"] == []
    assert result["evidence_coverage"] == 0
    assert result["dimension_scores"][0]["missing_evidence"]


def test_out_of_range_score_is_rejected():
    rubric = _rubric()
    raw = {
        "confidence": 0.5,
        "dimension_scores": [
            {"key": dimension["key"], "score": 11, "evidence": []}
            for dimension in rubric["dimensions"]
        ],
    }
    with pytest.raises(InvalidEvaluationError):
        EvaluationService.validate_model_output(raw, rubric, "回答", "technical")


def test_fallback_preserves_structured_shape():
    result = EvaluationService.fallback(_rubric(), "不会", "technical", fallback_level=2, score_override=3)
    assert result["fallback"] is True
    assert result["score"] == pytest.approx(3.0)
    assert result["dimension_scores"]
    assert result["evidence_coverage"] == 0
