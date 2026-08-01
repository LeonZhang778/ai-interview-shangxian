"""笔记模板 API 路由。"""

from fastapi import APIRouter
from app.schemas.response import ApiResponse
from app.services.client.note_template import get_templates, get_template

router = APIRouter()


@router.get("/templates")
async def get_note_templates():
    """获取所有笔记模板列表（不含正文）"""
    return ApiResponse.success(data={"templates": get_templates()})


@router.get("/templates/{template_id}")
async def get_template_detail(template_id: str):
    """获取模板详情（含 Markdown 正文）"""
    t = get_template(template_id)
    if not t:
        return ApiResponse.failed(message="模板不存在", body_code=404)
    return ApiResponse.success(data={
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "icon": t.icon,
        "note_type": t.note_type,
        "markdown": t.markdown,
    })