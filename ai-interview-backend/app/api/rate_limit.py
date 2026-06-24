import logging

from app.core.config import settings
from app.exceptions.http_exceptions import APIException
from app.models.user import User
from app.services.common.redis import redis_client

logger = logging.getLogger(__name__)


def make_rate_limiter(scope: str):
    """Create a user-scoped sliding-window rate limit checker."""

    async def check_rate_limit(current_user: User) -> None:
        key = f"{current_user.id}:{scope}"
        allowed = await redis_client.sliding_window_check(
            user_id=key,
            limit=settings.RATE_LIMIT_REQUESTS,
            window=settings.RATE_LIMIT_WINDOW,
        )
        if not allowed:
            logger.warning("用户 %s 触发接口限流: %s", current_user.id, scope)
            raise APIException(
                code=42901,
                status_code=429,
                message="请求过于频繁，请稍后再试",
            )

    return check_rate_limit


check_ai_rate_limit = make_rate_limiter("ai")
