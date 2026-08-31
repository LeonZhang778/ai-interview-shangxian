from app.core.config import Settings


def test_grok_env_overrides_legacy_ai_config(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test-xai-key")
    monkeypatch.setenv("GROK_MODELS_BASE_URL", "https://sub.anzhiyu.com/v1")
    monkeypatch.setenv("GROK_MODEL", "grok-4")
    monkeypatch.setenv("AI_API_KEY", "legacy-key")
    monkeypatch.setenv("AI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setenv("AI_MODEL", "qwen-plus")

    settings = Settings()

    assert settings.AI_API_KEY == "test-xai-key"
    assert settings.AI_BASE_URL == "https://sub.anzhiyu.com/v1"
    assert settings.AI_MODEL == "grok-4"
