from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    criterion_key: str = Field(..., min_length=1, max_length=80)
    quote: str = Field(..., min_length=1, max_length=500)
    claim: str = Field(default="", max_length=300)
    support: Literal["direct", "partial", "inferred"] = "direct"


class DimensionEvaluation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    key: str = Field(..., min_length=1, max_length=80)
    score: float = Field(..., ge=0, le=10)
    rationale: str = Field(default="", max_length=1000)
    evidence: List[EvidenceItem] = Field(default_factory=list, max_length=10)
    missing_criteria: List[str] = Field(default_factory=list, max_length=20)
    improvement_actions: List[str] = Field(default_factory=list, max_length=10)


class StructuredEvaluationOutput(BaseModel):
    """模型返回的结构化评分中间格式。

    顶层 score 会被服务端忽略，最终分数只由 Rubric 权重确定性计算。
    """

    model_config = ConfigDict(extra="ignore")

    rubric_version: Optional[str] = Field(default=None, max_length=64)
    feedback: str = Field(default="", max_length=3000)
    dimension_scores: List[DimensionEvaluation] = Field(..., min_length=1, max_length=20)
    confidence: float = Field(default=0, ge=0, le=1)
