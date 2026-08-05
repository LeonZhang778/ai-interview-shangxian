from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.api.backoffice.v1.media_tasks import _parse_input_file_ids, _serialize_file_meta, router


def test_parse_input_file_ids_accepts_legacy_json_string():
    assert _parse_input_file_ids("[1, 2, 3]") == [1, 2, 3]
    assert _parse_input_file_ids([4, 5]) == [4, 5]
    assert _parse_input_file_ids("not json") == []


def test_serialize_file_meta_does_not_expose_storage_key():
    now = datetime.now(timezone.utc)
    file_record = SimpleNamespace(
        id=1,
        user_id=2,
        storage_key="uploads/media/2/source/private.mp4",
        original_name="private.mp4",
        media_type="video",
        source_format="mp4",
        size_bytes=1024,
        duration_ms=3000,
        created_at=now,
        expires_at=now,
    )

    data = _serialize_file_meta(file_record)

    assert data["original_name"] == "private.mp4"
    assert "storage_key" not in data


@pytest.mark.parametrize(
    "path,method",
    [
        ("", "GET"),
        ("/{task_id}/retry", "POST"),
        ("/{task_id}/terminate", "POST"),
    ],
)
def test_backoffice_media_task_routes_exist(path, method):
    matches = [
        route for route in router.routes
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set())
    ]
    assert matches
