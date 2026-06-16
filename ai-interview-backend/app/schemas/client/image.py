from typing import Optional, List
from pydantic import Field
from ..base import BaseSchema


class ImageGenerate(BaseSchema):
    prompt: str = Field(..., min_length=1, max_length=2000, description="正向提示词")
    negative_prompt: Optional[str] = Field(None, max_length=2000, description="反向提示词")
    width: int = Field(default=512, ge=256, le=1024, description="图片宽度")
    height: int = Field(default=512, ge=256, le=1024, description="图片高度")
    steps: int = Field(default=20, ge=1, le=50, description="生成步数")
    cfg_scale: int = Field(default=7, ge=1, le=20, description="CFG Scale")


class ImageTaskResponse(BaseSchema):
    id: int
    prompt: str
    negative_prompt: Optional[str] = None
    width: int = 512
    height: int = 512
    steps: int = 20
    cfg_scale: int = 7
    status: str = "pending"
    image_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
