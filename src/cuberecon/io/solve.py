"""The ``Solve`` object and its JSON format (see PLAN.md, section 3)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from cuberecon.cube import FACES, Move, parse_move, parse_moves

SCHEMA_VERSION = 1
SOURCES = ("manual", "auto", "corrected")
DEFAULT_COLOR_SCHEME: dict[str, str] = {
    "U": "white",
    "F": "green",
    "R": "red",
    "D": "yellow",
    "L": "orange",
    "B": "blue",
}


class SolveFormatError(ValueError):
    """Raised when a Solve or one of its parts is invalid."""


@dataclass
class VideoInfo:
    path: str
    fps: float
    width: int
    height: int
    duration_ms: float


@dataclass
class TimedMove:
    move: str
    t_start_ms: float
    t_end_ms: float
    confidence: float = 1.0
    source: str = "manual"

    def __post_init__(self) -> None:
        try:
            parse_move(self.move)
        except ValueError as exc:
            raise SolveFormatError(str(exc)) from exc
        if self.t_end_ms < self.t_start_ms:
            raise SolveFormatError(f"move {self.move!r} ends before it starts")
        if not 0.0 <= self.confidence <= 1.0:
            raise SolveFormatError(f"confidence out of [0, 1]: {self.confidence}")
        if self.source not in SOURCES:
            raise SolveFormatError(f"unknown source {self.source!r}")

    def parsed(self) -> Move:
        return parse_move(self.move)


@dataclass
class Segment:
    step: str
    t_start_ms: float
    t_end_ms: float
    move_range: tuple[int, int]
    """Half-open range ``[start, end)`` of move indices."""
    case_id: str | None = None


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class Solve:
    scramble: str
    moves: list[TimedMove] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid4().hex)
    created_at: str = field(default_factory=_now)
    video: VideoInfo | None = None
    color_scheme: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_COLOR_SCHEME))
    calibration: dict[str, list[list[float]]] | None = None
    """Optional color -> list of Lab samples."""
    segments: list[Segment] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        try:
            parse_moves(self.scramble)
        except ValueError as exc:
            raise SolveFormatError(f"invalid scramble: {exc}") from exc
        if set(self.color_scheme) != set(FACES):
            raise SolveFormatError("color_scheme must map exactly the faces U R F D L B")

    def parsed_moves(self) -> list[Move]:
        return [m.parsed() for m in self.moves]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "id": self.id,
            "created_at": self.created_at,
            "video": None if self.video is None else vars(self.video).copy(),
            "scramble": self.scramble,
            "color_scheme": dict(self.color_scheme),
            "calibration": self.calibration,
            "moves": [vars(m).copy() for m in self.moves],
            "segments": [{**vars(s), "move_range": list(s.move_range)} for s in self.segments],
            "stats": self.stats,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Solve:
        version = data.get("schema_version", SCHEMA_VERSION)
        if version > SCHEMA_VERSION:
            raise SolveFormatError(f"unsupported schema_version {version}")
        try:
            video = data.get("video")
            return cls(
                id=data["id"],
                created_at=data["created_at"],
                video=None if video is None else VideoInfo(**video),
                scramble=data["scramble"],
                color_scheme=data.get("color_scheme") or dict(DEFAULT_COLOR_SCHEME),
                calibration=data.get("calibration"),
                moves=[TimedMove(**m) for m in data.get("moves", [])],
                segments=[
                    Segment(**{**s, "move_range": tuple(s["move_range"])})
                    for s in data.get("segments", [])
                ],
                stats=data.get("stats") or {},
            )
        except (KeyError, TypeError) as exc:
            raise SolveFormatError(f"malformed solve: {exc}") from exc

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> Solve:
        return cls.from_dict(json.loads(text))

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json() + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> Solve:
        return cls.from_json(Path(path).read_text(encoding="utf-8"))
