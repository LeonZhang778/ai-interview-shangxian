import hashlib
import json
import logging
import time
import uuid
from redis.asyncio import Redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self):
        # 构建Redis连接参数
        redis_params = {
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "decode_responses": True
        }

        # 只有当密码不为空时才添加密码参数
        if hasattr(settings, "REDIS_PASSWORD") and settings.REDIS_PASSWORD:
            redis_params["password"] = settings.REDIS_PASSWORD

        self.redis = Redis(**redis_params)

    # === 基础操作 ===

    async def set_with_ttl(self, key: str, value: str, ttl_seconds: int):
        """设置键值对，带过期时间"""
        await self.redis.setex(key, ttl_seconds, value)

    async def get(self, key: str) -> str:
        """获取值"""
        return await self.redis.get(key)

    async def delete(self, key: str):
        """删除键"""
        await self.redis.delete(key)

    async def incr_with_ttl(self, key: str, ttl_seconds: int) -> int:
        """原子自增，并仅在该 key 首次创建时设置过期时间；返回自增后的值。

        用于登录失败计数：自增必须原子（并发的失败请求不能互相覆盖），
        且 TTL 只在第一次写入时设置 —— 否则每次失败都会续期，计数永远不释放，
        账号会被永久锁死。
        """
        value = await self.redis.incr(key)
        if value == 1:
            await self.redis.expire(key, ttl_seconds)
        return int(value)

    async def set_cooldown(self, key: str, ttl_seconds: int):
        """设置冷却时间"""
        await self.redis.setex(key, ttl_seconds, "1")

    async def check_cooldown(self, key: str) -> bool:
        """检查是否在冷却中"""
        return bool(await self.redis.exists(key))

    def pipeline(self, *args, **kwargs):
        """
        兼容原生redis-py的pipeline用法，直接转发到底层redis实例。
        注意：如果底层用的是redis.asyncio.Redis，返回的是异步pipeline。
        """
        return self.redis.pipeline(*args, **kwargs)

    async def brpop(self, key, timeout=1):
        return await self.redis.brpop(key, timeout=timeout)

    async def close(self):
        """关闭Redis连接"""
        await self.redis.close()

    # === Sorted Set 操作（限流用）===

    async def zadd(self, key: str, mapping: dict):
        """向 Sorted Set 添加元素"""
        return await self.redis.zadd(key, mapping)

    async def zcard(self, key: str) -> int:
        """获取 Sorted Set 元素数量"""
        return await self.redis.zcard(key)

    async def zrem(self, key: str, *members):
        """从 Sorted Set 移除元素"""
        return await self.redis.zrem(key, *members)

    async def zremrangebyscore(self, key: str, min_score: float, max_score: float):
        """按分数范围移除 Sorted Set 元素"""
        return await self.redis.zremrangebyscore(key, min_score, max_score)

    # === 滑动窗口限流 ===

    async def sliding_window_check(self, user_id: str, limit: int = 30, window: int = 60) -> bool:
        """
        滑动窗口限流检查

        Args:
            user_id: 用户标识
            limit: 窗口内最大请求数
            window: 窗口时间（秒）

        Returns:
            True: 允许请求, False: 超出限制
        """
        key = f"ratelimit:{user_id}"
        now = time.time()
        request_id = str(uuid.uuid4())

        pipe = self.redis.pipeline()
        # 移除窗口外的旧记录
        pipe.zremrangebyscore(key, 0, now - window)
        # 添加当前请求
        pipe.zadd(key, {request_id: now})
        # 统计窗口内请求数
        pipe.zcard(key)
        # 设置 key 过期时间
        pipe.expire(key, window)
        results = await pipe.execute()

        current_count = results[2]
        if current_count > limit:
            # 超出限制，移除刚添加的记录
            await self.redis.zrem(key, request_id)
            logger.warning(f"用户 {user_id} 触发限流: {current_count}/{limit} in {window}s")
            return False
        return True

    # === LLM 缓存 ===

    def llm_cache_key(self, prefix: str, content: str) -> str:
        """生成 LLM 缓存 key"""
        return f"llm:{prefix}:{hashlib.md5(content.encode()).hexdigest()}"

    async def get_llm_cache(self, prefix: str, content: str) -> dict | None:
        """
        获取 LLM 缓存

        Args:
            prefix: 缓存前缀（如 evaluate, parse, questions）
            content: 缓存内容（用于生成 hash）

        Returns:
            缓存的 dict 或 None
        """
        key = self.llm_cache_key(prefix, content)
        cached = await self.get(key)
        if cached:
            logger.info(f"[LLM缓存命中] {prefix}")
            return json.loads(cached)
        return None

    async def set_llm_cache(self, prefix: str, content: str, result: dict, ttl: int = 3600):
        """
        设置 LLM 缓存

        Args:
            prefix: 缓存前缀
            content: 缓存内容（用于生成 hash）
            result: 要缓存的结果
            ttl: 过期时间（秒），默认 1 小时
        """
        key = self.llm_cache_key(prefix, content)
        import random
        # 加随机偏移防雪崩
        ttl = ttl + random.randint(0, 60)
        await self.set_with_ttl(key, json.dumps(result, ensure_ascii=False), ttl)
        logger.info(f"[LLM缓存设置] {prefix}, TTL={ttl}s")


redis_client = RedisClient()
