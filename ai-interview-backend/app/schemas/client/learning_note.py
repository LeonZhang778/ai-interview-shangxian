from typing import Optional, List
from pydantic import Field
from ..base import BaseSchema


class LearningNoteCreate(BaseSchema):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(default="", max_length=50000)
    note_type: str = Field(default="note")  # note/experience/mistake/review/material
    visibility: str = Field(default="private")  # private/public
    status: str = Field(default="draft")  # draft/published
    tags: Optional[str] = Field(default=None, max_length=500)
    interview_id: Optional[int] = None


class LearningNoteUpdate(BaseSchema):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    content: Optional[str] = Field(default=None, max_length=50000)
    note_type: Optional[str] = None
    visibility: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[str] = Field(default=None, max_length=500)


class LearningNoteFromInterview(BaseSchema):
    """从 AI 面试报告生成学习笔记草稿"""
    interview_id: int
    title: Optional[str] = None
    note_type: str = Field(default="review")  # review/mistake
    visibility: str = Field(default="private")


class LearningNoteListItem(BaseSchema):
    id: int
    title: str
    note_type: str
    visibility: str
    status: str
    tags: Optional[str] = None
    source: str = "manual"
    interview_id: Optional[int] = None
    view_count: int = 0
    like_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class LearningNoteDetail(BaseSchema):
    id: int
    title: str
    content: str
    note_type: str
    visibility: str
    status: str
    tags: Optional[str] = None
    source: str = "manual"
    interview_id: Optional[int] = None
    view_count: int = 0
    like_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
