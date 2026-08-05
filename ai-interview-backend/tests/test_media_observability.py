from app.schedule.jobs.media_tasks import _status_event_name
from app.services.media.observability import build_media_event_payload, hash_user_id


def test_media_event_payload_hashes_user_id_and_keeps_safe_fields():
    payload = build_media_event_payload(
        event="media.task.completed",
        task_id=12,
        file_id=34,
        user_id=56,
        trace_id="trace-1",
        tool_name="convert",
        duration_ms=1234,
        extra={"output_size": 4096},
    )

    assert payload["user_id_hash"] == hash_user_id(56)
    assert "user_id" not in payload
    assert "storage_key" not in payload
    assert payload["event"] == "media.task.completed"
    assert payload["duration_ms"] == 1234


def test_worker_status_maps_to_observability_event_names():
    assert _status_event_name("processing", 5) == "media.task.started"
    assert _status_event_name("processing", 10) == "media.task.progress"
    assert _status_event_name("completed", 100) == "media.task.completed"
    assert _status_event_name("failed", None) == "media.task.failed"
    assert _status_event_name("cancelled", None) == "media.task.cancelled"
