from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.api.backoffice.deps import get_current_admin
from app.models.admin import Admin
from app.models.setting import SystemSetting
from app.schemas.response import ApiResponse
from app.services.common.setting_service import invalidate_settings_cache

router = APIRouter()


class SettingItem(BaseModel):
    key: str
    value: Optional[str] = None


class SettingsBatchUpdate(BaseModel):
    settings: List[SettingItem]


@router.get("")
async def get_all_settings(
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """获取所有系统设置"""
    result = await db.execute(select(SystemSetting).order_by(SystemSetting.id))
    settings = result.scalars().all()

    items = [
        {
            "id": s.id,
            "key": s.key,
            "value": s.value,
            "description": s.description,
        }
        for s in settings
    ]

    return ApiResponse.success(data={"items": items})


@router.put("")
async def batch_update_settings(
    body: SettingsBatchUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """批量更新设置"""
    for item in body.settings:
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == item.key)
        )
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = item.value
        else:
            db.add(SystemSetting(key=item.key, value=item.value))

    await db.commit()
    await invalidate_settings_cache()
    return ApiResponse.success(message="设置已更新")


@router.put("/{key}")
async def update_single_setting(
    key: str,
    body: SettingItem,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """更新单个设置"""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == key)
    )
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = body.value
    else:
        db.add(SystemSetting(key=key, value=body.value))

    await db.commit()
    await invalidate_settings_cache()
    return ApiResponse.success(message="设置已更新")
