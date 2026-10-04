"""SECRET_KEY 生产环境校验的回归测试。

背景：config.py 曾长期以 "your-secret-key-change-in-production" 作为默认值，
而 CI 写入 .env 时不包含也不校验 SECRET_KEY。一旦部署机的 .env 缺这一行，
全站 JWT 就可用这个公开常量伪造。以下用例锁定「生产环境必须持有强随机密钥」
这一行为，防止回退。
"""

import pytest
from pydantic import ValidationError

from app.core.config import MIN_SECRET_KEY_LENGTH, Settings

WEAK = "your-secret-key-change-in-production"


@pytest.mark.parametrize(
    "secret_key",
    ["", WEAK, "change-me", "changeme", "secret", "dev", "short-key"],
)
def test_production_rejects_weak_or_missing_secret_key(secret_key):
    """生产环境：空值、占位值、长度不足都必须拒绝启动。"""
    with pytest.raises(ValidationError):
        Settings(ENV="production", SECRET_KEY=secret_key)


@pytest.mark.parametrize("env", ["production", "prod", "PRODUCTION", " Production "])
def test_production_env_variants_are_enforced(env):
    with pytest.raises(ValidationError):
        Settings(ENV=env, SECRET_KEY=WEAK)


def test_production_accepts_strong_secret_key():
    key = "a" * MIN_SECRET_KEY_LENGTH
    settings = Settings(ENV="production", SECRET_KEY=key)
    assert settings.SECRET_KEY == key


def test_development_keeps_default_for_local_convenience():
    """非生产环境不应因弱密钥而无法启动，避免影响本地开发与测试。"""
    settings = Settings(ENV="development")
    assert settings.SECRET_KEY == WEAK
