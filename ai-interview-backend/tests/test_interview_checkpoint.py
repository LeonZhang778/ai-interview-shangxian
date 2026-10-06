import asyncio
import os
import uuid

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.base import empty_checkpoint

from app.core.config import Settings, settings
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


def test_settings_reject_nonzero_checkpoint_database():
    with pytest.raises(ValueError, match="REDIS_CHECKPOINT_DB.*0"):
        Settings(REDIS_CHECKPOINT_DB=1)


def test_settings_reject_nonpositive_checkpoint_ttl():
    with pytest.raises(ValueError, match="LANGGRAPH_CHECKPOINT_TTL_MINUTES"):
        Settings(LANGGRAPH_CHECKPOINT_TTL_MINUTES=0)


def test_redis_checkpoint_round_trip_ttl_and_thread_isolation():
    redis_url = os.getenv("REDIS_CHECKPOINT_TEST_URL")
    if not redis_url:
        pytest.skip("REDIS_CHECKPOINT_TEST_URL is not configured")

    async def run():
        prefix = f"test_ai_interview_checkpoint_{uuid.uuid4().hex}"
        saver = __import__(
            "langgraph.checkpoint.redis.aio",
            fromlist=["AsyncRedisSaver"],
        ).AsyncRedisSaver(
            redis_url=redis_url,
            ttl={"default_ttl": 1, "refresh_on_read": True},
            checkpoint_prefix=prefix,
            checkpoint_write_prefix=f"{prefix}_write",
        )
        thread_a = f"integration-a-{uuid.uuid4().hex}"
        thread_b = f"integration-b-{uuid.uuid4().hex}"

        async with saver:
            await saver._redis.ft(saver.checkpoints_index.name).info()

            def checkpoint(label: str) -> dict:
                value = empty_checkpoint()
                value["channel_values"] = {"label": label}
                value["channel_versions"] = {"label": 1}
                return value

            async def put(thread_id: str, label: str):
                config = {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": "",
                    }
                }
                metadata = {
                    "source": "input",
                    "step": 0,
                    "parents": {},
                    "run_id": f"run-{thread_id}",
                    "counters_since_delta_snapshot": {},
                }
                await saver.aput(config, checkpoint(label), metadata, {"label": 1})

            await put(thread_a, "a")
            await put(thread_b, "b")

            loaded_a = await saver.aget(
                {"configurable": {"thread_id": thread_a, "checkpoint_ns": ""}}
            )
            loaded_b = await saver.aget(
                {"configurable": {"thread_id": thread_b, "checkpoint_ns": ""}}
            )

            assert loaded_a["channel_values"]["label"] == "a"
            assert loaded_b["channel_values"]["label"] == "b"

            checkpoint_id = loaded_a["id"]
            checkpoint_key = saver._make_redis_checkpoint_key_cached(
                thread_a, "", checkpoint_id
            )
            pointer_key = saver._make_redis_checkpoint_latest_key(thread_a, "")
            assert await saver._redis.ttl(checkpoint_key) > 0
            assert await saver._redis.ttl(pointer_key) > 0

            await saver.adelete_thread(thread_a)
            await saver.adelete_thread(thread_b)

    asyncio.run(run())
