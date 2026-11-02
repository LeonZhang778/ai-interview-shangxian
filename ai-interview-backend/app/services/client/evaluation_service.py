"""版本化 Rubric 和结构化面试评分服务。"""

import copy
import json
import logging
import math
from typing import Any, Dict, Optional

from pydantic import ValidationError as PydanticValidationError

from app.schemas.client.evaluation import StructuredEvaluationOutput
from app.services.common.setting_service import get_setting

logger = logging.getLogger(__name__)

RUBRIC_SETTING_KEY = "interview_scoring_rubric"

DEFAULT_RUBRIC: Dict[str, Any] = {
    "version": "backend-v1",
    "scale": {"min_score": 1, "max_score": 10},
    "dimensions": [
        {
            "key": "technical_accuracy",
            "name": "技术准确性",
            "weight": 0.35,
            "max_score": 10,
            "applicable_categories": ["technical", "coding", "system-design", "project"],
            "definition": "技术概念、机制和结论是否正确",
            "required_evidence": [
                {"key": "core_concept", "description": "能够正确解释核心概念或机制"},
                {"key": "boundary_condition", "description": "能够说明边界条件、限制或异常情况"},
            ],
            "deductions": ["关键概念错误", "忽略明显边界条件"],
        },
        {
            "key": "reasoning",
            "name": "分析与推理",
            "weight": 0.25,
            "max_score": 10,
            "applicable_categories": ["technical", "coding", "system-design", "project"],
            "definition": "是否能说明判断过程、因果关系和技术取舍",
            "required_evidence": [
                {"key": "reasoning_chain", "description": "能够说明从问题到结论的推理过程"},
                {"key": "tradeoff", "description": "能够说明方案选择或技术取舍"},
            ],
            "deductions": ["只给结论不解释原因", "技术选型没有取舍依据"],
        },
        {
            "key": "evidence",
            "name": "项目证据",
            "weight": 0.2,
            "max_score": 10,
            "applicable_categories": ["project", "behavioral", "system-design"],
            "definition": "是否能够使用真实项目、数据或结果证明能力",
            "required_evidence": [
                {"key": "concrete_example", "description": "能够提供具体项目、场景或个人负责内容"},
                {"key": "result", "description": "能够说明结果、影响或验证方式"},
            ],
            "deductions": ["只有抽象描述没有实例", "无法说明个人负责内容"],
        },
        {
            "key": "communication",
            "name": "表达与结构",
            "weight": 0.2,
            "max_score": 10,
            "applicable_categories": ["*"],
            "definition": "回答是否清晰、完整、有结构",
            "required_evidence": [{"key": "structure", "description": "回答具有清晰的先后结构"}],
            "deductions": ["回答严重偏题", "信息堆叠但缺乏结构"],
        },
    ],
    "fallback": {
        "default_score": 5,
        "confidence": 0,
        "feedback": "AI 暂时不可用，已使用基础评分。",
    },
}


class InvalidRubricError(ValueError):
    pass


class InvalidEvaluationError(ValueError):
    pass


def _copy_default() -> Dict[str, Any]:
    return copy.deepcopy(DEFAULT_RUBRIC)


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


class EvaluationService:
    @staticmethod
    def validate_rubric(value: Any) -> Dict[str, Any]:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (TypeError, json.JSONDecodeError) as exc:
                raise InvalidRubricError("评分 Rubric 不是有效 JSON") from exc
        if not isinstance(value, dict):
            raise InvalidRubricError("评分 Rubric 必须是 JSON 对象")

        rubric = copy.deepcopy(value)
        version = str(rubric.get("version", "")).strip()
        dimensions = rubric.get("dimensions")
        if not version or not isinstance(dimensions, list) or len(dimensions) < 2:
            raise InvalidRubricError("Rubric 必须包含 version 和至少两个 dimensions")

        scale = rubric.get("scale") or {}
        min_score = scale.get("min_score", 1)
        max_score = scale.get("max_score", 10)
        if not _finite_number(min_score) or not _finite_number(max_score) or min_score >= max_score:
            raise InvalidRubricError("Rubric 分数范围无效")
        rubric["scale"] = {"min_score": float(min_score), "max_score": float(max_score)}

        seen = set()
        total_weight = 0.0
        normalized_dimensions = []
        for item in dimensions:
            if not isinstance(item, dict):
                raise InvalidRubricError("Rubric dimension 必须是对象")
            key = str(item.get("key", "")).strip()
            if not key or key in seen:
                raise InvalidRubricError("Rubric dimension key 不能为空且不能重复")
            seen.add(key)
            weight = item.get("weight")
            dimension_max = item.get("max_score", max_score)
            if not _finite_number(weight) or float(weight) <= 0:
                raise InvalidRubricError(f"Rubric dimension {key} 的 weight 无效")
            if not _finite_number(dimension_max) or float(dimension_max) <= 0:
                raise InvalidRubricError(f"Rubric dimension {key} 的 max_score 无效")
            criteria = item.get("required_evidence", [])
            if not isinstance(criteria, list):
                raise InvalidRubricError(f"Rubric dimension {key} 的 required_evidence 无效")
            criterion_keys = set()
            normalized_criteria = []
            for criterion in criteria:
                if not isinstance(criterion, dict):
                    raise InvalidRubricError(f"Rubric dimension {key} 的 evidence criterion 无效")
                criterion_key = str(criterion.get("key", "")).strip()
                description = str(criterion.get("description", "")).strip()
                if not criterion_key or criterion_key in criterion_keys or not description:
                    raise InvalidRubricError(f"Rubric dimension {key} 的 evidence criterion 无效")
                criterion_keys.add(criterion_key)
                normalized_criteria.append({"key": criterion_key, "description": description[:300]})
            normalized = copy.deepcopy(item)
            normalized.update(
                {
                    "key": key,
                    "weight": float(weight),
                    "max_score": float(dimension_max),
                    "name": str(item.get("name", key))[:100],
                    "applicable_categories": item.get("applicable_categories") or ["*"],
                    "required_evidence": normalized_criteria,
                    "deductions": [str(x)[:300] for x in (item.get("deductions") or [])][:20],
                }
            )
            total_weight += float(weight)
            normalized_dimensions.append(normalized)

        if total_weight <= 0:
            raise InvalidRubricError("Rubric 权重总和必须大于 0")
        for index, item in enumerate(normalized_dimensions):
            item["weight"] = item["weight"] / total_weight
            if index == len(normalized_dimensions) - 1:
                item["weight"] = max(0.0, 1.0 - sum(x["weight"] for x in normalized_dimensions[:-1]))
        rubric["dimensions"] = normalized_dimensions
        fallback = rubric.get("fallback") or {}
        fallback_score = fallback.get("default_score", 5)
        if not _finite_number(fallback_score):
            fallback_score = 5
        rubric["fallback"] = {
            "default_score": max(float(min_score), min(float(max_score), float(fallback_score))),
            "confidence": 0,
            "feedback": str(fallback.get("feedback", "AI 暂时不可用，已使用基础评分。"))[:500],
        }
        return rubric

    @staticmethod
    async def get_current_rubric() -> Dict[str, Any]:
        try:
            raw = await get_setting(RUBRIC_SETTING_KEY, "")
            return EvaluationService.validate_rubric(raw or _copy_default())
        except Exception as exc:
            logger.error("系统评分 Rubric 读取或校验失败，使用内置默认版本: %s", exc)
            return EvaluationService.validate_rubric(_copy_default())

    @staticmethod
    def applicable_dimensions(rubric: Dict[str, Any], category: Optional[str]) -> list[dict]:
        category = (category or "").strip().lower()
        dimensions = []
        for dimension in rubric["dimensions"]:
            categories = {str(x).lower() for x in dimension.get("applicable_categories", ["*"])}
            if "*" in categories or not category or category in categories:
                dimensions.append(dimension)
        return dimensions or list(rubric["dimensions"])

    @staticmethod
    def _weighted_score(rubric: Dict[str, Any], dimension_scores: list[dict]) -> float:
        if not dimension_scores:
            return 0.0
        weight_total = sum(float(item["weight"]) for item in dimension_scores)
        if weight_total <= 0:
            return 0.0
        score = sum(
            (float(item["score"]) / float(item["max_score"]) * 10)
            * (float(item["weight"]) / weight_total)
            for item in dimension_scores
        )
        return round(max(1.0, min(10.0, score)), 1)

    @staticmethod
    def fallback(
        rubric: Dict[str, Any],
        answer: str,
        category: Optional[str],
        feedback: Optional[str] = None,
        fallback_level: int = 3,
        skip_type: Optional[str] = None,
        score_override: Optional[float] = None,
    ) -> Dict[str, Any]:
        dimensions = EvaluationService.applicable_dimensions(rubric, category)
        fallback_score = float(
            score_override if score_override is not None else rubric["fallback"]["default_score"]
        )
        fallback_score = max(float(rubric["scale"]["min_score"]), min(10.0, fallback_score))
        result_dimensions = []
        missing = []
        for dimension in dimensions:
            criteria = [
                {"criterion_key": criterion["key"], "description": criterion["description"]}
                for criterion in dimension.get("required_evidence", [])
            ]
            missing.extend(criteria)
            result_dimensions.append(
                {
                    "key": dimension["key"],
                    "name": dimension.get("name", dimension["key"]),
                    "score": fallback_score,
                    "max_score": dimension["max_score"],
                    "weight": dimension["weight"],
                    "weighted_score": 0,
                    "rationale": "未完成结构化评分",
                    "evidence": [],
                    "missing_evidence": criteria,
                    "improvement_actions": ["稍后重新查看详细评分"],
                    "confidence": 0,
                }
            )
        score = EvaluationService._weighted_score(rubric, result_dimensions)
        return {
            "rubric_version": rubric["version"],
            "score": score,
            "feedback": (feedback or rubric["fallback"]["feedback"])[:3000],
            "dimension_scores": result_dimensions,
            "evidence_coverage": 0,
            "confidence": 0,
            "fallback": True,
            "fallback_level": fallback_level,
            "skip_type": skip_type,
        }

    @staticmethod
    def from_legacy_score(
        score: Any,
        rubric: Dict[str, Any],
        category: Optional[str],
        feedback: str,
    ) -> Dict[str, Any]:
        """兼容旧 Prompt 只返回 {score} 的响应，避免升级期间突然降级所有评分。"""
        try:
            numeric_score = float(score)
        except (TypeError, ValueError) as exc:
            raise InvalidEvaluationError("旧版评分不是有效数字") from exc
        dimensions = EvaluationService.applicable_dimensions(rubric, category)
        result_dimensions = []
        for dimension in dimensions:
            bounded = max(rubric["scale"]["min_score"], min(dimension["max_score"], numeric_score))
            missing = [
                {"criterion_key": item["key"], "description": item["description"]}
                for item in dimension.get("required_evidence", [])
            ]
            result_dimensions.append(
                {
                    "key": dimension["key"],
                    "name": dimension.get("name", dimension["key"]),
                    "score": round(bounded, 1),
                    "max_score": dimension["max_score"],
                    "weight": dimension["weight"],
                    "weighted_score": 0,
                    "rationale": "旧版评分响应未提供结构化证据",
                    "evidence": [],
                    "missing_evidence": missing,
                    "improvement_actions": [],
                    "confidence": 0,
                }
            )
        final_score = EvaluationService._weighted_score(rubric, result_dimensions)
        return {
            "rubric_version": rubric["version"],
            "score": final_score,
            "feedback": feedback[:3000],
            "dimension_scores": result_dimensions,
            "evidence_coverage": 0,
            "confidence": 0,
            "fallback": False,
            "legacy": True,
        }

    @staticmethod
    def validate_model_output(
        value: Any,
        rubric: Dict[str, Any],
        answer: str,
        category: Optional[str],
    ) -> Dict[str, Any]:
        try:
            parsed = StructuredEvaluationOutput.model_validate(value)
        except PydanticValidationError as exc:
            raise InvalidEvaluationError("结构化评分字段校验失败") from exc

        dimensions = EvaluationService.applicable_dimensions(rubric, category)
        rubric_map = {item["key"]: item for item in dimensions}
        all_rubric_keys = {item["key"] for item in rubric["dimensions"]}
        model_map = {}
        for item in parsed.dimension_scores:
            if item.key not in all_rubric_keys:
                raise InvalidEvaluationError("结构化评分维度缺失或重复")
            if item.key not in rubric_map:
                continue
            if item.key in model_map:
                raise InvalidEvaluationError("结构化评分维度缺失或重复")
            model_map[item.key] = item
        if set(model_map) != set(rubric_map):
            raise InvalidEvaluationError("结构化评分未覆盖所有适用维度")

        result_dimensions = []
        total_criteria = 0
        verified_criteria = 0
        for key, rubric_dimension in rubric_map.items():
            model_dimension = model_map[key]
            score = float(model_dimension.score)
            max_score = float(rubric_dimension["max_score"])
            if not math.isfinite(score) or score < rubric["scale"]["min_score"] or score > max_score:
                raise InvalidEvaluationError("结构化评分分数越界")
            criteria_map = {item["key"]: item for item in rubric_dimension.get("required_evidence", [])}
            verified = []
            seen_criteria = set()
            for evidence in model_dimension.evidence:
                if evidence.criterion_key not in criteria_map or evidence.criterion_key in seen_criteria:
                    continue
                quote = evidence.quote.strip()
                start = answer.find(quote) if quote else -1
                if start < 0:
                    continue
                seen_criteria.add(evidence.criterion_key)
                verified.append(
                    {
                        "criterion_key": evidence.criterion_key,
                        "quote": quote,
                        "source": "candidate_answer",
                        "start": start,
                        "end": start + len(quote),
                        "claim": evidence.claim[:300],
                        "support": evidence.support,
                        "verified": True,
                    }
                )
            total_criteria += len(criteria_map)
            verified_criteria += len(seen_criteria)
            missing = [
                {"criterion_key": criterion_key, "description": criterion["description"]}
                for criterion_key, criterion in criteria_map.items()
                if criterion_key not in seen_criteria
            ]
            result_dimensions.append(
                {
                    "key": key,
                    "name": rubric_dimension.get("name", key),
                    "score": round(score, 1),
                    "max_score": max_score,
                    "weight": rubric_dimension["weight"],
                    "weighted_score": 0,
                    "rationale": model_dimension.rationale[:1000],
                    "evidence": verified,
                    "missing_evidence": missing,
                    "improvement_actions": [str(x)[:500] for x in model_dimension.improvement_actions][:10],
                    "confidence": round(float(parsed.confidence), 2),
                }
            )

        score = EvaluationService._weighted_score(rubric, result_dimensions)
        for item in result_dimensions:
            item["weighted_score"] = round(
                (item["score"] / item["max_score"] * 10) * item["weight"], 3
            )
        return {
            "rubric_version": rubric["version"],
            "score": score,
            "feedback": parsed.feedback.strip()[:3000],
            "dimension_scores": result_dimensions,
            "evidence_coverage": round(verified_criteria / total_criteria, 2) if total_criteria else 1,
            "confidence": round(float(parsed.confidence), 2),
            "fallback": False,
        }


evaluation_service = EvaluationService()
