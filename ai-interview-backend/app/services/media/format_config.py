"""
格式别名、编码器默认值和兼容矩阵配置（T006）

从源项目 distilled 的 FFmpeg 规则，改写为 Python 纯配置。
"""

from typing import Dict, List, Optional


# ============================================================
# 1. 输出格式别名和容器映射
# ============================================================

# 标准格式别名：用户可选的 target_format
FORMAT_ALIASES: Dict[str, str] = {
    "mp4": "mp4",
    "mov": "mov",
    "mkv": "mkv",
    "webm": "webm",
    "avi": "avi",
    "flv": "flv",
    "gif": "gif",
    "mp3": "mp3",
    "wav": "wav",
    "m4a": "m4a",
    "aac": "aac",
    "flac": "flac",
    "ogg": "ogg",
    "wma": "wma",
    "opus": "opus",
}

# 容器 → FFmpeg 格式参数
CONTAINER_ARGS: Dict[str, str] = {
    "mp4": "-f mp4",
    "mov": "-f mov",
    "mkv": "-f matroska",
    "webm": "-f webm",
    "avi": "-f avi",
    "flv": "-f flv",
    "gif": "-f gif",
    "mp3": "-f mp3",
    "wav": "-f wav",
    "m4a": "-f mp4",
    "aac": "-f adts",
    "flac": "-f flac",
    "ogg": "-f ogg",
    "wma": "-f asf",
    "opus": "-f opus",
}

# 格式 → 媒体类型
FORMAT_MEDIA_KIND: Dict[str, str] = {
    "mp4": "video",
    "mov": "video",
    "mkv": "video",
    "webm": "video",
    "avi": "video",
    "flv": "video",
    "gif": "image",
    "png": "image",
    "jpg": "image",
    "jpeg": "image",
    "webp": "image",
    "mp3": "audio",
    "wav": "audio",
    "m4a": "audio",
    "aac": "audio",
    "flac": "audio",
    "ogg": "audio",
    "wma": "audio",
    "opus": "audio",
}


# ============================================================
# 2. 视频/音频编码器别名、默认值和兼容矩阵
# ============================================================

# tool_code 枚举
TOOL_CODES: Dict[str, str] = {
    "convert": "格式转换",
    "compress": "视频压缩",
    "trim": "视频截取",
    "extract_audio": "提取音频",
    "audio_convert": "音频转换",
    "merge": "视频合并",
    "gif": "视频转GIF",
    "watermark": "添加水印",
    "redact": "区域模糊/遮挡",
}

# 当前 Worker 已实现的工具。其余代码保留在能力配置中，待对应故事完成后再开放。
IMPLEMENTED_TOOL_CODES = {
    "convert", "compress", "trim", "extract_audio", "audio_convert",
    "merge", "gif", "watermark", "redact",
}

# 格式 → 默认视频编码器
DEFAULT_VIDEO_CODEC: Dict[str, str] = {
    "mp4": "libx264",
    "mov": "libx264",
    "mkv": "libx265",
    "webm": "libvpx-vp9",
    "avi": "libx264",
    "flv": "libx264",
}

# 格式 → 默认音频编码器
DEFAULT_AUDIO_CODEC: Dict[str, str] = {
    "mp4": "aac",
    "mov": "aac",
    "mkv": "aac",
    "webm": "libopus",
    "avi": "mp3",
    "flv": "mp3",
    "mp3": "libmp3lame",
    "wav": "pcm_s16le",
    "m4a": "aac",
    "aac": "aac",
    "flac": "flac",
    "ogg": "libvorbis",
    "wma": "wmav2",
    "opus": "libopus",
}

# 格式 → 支持的视频编码器白名单
SUPPORTED_VIDEO_CODECS: Dict[str, List[str]] = {
    "mp4": ["libx264", "libx265", "h264_nvenc", "h264_amf", "h264_qsv"],
    "mov": ["libx264", "libx265", "prores", "dnxhd"],
    "mkv": ["libx264", "libx265", "libvpx-vp9", "av1"],
    "webm": ["libvpx-vp9", "libvpx", "av1"],
    "avi": ["libx264", "mpeg4"],
    "flv": ["libx264", "mpeg4"],
}

# 格式 → 支持的音频编码器白名单
SUPPORTED_AUDIO_CODECS: Dict[str, List[str]] = {
    "mp4": ["aac", "mp3", "libmp3lame", "ac3", "eac3"],
    "mov": ["aac", "pcm_s16le", "pcm_s24le"],
    "mkv": ["aac", "flac", "libopus", "libvorbis", "ac3"],
    "webm": ["libopus", "libvorbis"],
    "avi": ["mp3", "libmp3lame", "pcm_s16le"],
    "flv": ["mp3", "aac"],
    "mp3": ["libmp3lame", "mp3"],
    "wav": ["pcm_s16le", "pcm_s24le", "pcm_s32le"],
    "m4a": ["aac", "alac"],
    "aac": ["aac"],
    "flac": ["flac"],
    "ogg": ["libvorbis", "libopus"],
    "wma": ["wmav2", "wmapro"],
    "opus": ["libopus"],
}

# 格式 → 是否支持视频流
FORMAT_HAS_VIDEO: set = {"mp4", "mov", "mkv", "webm", "avi", "flv", "gif"}

# 格式 → 是否支持音频流
FORMAT_HAS_AUDIO: set = {
    "mp4", "mov", "mkv", "webm", "avi", "flv",
    "mp3", "wav", "m4a", "aac", "flac", "ogg", "wma", "opus",
}

# 纯音频格式（不含视频流）
AUDIO_ONLY_FORMATS: set = {"mp3", "wav", "m4a", "aac", "flac", "ogg", "wma", "opus"}

# 视频格式（可含音视频/纯视频）
VIDEO_FORMATS: set = {"mp4", "mov", "mkv", "webm", "avi", "flv"}


# ============================================================
# 3. 质量参数和压缩预设
# ============================================================

# 压缩预设（CRF 值范围 0-51，越小质量越高）
COMPRESSION_QUALITY: Dict[str, Dict] = {
    "high": {"crf": 18, "preset": "slow", "description": "高质量（文件较大）"},
    "medium": {"crf": 23, "preset": "medium", "description": "平衡质量与大小"},
    "low": {"crf": 28, "preset": "fast", "description": "小文件（质量略低）"},
    "custom": {"crf": None, "preset": None, "description": "自定义参数"},
}

# 分辨率预设（宽 x 高，保持比例时只参考宽度）
RESOLUTION_PRESETS: Dict[str, int] = {
    "4320p": 7680,  # 8K
    "2160p": 3840,  # 4K
    "1440p": 2560,  # 2K
    "1080p": 1920,  # Full HD
    "720p": 1280,   # HD
    "480p": 854,    # SD
    "360p": 640,    # 低分辨率
    "240p": 426,    # 极低分辨率
}

# GIF 质量预设
GIF_QUALITY: Dict[str, Dict] = {
    "high": {"fps": 15, "width": 480, "description": "高质量 GIF"},
    "medium": {"fps": 10, "width": 320, "description": "平衡质量与大小"},
    "low": {"fps": 5, "width": 240, "description": "小文件 GIF"},
}


# ============================================================
# 4. 文件扩展名 ↔ MIME 类型映射
# ============================================================

EXTENSION_MIME: Dict[str, str] = {
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "mkv": "video/x-matroska",
    "webm": "video/webm",
    "avi": "video/x-msvideo",
    "flv": "video/x-flv",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "m4a": "audio/mp4",
    "aac": "audio/aac",
    "flac": "audio/flac",
    "ogg": "audio/ogg",
    "wma": "audio/x-ms-wma",
    "opus": "audio/opus",
    "gif": "image/gif",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}

# 媒体工具支持的上传扩展名白名单
ALLOWED_UPLOAD_EXTENSIONS: set = set(EXTENSION_MIME.keys())

# 通过扩展名推断媒体类型
EXTENSION_MEDIA_KIND: Dict[str, str] = {
    "mp4": "video", "mov": "video", "mkv": "video", "webm": "video",
    "avi": "video", "flv": "video",
    "mp3": "audio", "wav": "audio", "m4a": "audio", "aac": "audio",
    "flac": "audio", "ogg": "audio", "wma": "audio", "opus": "audio",
    "gif": "image", "png": "image", "jpg": "image", "jpeg": "image",
    "webp": "image",
}


class FormatConfig:
    """格式配置查询类"""

    # 保持配置常量可通过 format_config 实例访问，兼容 API 和 Celery 任务。
    TOOL_CODES = TOOL_CODES
    RESOLUTION_PRESETS = RESOLUTION_PRESETS
    COMPRESSION_QUALITY = COMPRESSION_QUALITY
    GIF_QUALITY = GIF_QUALITY

    @staticmethod
    def is_valid_tool_code(tool_code: str) -> bool:
        """检查工具代码是否合法且已由当前 Worker 实现"""
        return tool_code in IMPLEMENTED_TOOL_CODES

    @staticmethod
    def get_container_args(format_key: str) -> str:
        return CONTAINER_ARGS.get(format_key, "-f mp4")

    @staticmethod
    def get_default_video_codec(format_key: str) -> Optional[str]:
        return DEFAULT_VIDEO_CODEC.get(format_key)

    @staticmethod
    def get_default_audio_codec(format_key: str) -> Optional[str]:
        return DEFAULT_AUDIO_CODEC.get(format_key)

    @staticmethod
    def is_video_format(format_key: str) -> bool:
        return format_key in FORMAT_HAS_VIDEO

    @staticmethod
    def is_audio_format(format_key: str) -> bool:
        return format_key in FORMAT_HAS_AUDIO

    @staticmethod
    def is_audio_only_format(format_key: str) -> bool:
        return format_key in AUDIO_ONLY_FORMATS

    @staticmethod
    def is_valid_format(format_key: str) -> bool:
        return format_key in FORMAT_ALIASES

    @staticmethod
    def get_media_kind(format_key: str) -> str:
        """按格式返回 video、audio 或 image，未知格式返回 unknown。"""
        return FORMAT_MEDIA_KIND.get(format_key.lower(), "unknown")

    @staticmethod
    def get_mime_type(format_key: str) -> str:
        return EXTENSION_MIME.get(format_key.lower(), "application/octet-stream")

    @staticmethod
    def is_valid_codec(format_key: str, codec: str, codec_type: str = "video") -> bool:
        if codec_type == "video":
            codecs = SUPPORTED_VIDEO_CODECS.get(format_key, [])
        else:
            codecs = SUPPORTED_AUDIO_CODECS.get(format_key, [])
        return codec in codecs

    @staticmethod
    def get_capabilities() -> Dict:
        """返回能力清单（供 capabilities 接口使用）"""
        return {
            "formats": list(FORMAT_ALIASES.keys()),
            "tool_codes": TOOL_CODES,
            "video_codecs": SUPPORTED_VIDEO_CODECS,
            "audio_codecs": SUPPORTED_AUDIO_CODECS,
            "resolution_presets": RESOLUTION_PRESETS,
            "compression_quality": list(COMPRESSION_QUALITY.keys()),
            "gif_quality": list(GIF_QUALITY.keys()),
            "max_file_size_mb": 500,
        }

    @staticmethod
    def get_allowed_extensions() -> list:
        return sorted(ALLOWED_UPLOAD_EXTENSIONS)


format_config = FormatConfig()