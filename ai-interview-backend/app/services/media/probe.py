"""
FFprobe 媒体探测服务（T005）

使用 ffprobe 探测媒体文件的流信息、时长、分辨率等元数据。
"""

import json
import logging
import asyncio
from typing import Dict, Optional, List
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class MediaStreamInfo:
    """单个媒体流信息"""
    index: int = 0
    codec_type: str = ""        # video / audio / subtitle
    codec_name: str = ""        # h264, aac, vp9, etc.
    codec_long_name: str = ""
    profile: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    coded_width: Optional[int] = None
    coded_height: Optional[int] = None
    pix_fmt: Optional[str] = None        # yuv420p, etc.
    color_space: Optional[str] = None
    color_transfer: Optional[str] = None
    color_primaries: Optional[str] = None
    field_order: Optional[str] = None
    r_frame_rate: str = ""               # "30/1"
    avg_frame_rate: str = ""             # "30000/1001"
    sample_rate: Optional[int] = None    # 音频采样率
    channels: Optional[int] = None       # 音频声道数
    channel_layout: Optional[str] = None
    bits_per_sample: Optional[int] = None
    duration: Optional[float] = None
    bit_rate: Optional[int] = None
    tags: Dict[str, str] = field(default_factory=dict)
    disposition: Dict[str, int] = field(default_factory=dict)
    is_attachment: bool = False


@dataclass
class MediaProbeInfo:
    """完整的媒体探测信息"""
    file_path: str = ""
    format_name: str = ""                # mov,mp4,m4a,3gp,3g2,mj2
    format_long_name: str = ""
    size_bytes: int = 0
    duration_seconds: Optional[float] = None
    bit_rate: Optional[int] = None
    start_time: Optional[float] = None
    streams: List[MediaStreamInfo] = field(default_factory=list)
    has_video: bool = False
    has_audio: bool = False
    width: Optional[int] = None
    height: Optional[int] = None
    tags: Dict[str, str] = field(default_factory=dict)
    probe_json: Dict = field(default_factory=dict)  # 原始 JSON 快照

    @property
    def probe_summary(self) -> Dict:
        """返回受控的元数据摘要（不含原始 JSON 中的敏感路径）"""
        return {
            "format_name": self.format_name,
            "size_bytes": self.size_bytes,
            "duration_seconds": self.duration_seconds,
            "bit_rate": self.bit_rate,
            "has_video": self.has_video,
            "has_audio": self.has_audio,
            "width": self.width,
            "height": self.height,
            "stream_count": len(self.streams),
        }


class FFprobeService:
    """FFprobe 媒体探测服务"""

    def __init__(self, ffprobe_path: str = "ffprobe"):
        self.ffprobe_path = ffprobe_path

    async def probe(self, file_path: str) -> MediaProbeInfo:
        """
        执行 ffprobe 探测，返回结构化的媒体信息。

        Args:
            file_path: 媒体文件绝对路径

        Returns:
            MediaProbeInfo 对象

        Raises:
            RuntimeError: ffprobe 执行失败或输出解析失败
        """
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

            if proc.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace").strip()
                raise RuntimeError(
                    f"ffprobe 执行失败 (code={proc.returncode}): {error_msg}"
                )

            raw = json.loads(stdout.decode("utf-8", errors="replace"))
            return self._parse_probe_output(raw, file_path)

        except asyncio.TimeoutError:
            raise RuntimeError("ffprobe 探测超时（30秒）")
        except FileNotFoundError:
            raise RuntimeError(f"找不到 ffprobe 可执行文件: {self.ffprobe_path}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"ffprobe 输出 JSON 解析失败: {e}")

    def _parse_probe_output(self, raw: Dict, file_path: str) -> MediaProbeInfo:
        """解析 ffprobe JSON 输出"""
        info = MediaProbeInfo(file_path=file_path)
        info.probe_json = raw  # 存原始快照

        # 解析 format 信息
        fmt = raw.get("format", {})
        info.format_name = fmt.get("format_name", "")
        info.format_long_name = fmt.get("format_long_name", "")
        info.size_bytes = int(fmt.get("size", 0))
        info.bit_rate = int(fmt.get("bit_rate", 0)) if fmt.get("bit_rate") else None
        info.tags = fmt.get("tags", {})

        # 解析 duration
        dur_str = fmt.get("duration")
        if dur_str:
            try:
                info.duration_seconds = round(float(dur_str), 3)
            except (ValueError, TypeError):
                pass

        # 解析 start_time
        start_str = fmt.get("start_time")
        if start_str:
            try:
                info.start_time = float(start_str)
            except (ValueError, TypeError):
                pass

        # 解析 streams
        streams_raw = raw.get("streams", [])
        for s in streams_raw:
            stream = MediaStreamInfo(
                index=s.get("index", 0),
                codec_type=s.get("codec_type", ""),
                codec_name=s.get("codec_name", ""),
                codec_long_name=s.get("codec_long_name", ""),
                profile=s.get("profile"),
                pix_fmt=s.get("pix_fmt"),
                color_space=s.get("color_space"),
                color_transfer=s.get("color_transfer"),
                color_primaries=s.get("color_primaries"),
                field_order=s.get("field_order"),
                r_frame_rate=s.get("r_frame_rate", ""),
                avg_frame_rate=s.get("avg_frame_rate", ""),
                sample_rate=int(s["sample_rate"]) if s.get("sample_rate") else None,
                channels=s.get("channels"),
                channel_layout=s.get("channel_layout"),
                bits_per_sample=s.get("bits_per_sample"),
                bit_rate=int(s["bit_rate"]) if s.get("bit_rate") else None,
                tags=s.get("tags", {}),
                disposition=s.get("disposition", {}),
                is_attachment=s.get("disposition", {}).get("attached_pic", 0) == 1,
            )

            # 视频特有字段
            if s.get("width"):
                stream.width = s["width"]
                stream.coded_width = s.get("coded_width")
            if s.get("height"):
                stream.height = s["height"]
                stream.coded_height = s.get("coded_height")

            # 音频 duration（来自 stream 级别）
            if s.get("duration"):
                try:
                    stream.duration = float(s["duration"])
                except (ValueError, TypeError):
                    pass

            info.streams.append(stream)

            # 汇总信息
            if stream.codec_type == "video" and not stream.is_attachment:
                info.has_video = True
                if info.width is None:
                    info.width = stream.width
                    info.height = stream.height
            elif stream.codec_type == "audio":
                info.has_audio = True

        return info

    async def check_ffprobe_available(self) -> bool:
        """检查 ffprobe 是否可用"""
        try:
            proc = await asyncio.create_subprocess_exec(
                self.ffprobe_path, "-version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            return proc.returncode == 0
        except FileNotFoundError:
            return False


ffprobe_service = FFprobeService()