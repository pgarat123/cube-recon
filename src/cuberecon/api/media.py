"""Video discovery and metadata (through ffprobe, no decoding)."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
WORK_SUFFIX = ".h264"
"""H.264 working copies are named ``<stem>.h264.mp4`` next to the original."""


class MediaError(RuntimeError):
    """Raised when a video cannot be probed."""


@dataclass(frozen=True)
class VideoMeta:
    name: str
    """File name relative to the videos directory (used as id in the API)."""
    size_bytes: int
    codec: str
    width: int
    height: int
    fps: float
    fps_num: int
    fps_den: int
    frame_count: int
    duration_ms: float
    start_time_ms: float
    work_copy: str | None = None
    """Name of the H.264 working copy, if one exists."""

    def to_dict(self) -> dict:
        return asdict(self)


def list_videos(videos_dir: Path) -> list[Path]:
    """Video files directly in ``videos_dir``, sorted by name."""
    if not videos_dir.is_dir():
        return []
    return sorted(
        p
        for p in videos_dir.iterdir()
        if p.is_file() and p.suffix.lower() in VIDEO_SUFFIXES and not p.name.startswith(".")
    )


def work_copy_name(name: str) -> str:
    return f"{Path(name).stem}{WORK_SUFFIX}.mp4"


def is_work_copy(path: Path) -> bool:
    return path.stem.endswith(WORK_SUFFIX)


def probe(path: Path) -> VideoMeta:
    """Metadata of the first video stream. Cached on (path, size, mtime)."""
    stat = path.stat()
    return _probe_cached(str(path), stat.st_size, stat.st_mtime_ns)


@lru_cache(maxsize=64)
def _probe_cached(path_str: str, size: int, mtime_ns: int) -> VideoMeta:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise MediaError("ffprobe not found (install ffmpeg)")
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name,width,height,r_frame_rate,avg_frame_rate,nb_frames,duration,start_time"
        ":format=duration",
        "-of",
        "json",
        path_str,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise MediaError(f"ffprobe failed on {path_str}: {proc.stderr.strip()}")
    data = json.loads(proc.stdout)
    streams = data.get("streams") or []
    if not streams:
        raise MediaError(f"no video stream in {path_str}")
    s = streams[0]
    rate = Fraction(s.get("avg_frame_rate") or "0/1")
    if rate == 0:
        rate = Fraction(s.get("r_frame_rate") or "0/1")
    if rate == 0:
        raise MediaError(f"unknown frame rate in {path_str}")
    duration = float(s.get("duration") or data.get("format", {}).get("duration") or 0.0)
    frames = int(s.get("nb_frames") or 0) or round(duration * rate)
    return VideoMeta(
        name=Path(path_str).name,
        size_bytes=size,
        codec=s.get("codec_name", "unknown"),
        width=int(s["width"]),
        height=int(s["height"]),
        fps=round(float(rate), 6),
        fps_num=rate.numerator,
        fps_den=rate.denominator,
        frame_count=frames,
        duration_ms=round(duration * 1000.0, 3),
        start_time_ms=round(float(s.get("start_time") or 0.0) * 1000.0, 3),
    )
