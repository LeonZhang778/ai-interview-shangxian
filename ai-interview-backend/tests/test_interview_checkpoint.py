import asyncio

from langgraph.checkpoint.memory import InMemorySaver

from app.core.config import settings
from app.graphs.interview_graph import InterviewState, build_interview_graph


def test_interview_state_excludes_runtime_only_dependencies():
    annotations = InterviewState.__annotations__

    assert "db" not in annotations
    assert "chunk_queue" not in annotations


def test_build_interview_graph_accepts_external_checkpointer():
    checkpointer = InMemorySaver()

    graph = build_interview_graph(checkpointer=checkpointer)

    assert graph.checkpointer is checkpointer


def test_checkpoint_settings_use_dedicated_redis_database_and_ttl(monkeypatch):
    monkeypatch.setattr(settings, "REDIS_HOST", "redis.example")
    monkeypatch.setattr(settings, "REDIS_PORT", 6379)
    monkeypatch.setattr(settings, "REDIS_PASSWORD", "s:ecret@value")
    monkeypatch.setattr(settings, "REDIS_CHECKPOINT_DB", 0)
    monkeypatch.setattr(settings, "LANGGRAPH_CHECKPOINT_TTL_MINUTES", 180)

    from app.graphs.checkpoint import RedisCheckpointManager

    manager = RedisCheckpointManager()

    assert manager.redis_url == "redis://:s%3Aecret%40value@redis.example:6379/0"
    assert manager.ttl == {"default_ttl": 180, "refresh_on_read": True}


def test_checkpoint_manager_start_is_idempotent(monkeypatch):
    from app.graphs.checkpoint import RedisCheckpointManager

    class FakeSaver:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

    fake_saver = FakeSaver()
    monkeypatch.setattr("app.graphs.checkpoint.AsyncRedisSaver", lambda **_kwargs: fake_saver)

    async def run():
        manager = RedisCheckpointManager()
        await manager.start()
        await manager.start()
        assert manager.saver is fake_saver
        assert manager._started is True

    asyncio.run(run())
