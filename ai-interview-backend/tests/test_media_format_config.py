from app.services.media.format_config import format_config


def test_audio_formats_have_expected_default_codecs_and_media_kind():
    expected = {
        "aac": "aac",
        "mp3": "libmp3lame",
        "wav": "pcm_s16le",
        "flac": "flac",
        "ogg": "libvorbis",
        "wma": "wmav2",
    }

    for format_key, codec in expected.items():
        assert format_config.is_valid_format(format_key)
        assert format_config.is_audio_only_format(format_key)
        assert format_config.get_media_kind(format_key) == "audio"
        assert format_config.get_default_audio_codec(format_key) == codec
        assert format_config.is_valid_codec(format_key, codec, "audio")


def test_tool_code_mapping_only_allows_implemented_tools():
    assert format_config.is_valid_tool_code("convert")
    assert format_config.is_valid_tool_code("compress")
    assert format_config.is_valid_tool_code("extract_audio")
    assert format_config.is_valid_tool_code("audio_convert")
    assert format_config.is_valid_tool_code("merge")
    assert format_config.is_valid_tool_code("gif")
    assert format_config.is_valid_tool_code("watermark")
    assert not format_config.is_valid_tool_code("redact")
    assert not format_config.is_valid_tool_code("remove_watermark")
