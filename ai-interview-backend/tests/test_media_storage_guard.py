"""媒体存储治理纯函数测试（W1：魔数判定 / 文件名截断 / 配额 / 清理筛选）。

全部为纯函数级测试，不依赖 Redis / 数据库 / ffprobe，CI 无 Redis 环境可直接跑。
"""

from datetime import datetime, timedelta, timezone

from app.api.client.v1.media.files import (
    DEFAULT_USER_QUOTA_MB,
    check_quota_overflow,
    classify_media_signature,
    parse_positive_int,
    truncate_filename,
)
from app.schedule.jobs.media_cleanup import (
    should_hard_delete,
    should_purge_expired,
)

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)

MB = 1024 * 1024


# ---------------- 魔数判定 ----------------

def test_signature_rejects_plain_text_masquerading_as_mp4():
    assert classify_media_signature(b"hello world, this is text!!") == "non_media"


def test_signature_accepts_real_mp4_header():
    header = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 4
    assert classify_media_signature(header) == "media"


def test_signature_unknown_is_passed_through():
    header = bytes(range(16))
    assert classify_media_signature(header) == "unknown"


def test_signature_rejects_executables_and_zip():
    assert classify_media_signature(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00") == "non_media"
    assert classify_media_signature(b"\x7fELF\x02\x01\x01\x00\x00\x00") == "non_media"
    assert classify_media_signature(b"PK\x03\x04\x14\x00\x00\x00\x08\x00") == "non_media"


def test_signature_accepts_common_media_containers():
    assert classify_media_signature(b"\x1a\x45\xdf\xa3\x01\x00\x00\x00\x00\x00") == "media"  # mkv
    assert classify_media_signature(b"RIFF\x00\x00\x00\x00AVI LIST") == "media"  # avi
    assert classify_media_signature(b"RIFF\x00\x00\x00\x00WAVEfmt ") == "media"  # wav
    assert classify_media_signature(b"ID3\x04\x00\x00\x00\x00\x00\x00") == "media"  # mp3
    assert classify_media_signature(b"OggS\x00\x02\x00\x00\x00\x00") == "media"  # ogg
    assert classify_media_signature(b"fLaC\x00\x00\x00\x22\x00\x00\x00") == "media"  # flac
    assert classify_media_signature(b"\xff\xd8\xff\xe0\x00\x10JFIF") == "media"  # jpeg
    assert classify_media_signature(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rI") == "media"  # png
    assert classify_media_signature(b"GIF89a\x01\x00\x01\x00\x00\x00") == "media"  # gif
    assert classify_media_signature(b"\xff\xfb\x90\x00\x00\x00\x00\x00\x00\x00") == "media"  # mp3 帧同步


def test_signature_empty_header_is_unknown():
    assert classify_media_signature(b"") == "unknown"


# ---------------- 文件名截断 ----------------

def test_truncate_filename_keeps_extension():
    name = "a" * 296 + ".mp4"  # 300 字符
    out = truncate_filename(name)
    assert len(out) == 200
    assert out.endswith(".mp4")
    assert out == "a" * 196 + ".mp4"


def test_truncate_filename_short_name_untouched():
    name = "video.mp4"
    assert truncate_filename(name) == name


def test_truncate_filename_without_extension():
    out = truncate_filename("x" * 300)
    assert len(out) == 200


def test_truncate_filename_handles_empty_name():
    assert truncate_filename("") == "unknown"
    assert truncate_filename(None) == "unknown"


# ---------------- 配额计算 ----------------

def test_quota_1900mb_plus_200mb_exceeds_2048mb():
    message = check_quota_overflow(1900 * MB, 200 * MB, DEFAULT_USER_QUOTA_MB)
    assert message is not None
    assert "存储空间不足" in message
    assert "2048" in message


def test_quota_100mb_plus_200mb_within_2048mb():
    assert check_quota_overflow(100 * MB, 200 * MB, DEFAULT_USER_QUOTA_MB) is None


def test_quota_exact_boundary_allowed():
    assert check_quota_overflow(1848 * MB, 200 * MB, DEFAULT_USER_QUOTA_MB) is None


def test_parse_positive_int_falls_back_on_invalid():
    assert parse_positive_int(None, 2048) == 2048
    assert parse_positive_int("", 2048) == 2048
    assert parse_positive_int("abc", 2048) == 2048
    assert parse_positive_int("-5", 2048) == 2048
    assert parse_positive_int("0", 2048) == 2048
    assert parse_positive_int("100", 2048) == 100


# ---------------- 清理筛选 ----------------

def test_cleanup_filter_null_expires_at_never_purged():
    assert not should_purge_expired(None, None, NOW)


def test_cleanup_filter_future_expires_at_kept():
    assert not should_purge_expired(NOW + timedelta(hours=1), None, NOW)


def test_cleanup_filter_past_expires_at_purged():
    assert should_purge_expired(NOW - timedelta(hours=1), None, NOW)


def test_cleanup_filter_soft_deleted_left_to_hard_delete_pass():
    assert not should_purge_expired(NOW - timedelta(hours=1), NOW - timedelta(minutes=1), NOW)


def test_hard_delete_filter_requires_soft_deleted_overdue():
    assert not should_hard_delete(None, NOW)
    assert not should_hard_delete(NOW - timedelta(days=1), NOW)
    assert should_hard_delete(NOW - timedelta(days=8), NOW)
