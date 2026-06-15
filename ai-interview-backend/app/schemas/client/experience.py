from typing import Optional, List
from pydantic import Field
from ..base import BaseSchema


class ExperienceListItem(BaseSchema):
    id: int
    title: str
    company: str
    position: str
    level: Optional[str] = None
    round: Optional[str] = None
    summary: Optional[str] = None
    view_count: int = 0
    like_count: int = 0
    collect_count: int = 0
    tags: List[str] = []
    created_at: Optional[str] = None


class ExperienceDetail(BaseSchema):
    id: int
    title: str
    company: str
    position: str
    level: Optional[str] = None
    round: Optional[str] = None
    content: str
    summary: Optional[str] = None
    view_count: int = 0
    like_count: int = 0
    collect_count: int = 0
    is_anonymous: bool = True
    author_name: Optional[str] = None
    tags: List[str] = []
    related: List[ExperienceListItem] = []
    created_at: Optional[str] = None


class ExperienceFilter(BaseSchema):
    company: Optional[str] = None
    position: Optional[str] = None
    level: Optional[str] = None
    round: Optional[str] = None
    sort: str = "latest"  # latest/popular/collected
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=50)
