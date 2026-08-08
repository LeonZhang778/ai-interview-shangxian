import pytest

from app.api.client.v1.media.tasks import _validate_options, _validate_special_options
from app.exceptions.http_exceptions import APIException


def assert_bad(call, message):
    with pytest.raises(APIException) as exc_info:
        call()
    assert exc_info.value.status_code == 400
    assert message in str(exc_info.value.detail)


def test_gif_duration_must_be_positive_and_finite():
    assert_bad(lambda: _validate_special_options({"duration": 0}, "gif"), "GIF 时长")
    assert_bad(lambda: _validate_special_options({"duration": "nan"}, "gif"), "GIF 时间参数")


def test_gif_width_and_fps_are_bounded():
    assert_bad(lambda: _validate_special_options({"duration": 1, "width": 15}, "gif"), "GIF 宽度")
    assert_bad(lambda: _validate_special_options({"duration": 1, "frame_rate": 61}, "gif"), "GIF 帧率")


def test_merge_requires_two_to_ten_files():
    assert_bad(lambda: _validate_special_options({"file_ids": [1]}, "merge"), "至少需要 2 个")
    assert_bad(lambda: _validate_special_options({"file_ids": list(range(11))}, "merge"), "最多 10 个")


def test_watermark_options_are_validated():
    assert_bad(lambda: _validate_special_options({}, "watermark"), "watermark_file_id")
    assert_bad(lambda: _validate_special_options({"watermark_file_id": 2, "opacity": 0}, "watermark"), "透明度")
    assert_bad(lambda: _validate_special_options({"watermark_file_id": 2, "watermark_width": 15}, "watermark"), "宽度")
    assert_bad(
        lambda: _validate_special_options(
            {"watermark_type": "text", "watermark_text": "demo", "watermark_font_color": "red:enable=1"},
            "watermark",
        ),
        "颜色",
    )


def test_conversion_numbers_must_be_finite_and_non_negative():
    assert_bad(lambda: _validate_options({"duration": "inf"}, "mp4"), "非负有限数字")
    assert_bad(lambda: _validate_options({"start_time": -1}, "mp4"), "非负有限数字")
