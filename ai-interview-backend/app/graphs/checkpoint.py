"""Redis-backed LangGraph checkpoint lifecycle."""

from __future__ import annotations

from urllib.parse import quote

from langgraph.checkpoint.redis.aio import AsyncRedisSaver

from app.core.config import settings


def build_redis_url(host: str, port: int, password: str, database: int) -> str:
    """Build a Redis URL without exposing credentials in logs."""
    encoded_password = quote(password, safe="")
    auth = f":{encoded_password}@" if password else ""
    return f"redis://{auth}{host}:{port}/{database}"


class RedisCheckpointManager:
    """Own one async Redis checkpoint saver per API worker process."""

    def __init__(self) -> None:
        self.redis_url = build_redis_url(
            settings.REDIS_HOST,
            settings.REDIS_PORT,
            settings.REDIS_PASSWORD,
            settings.REDIS_CHECKPOINT_DB,
        )
        self.ttl = {
            "default_ttl": settings.LANGGRAPH_CHECKPOINT_TTL_MINUTES,
            "refresh_on_read": True,
        }
        self.saver = AsyncRedisSaver(
            redis_url=self.redis_url,
            ttl=self.ttl,
            checkpoint_prefix="ai_interview_checkpoint",
            checkpoint_write_prefix="ai_interview_checkpoint_write",
        )
        self._started = False

    async def start(self) -> AsyncRedisSaver:
        """Connect, create indexes, and make the saver ready for graph calls."""
        if not self._started:
            await self.saver.__aenter__()
            self._started = True
        return self.saver

    async def stop(self) -> None:
        """Close the saver connection during application shutdown."""
        if self._started:
            await self.saver.__aexit__(None, None, None)
            self._started = False


redis_checkpoint_manager = RedisCheckpointManager()
