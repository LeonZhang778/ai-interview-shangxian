"""登录失败守卫：按「账号」与「来源 IP」两个维度限制连续失败次数。

背景：client 与 backoffice 两处登录此前都是「密码错就返回 400」，没有任何次数限制 ——
可以无限次爆破密码。管理端尤其敏感，一旦被猜到就等于交出整个后台。

设计取舍：
- 双维度计数。只看账号挡不住「一个 IP 撞很多账号」，只看 IP 挡不住「分布式撞一个账号」。
- 固定窗口：计数自第一次失败起算，窗口滑过后自动解锁，不需要额外的解锁流程。
- 成功登录只清零账号维度 —— IP 计数器可能同时装着别人的失败尝试，若成功一次就清空，
  攻击者只要用自己的合法账号登录一次，就能顺手把 IP 计数重置掉。
- Redis 不可用时放行（fail-open）：登录是最关键路径，缓存抖动不该让所有人都登不进来；
  短暂失去爆破保护，好过全员锁死。异常会记 warning 以便发现。
"""

import logging
from typing import Optional

from app.core.config import settings
from app.exceptions.http_exceptions import APIException
from app.services.common.redis import redis_client

logger = logging.getLogger(__name__)


class LoginGuard:
    """按 scope 隔离的登录失败计数器（scope 通常为 client / backoffice）。"""

    def __init__(self, scope: str, max_per_account: int, max_per_ip: int, window: int):
        self.scope = scope
        self.max_per_account = max_per_account
        self.max_per_ip = max_per_ip
        self.window = window

    def _account_key(self, account: str) -> str:
        return f"login_fail:{self.scope}:account:{account.strip().lower()}"

    def _ip_key(self, client_ip: str) -> str:
        return f"login_fail:{self.scope}:ip:{client_ip}"

    async def assert_allowed(self, account: str, client_ip: Optional[str]) -> None:
        """登录前置检查：已锁定则直接拒绝，调用方不必再校验密码。"""
        try:
            account_fails = int(await redis_client.get(self._account_key(account)) or 0)
            ip_fails = 0
            if client_ip:
                ip_fails = int(await redis_client.get(self._ip_key(client_ip)) or 0)
        except Exception as exc:
            logger.warning("[%s] 登录失败计数读取异常，本次放行: %s", self.scope, exc)
            return

        if account_fails >= self.max_per_account or ip_fails >= self.max_per_ip:
            logger.warning(
                "[%s] 登录已被锁定: account=%s ip=%s account_fails=%s ip_fails=%s",
                self.scope,
                account,
                client_ip,
                account_fails,
                ip_fails,
            )
            raise APIException(status_code=429, message="登录失败次数过多，请稍后再试")

    async def record_failure(self, account: str, client_ip: Optional[str]) -> None:
        """记录一次登录失败（账号与来源 IP 两个维度各计一次）。"""
        keys = [self._account_key(account)]
        if client_ip:
            keys.append(self._ip_key(client_ip))
        for key in keys:
            try:
                await redis_client.incr_with_ttl(key, self.window)
            except Exception as exc:
                logger.warning("[%s] 登录失败计数写入异常 key=%s: %s", self.scope, key, exc)

    async def clear(self, account: str) -> None:
        """成功登录后清零该账号的失败计数（IP 维度刻意不清，理由见模块 docstring）。"""
        try:
            await redis_client.delete(self._account_key(account))
        except Exception as exc:
            logger.warning("[%s] 登录失败计数清理异常: %s", self.scope, exc)


client_login_guard = LoginGuard(
    "client",
    settings.LOGIN_FAIL_MAX_PER_EMAIL,
    settings.LOGIN_FAIL_MAX_PER_IP,
    settings.LOGIN_FAIL_WINDOW,
)
backoffice_login_guard = LoginGuard(
    "backoffice",
    settings.LOGIN_FAIL_MAX_PER_EMAIL,
    settings.LOGIN_FAIL_MAX_PER_IP,
    settings.LOGIN_FAIL_WINDOW,
)
