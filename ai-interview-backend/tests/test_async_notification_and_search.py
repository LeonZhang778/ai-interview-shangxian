import asyncio

from app.core.config import settings
from app.services.client.notification_service import NotificationService
from app.services.client.search_backend_service import SearchBackendService


class FakeDb:
    def __init__(self):
        self.added = []
        self.committed = False
        self.rolled_back = False

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


def test_enqueue_notification_dispatches_celery_task(monkeypatch):
    calls = []

    from app.schedule.jobs import notification_tasks
    monkeypatch.setattr(notification_tasks.create_notification_task, "delay", lambda **kwargs: calls.append(kwargs))

    db = FakeDb()
    asyncio.run(NotificationService.enqueue_notification(
        db=db,
        user_id=3,
        title="面试已完成",
        content="查看报告",
        notification_type="interview",
        related_id=9,
        related_type="interview",
    ))

    assert calls == [{
        "user_id": 3,
        "title": "面试已完成",
        "content": "查看报告",
        "notification_type": "interview",
        "related_id": 9,
        "related_type": "interview",
    }]
    assert db.added == []


def test_enqueue_notification_falls_back_to_sync_create(monkeypatch):
    from app.schedule.jobs import notification_tasks

    def fail_delay(**kwargs):
        raise RuntimeError("broker down")

    monkeypatch.setattr(notification_tasks.create_notification_task, "delay", fail_delay)

    db = FakeDb()
    asyncio.run(NotificationService.enqueue_notification(db=db, user_id=3, title="通知"))

    assert len(db.added) == 1
    assert db.committed is True


def test_opensearch_result_maps_to_existing_search_response(monkeypatch):
    monkeypatch.setattr(settings, "SEARCH_BACKEND", "opensearch")
    monkeypatch.setattr(settings, "OPENSEARCH_URL", "http://search.local")
    monkeypatch.setattr(settings, "OPENSEARCH_INDEX", "learning_notes")

    def fake_post(path, body):
        assert path == "_search"
        assert body["query"]["bool"]["filter"] == [{"term": {"user_id": 5}}]
        return {
            "hits": {
                "total": {"value": 1},
                "hits": [{
                    "_score": 12.5,
                    "_source": {
                        "id": 11,
                        "title": "Redis",
                        "note_type": "note",
                        "tags": "cache",
                        "view_count": 2,
                        "like_count": 1,
                        "created_at": "2026-08-28T00:00:00",
                    },
                    "highlight": {"content": ["<mark>Redis</mark> 缓存"]},
                }],
            }
        }

    monkeypatch.setattr(SearchBackendService, "_post_json", fake_post)

    result = asyncio.run(SearchBackendService.search_learning_notes(
        keyword="redis",
        user_id=5,
        note_type=None,
        page=1,
        size=20,
        scope="my",
    ))

    assert result["total"] == 1
    assert result["items"][0]["id"] == 11
    assert result["items"][0]["headline"] == "<mark>Redis</mark> 缓存"


def test_reranker_reorders_search_items(monkeypatch):
    monkeypatch.setattr(settings, "RERANKER_URL", "http://reranker.local")
    monkeypatch.setattr(SearchBackendService, "_post_reranker", lambda body: {"scores": [0.1, 0.9]})

    items = [{"id": 1, "title": "A"}, {"id": 2, "title": "B"}]
    result = asyncio.run(SearchBackendService.rerank_notes("redis", items))

    assert [item["id"] for item in result] == [2, 1]
    assert result[0]["rerank_score"] == 0.9
