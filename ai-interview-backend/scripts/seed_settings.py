"""Seed system_settings table with default values.

Usage (inside docker container):
    python scripts/seed_settings.py
"""
import asyncio
import json
from app.db.base import get_session_local
from app.models.setting import SystemSetting
from app.services.client.evaluation_service import DEFAULT_RUBRIC
from sqlalchemy import select

DEFAULTS = [
    ("site_name", "智面 AI", "网站名称"),
    ("site_slogan", "AI 驱动的智能模拟面试平台", "标语"),
    ("site_logo", "/uploads/logo.png", "Logo 路径"),
    ("seo_title", "智面 AI — 智能模拟面试平台", "SEO 标题"),
    ("seo_description", "上传简历，AI 自动生成个性化面试题，实时评分反馈，生成综合评估报告", "SEO 描述"),
    ("icp_number", "", "备案号"),
    ("contact_email", "", "联系邮箱"),
    ("maintenance_mode", "false", "维护模式开关"),
    ("register_enabled", "true", "是否开放注册"),
    ("guest_enabled", "true", "是否允许游客模式"),
    ("image_generation_enabled", "true", "AI 生图功能开关"),
    ("job_gap_analysis_enabled", "true", "岗位描述与简历差距分析开关"),
    ("interview_scoring_rubric", json.dumps(DEFAULT_RUBRIC, ensure_ascii=False), "面试评分 Rubric JSON"),
]


async def seed():
    SessionLocal = get_session_local()
    async with SessionLocal() as db:
        for key, value, desc in DEFAULTS:
            result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
            existing = result.scalar_one_or_none()
            if not existing:
                db.add(SystemSetting(key=key, value=value, description=desc))
                print(f"  + {key} = {value}")
            else:
                print(f"  = {key} already exists, skipping")
        await db.commit()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(seed())
