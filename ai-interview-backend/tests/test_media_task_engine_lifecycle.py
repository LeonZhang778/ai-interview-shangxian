import asyncio

from app.schedule.jobs import media_tasks


class _FakeEngine:
    def __init__(self):
        self.disposed = False

    async def dispose(self):
        assert media_tasks._engine is None
        assert media_tasks._session_factory is None
        assert media_tasks._engine_loop_id is None
        self.disposed = True


def test_session_factory_is_recreated_for_new_event_loop(monkeypatch):
    engines = []

    def fake_create_async_engine(*args, **kwargs):
        engine = _FakeEngine()
        engines.append(engine)
        return engine

    def fake_async_sessionmaker(engine, **kwargs):
        return {"engine": engine}

    async def get_factory():
        return media_tasks._get_session_factory()

    monkeypatch.setattr(media_tasks, "_engine", None)
    monkeypatch.setattr(media_tasks, "_session_factory", None)
    monkeypatch.setattr(media_tasks, "_engine_loop_id", None)
    monkeypatch.setattr(media_tasks, "create_async_engine", fake_create_async_engine)
    monkeypatch.setattr(media_tasks, "async_sessionmaker", fake_async_sessionmaker)

    first_loop = asyncio.new_event_loop()
    second_loop = asyncio.new_event_loop()
    try:
        first_factory = first_loop.run_until_complete(get_factory())
        second_factory = second_loop.run_until_complete(get_factory())
    finally:
        first_loop.close()
        second_loop.close()

    assert len(engines) == 2
    assert first_factory is not second_factory
    assert first_factory["engine"] is engines[0]
    assert second_factory["engine"] is engines[1]


def test_dispose_engine_clears_cached_state_before_dispose(monkeypatch):
    engine = _FakeEngine()

    monkeypatch.setattr(media_tasks, "_engine", engine)
    monkeypatch.setattr(media_tasks, "_session_factory", object())
    monkeypatch.setattr(media_tasks, "_engine_loop_id", 123)

    asyncio.run(media_tasks._dispose_engine())

    assert engine.disposed is True
    assert media_tasks._engine is None
    assert media_tasks._session_factory is None
    assert media_tasks._engine_loop_id is None
