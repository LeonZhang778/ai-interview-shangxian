"""System settings service with Redis caching."""
import json
import logging
from sqlalchemy import select
from app.models.setting import SystemSetting
from app.db.base import get_session_local
from app.services.common.redis import redis_client

logger = logging.getLogger(__name__)

CACHE_KEY = "system_settings"
CACHE_TTL = 60  # seconds


async def get_all_settings() -> dict:
    """Get all settings as a dict, with Redis cache."""
    try:
        cached = await redis_client.get(CACHE_KEY)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    SessionLocal = get_session_local()
    async with SessionLocal() as db:
        result = await db.execute(select(SystemSetting))
        settings = result.scalars().all()
        data = {s.key: s.value for s in settings}

    try:
        await redis_client.set_with_ttl(CACHE_KEY, json.dumps(data), CACHE_TTL)
    except Exception:
        pass

    return data


async def get_setting(key: str, default: str = "") -> str:
    """Get a single setting value."""
    data = await get_all_settings()
    return data.get(key, default)


async def get_setting_bool(key: str, default: bool = True) -> bool:
    """Get a setting as boolean."""
    val = await get_setting(key, str(default).lower())
    return str(val).lower() in ("true", "1", "yes")


async def invalidate_settings_cache():
    """Clear the settings cache (call after updating settings)."""
    try:
        await redis_client.delete(CACHE_KEY)
    except Exception:
        pass
