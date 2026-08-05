import asyncio
from types import SimpleNamespace

import pytest

from app.exceptions.http_exceptions import APIException
from app.services.media.repository import MediaTaskRepository


class _FakeDb:
    def __init__(self):
        self.commits = 0
        self.refreshed = []

    async def commit(self):
        self.commits += 1

    async def refresh(self, item):
        self.refreshed.append(item)


def _task(status, retry_count=0):
    return SimpleNamespace(
        id=1,
        user_id=2,
        status=status,
        progress=55,
        error_code="FFMPEG_ERROR",
        error_message="failed",
        retry_count=retry_count,
        started_at="started",
        finished_at="finished",
        celery_task_id="celery-1",
    )


def test_admin_retry_resets_failed_task(monkeypatch):
    db = _FakeDb()
    task = _task("failed", retry_count=1)

    async def fake_get_by_id_admin(_db, task_id):
        assert task_id == task.id
        return task

    monkeypatch.setattr(MediaTaskRepository, "get_by_id_admin", fake_get_by_id_admin)

    result = asyncio.run(MediaTaskRepository.retry_task_admin(db, task.id))

    assert result.status == "pending"
    assert result.progress == 0
    assert result.error_code is None
    assert result.error_message is None
    assert result.started_at is None
    assert result.finished_at is None
    assert result.celery_task_id is None
    assert result.retry_count == 2
    assert db.commits == 1
    assert db.refreshed == [task]


def test_admin_retry_rejects_non_failed_task(monkeypatch):
    db = _FakeDb()
    task = _task("processing")

    async def fake_get_by_id_admin(_db, task_id):
        return task

    monkeypatch.setattr(MediaTaskRepository, "get_by_id_admin", fake_get_by_id_admin)

    with pytest.raises(APIException):
        asyncio.run(MediaTaskRepository.retry_task_admin(db, task.id))


def test_admin_terminate_rejects_completed_task(monkeypatch):
    db = _FakeDb()
    task = _task("completed")

    async def fake_get_by_id_admin(_db, task_id):
        return task

    monkeypatch.setattr(MediaTaskRepository, "get_by_id_admin", fake_get_by_id_admin)

    with pytest.raises(APIException):
        asyncio.run(MediaTaskRepository.terminate_task_admin(db, task.id))
