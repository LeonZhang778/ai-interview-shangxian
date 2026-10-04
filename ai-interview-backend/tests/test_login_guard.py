"""登录失败守卫与真实 IP 提取的行为锁定。

背景：client 与 backoffice 两处登录此前都只要密码错就返回 400，没有任何次数限制 ——
可以无限次爆破密码；管理端被猜到就等于交出整个后台。
另：原先提取客户端 IP 时取 X-Forwarded-For 的第一段，而该段完全由请求方控制（见
app/utils/request.py 的说明），拿它做限流等于没做。
"""

import asyncio
from typing import Optional

import pytest
from starlette.requests import Request

from app.exceptions.http_exceptions import APIException
from app.services.common import login_guard as login_guard_module
from app.services.common.login_guard import LoginGuard
from app.utils.request import get_client_ip


class _FakeRedis:
    def __init__(self):
        self.store: dict = {}

    async def get(self, key: str) -> Optional[str]:
        return self.store.get(key)

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def incr_with_ttl(self, key: str, ttl_seconds: int) -> int:
        value = int(self.store.get(key, 0)) + 1
        self.store[key] = str(value)
        return value


class _BrokenRedis:
    """所有操作都抛异常，用于验证 fail-open。"""

    async def get(self, key):
        raise ConnectionError("redis down")

    async def delete(self, key):
        raise ConnectionError("redis down")

    async def incr_with_ttl(self, key, ttl):
        raise ConnectionError("redis down")


@pytest.fixture
def env(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(login_guard_module, "redis_client", fake)
    guard = LoginGuard("test", max_per_account=3, max_per_ip=5, window=600)
    return guard, fake


# ---------------------------------------------------------------------------
# 登录失败计数
# ---------------------------------------------------------------------------

def test_allows_below_threshold(env):
    guard, _ = env
    for _ in range(2):
        asyncio.run(guard.record_failure("a@example.com", "1.1.1.1"))
    # 未达阈值，不抛异常即为通过
    asyncio.run(guard.assert_allowed("a@example.com", "1.1.1.1"))


def test_blocks_when_account_threshold_reached(env):
    guard, _ = env
    for _ in range(3):
        asyncio.run(guard.record_failure("a@example.com", None))
    with pytest.raises(APIException):
        asyncio.run(guard.assert_allowed("a@example.com", None))


def test_blocks_by_ip_across_different_accounts(env):
    """不同账号、同一 IP：账号维度不达标，但 IP 维度达标（防跨账号撞库）。"""
    guard, _ = env
    for i in range(5):
        asyncio.run(guard.record_failure(f"u{i}@example.com", "9.9.9.9"))
    with pytest.raises(APIException):
        asyncio.run(guard.assert_allowed("brand-new@example.com", "9.9.9.9"))


def test_account_and_ip_counters_are_separate(env):
    guard, fake = env
    asyncio.run(guard.record_failure("a@example.com", "1.1.1.1"))
    keys = sorted(fake.store)
    assert len(keys) == 2
    assert any("account" in k for k in keys)
    assert any("ip" in k for k in keys)


def test_clear_resets_account_but_leaves_ip_counter(env):
    """成功登录只清账号维度：否则攻击者用自己账号登录一次就能重置 IP 计数。"""
    guard, fake = env
    for i in range(5):
        asyncio.run(guard.record_failure(f"u{i}@example.com", "9.9.9.9"))
    asyncio.run(guard.clear("u0@example.com"))
    # 账号维度已清零，但 IP 维度仍是 5，依然应当被拒
    assert fake.store.get(guard._account_key("u0@example.com")) is None
    with pytest.raises(APIException):
        asyncio.run(guard.assert_allowed("u0@example.com", "9.9.9.9"))


def test_account_key_is_case_insensitive(env):
    """邮箱大小写不应被用来绕过计数。"""
    guard, fake = env
    for _ in range(3):
        asyncio.run(guard.record_failure("A@Example.com", None))
    with pytest.raises(APIException):
        asyncio.run(guard.assert_allowed("a@example.com", None))


# ---------------------------------------------------------------------------
# 降级行为：Redis 不可用
# ---------------------------------------------------------------------------

def test_fail_open_when_redis_unavailable(monkeypatch):
    """Redis 抖动时放行 —— 登录是最关键路径，不该让所有人登不进来。"""
    monkeypatch.setattr(login_guard_module, "redis_client", _BrokenRedis())
    guard = LoginGuard("test", 3, 5, 600)
    asyncio.run(guard.assert_allowed("a@example.com", "1.1.1.1"))


def test_record_failure_swallows_redis_error(monkeypatch):
    """计数写入失败不能让登录本身报 500。"""
    monkeypatch.setattr(login_guard_module, "redis_client", _BrokenRedis())
    guard = LoginGuard("test", 3, 5, 600)
    asyncio.run(guard.record_failure("a@example.com", "1.1.1.1"))


# ---------------------------------------------------------------------------
# 真实 IP 提取
# ---------------------------------------------------------------------------

def _make_request(headers=None, client=("10.0.0.1", 1234)):
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "headers": raw, "client": client})


def test_prefers_x_real_ip():
    """X-Real-IP 由 nginx 覆盖式写入，客户端无法伪造，必须优先采用。"""
    request = _make_request({
        "x-real-ip": "203.0.113.7",
        "x-forwarded-for": "1.2.3.4, 203.0.113.7",
    })
    assert get_client_ip(request) == "203.0.113.7"


def test_takes_last_hop_of_xff_not_first():
    """伪造的 XFF 会被 nginx 追加在末尾，取第一段等于取攻击者可控的值。"""
    request = _make_request({"x-forwarded-for": "6.6.6.6, 198.51.100.9"})
    assert get_client_ip(request) == "198.51.100.9"


def test_falls_back_to_socket_peer():
    request = _make_request({}, client=("192.0.2.10", 5555))
    assert get_client_ip(request) == "192.0.2.10"


def test_returns_none_without_any_source():
    request = _make_request({}, client=None)
    assert get_client_ip(request) is None


def test_ignores_blank_forwarded_entries():
    """空段不能把结果带偏。"""
    request = _make_request({"x-forwarded-for": "  , 203.0.113.7 , "})
    assert get_client_ip(request) == "203.0.113.7"
