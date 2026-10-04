import logging

from app.core.config import settings
from app.exceptions.http_exceptions import APIException
from app.models.user import User
from app.services.common.redis import redis_client

logger = logging.getLogger(__name__)


def make_rate_limiter(scope: str, limit: int, window: int):
    """构造一个「按用户」的滑动窗口限流依赖。

    Args:
        scope:  限流作用域。不同 scope 各自独立计数，互不影响。
        limit:  窗口内允许的最大请求数。
        window: 窗口长度（秒）。

    一律返回 429 而不是 403：前端 request.js 的响应拦截器把 401/403 当作「登录失效」
    处理，会直接 logout() 并把用户踢回登录页 —— 只是手快多点了两下的用户不该掉线。
    """

    async def check_rate_limit(current_user: User) -> None:
        key = f"{current_user.id}:{scope}"
        allowed = await redis_client.sliding_window_check(
            user_id=key,
            limit=limit,
            window=window,
        )
        if not allowed:
            logger.warning(
                "用户 %s 触发接口限流: scope=%s limit=%s/%ss",
                current_user.id,
                scope,
                limit,
                window,
            )
            raise APIException(
                code=42901,
                status_code=429,
                message="请求过于频繁，请稍后再试",
            )

    return check_rate_limit


# 按单次调用的成本分档（阈值见 app/core/config.py 的 RATE_LIMIT_* 注释）：
#   常规档：面试答题、笔记摘要、标签推荐、面经出题 —— 各自只跑一次 LLM
#   高成本档：简历解析 —— 长文本 + 可能 OCR 兜底，且会落一个后台任务
#   生图档：AI 生图 —— 消耗外部服务配额
check_ai_rate_limit = make_rate_limiter(
    "ai", settings.RATE_LIMIT_REQUESTS, settings.RATE_LIMIT_WINDOW
)
check_heavy_ai_rate_limit = make_rate_limiter(
    "heavy-ai", settings.RATE_LIMIT_HEAVY_REQUESTS, settings.RATE_LIMIT_WINDOW
)
check_image_rate_limit = make_rate_limiter(
    "image", settings.RATE_LIMIT_IMAGE_REQUESTS, settings.RATE_LIMIT_WINDOW
)
