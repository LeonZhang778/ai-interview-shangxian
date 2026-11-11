import re
from typing import Any

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.schemas.base import BaseSchema


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, dict):
        if "value" in value:
            return _to_text(value["value"])
        parts = []
        for key, item in value.items():
            text = _to_text(item)
            if text:
                parts.append(f"{key}: {text}")
        return "; ".join(parts)
    if isinstance(value, list):
        return "\n".join(text for item in value if (text := _to_text(item)))
    raise ValueError("简历字段必须是文本、列表或对象")


def _to_text_list(value: Any, *, split_string: bool = False) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (str, dict, list)):
        raise ValueError("简历列表字段必须是文本、列表或对象")

    items = value if isinstance(value, list) else [value]
    result = []
    for item in items:
        text = _to_text(item)
        if not text:
            continue
        if split_string:
            result.extend(part.strip() for part in re.split(r"[、,，;；\n]+", text) if part.strip())
        else:
            result.append(text)
    return result


class ParsedResume(BaseSchema):
    """Validated and normalized resume fields returned by the parsing model."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    name: str = ""
    education: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    summary: str = ""

    @field_validator("name", "education", "summary", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: Any) -> str:
        return _to_text(value)

    @field_validator("skills", mode="before")
    @classmethod
    def normalize_skills(cls, value: Any) -> list[str]:
        return _to_text_list(value, split_string=True)

    @field_validator("experience", "projects", mode="before")
    @classmethod
    def normalize_entry_lists(cls, value: Any) -> list[str]:
        return _to_text_list(value)

    @model_validator(mode="after")
    def require_some_resume_content(self):
        if not any((self.name, self.education, self.skills, self.experience, self.projects, self.summary)):
            raise ValueError("模型没有提取出任何简历字段")
        return self
