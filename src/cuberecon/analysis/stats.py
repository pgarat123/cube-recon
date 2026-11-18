"""Timed segments and solve statistics (TPS, pauses, rotations, recognition)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from cuberecon.io import Segment, Solve, TimedMove

from .cfop import CfopResult, segment

DEFAULT_PAUSE_THRESHOLD_MS = 300.0


def _r(x: float) -> float:
    return round(x, 3)


def timed_segments(result: CfopResult, moves: Sequence[TimedMove]) -> list[Segment]:
    """Attach timestamps to the steps. Empty steps get a zero-length interval."""
    segments = []
    for step in result.steps:
        if step.end > step.start:
            t_start = moves[step.start].t_start_ms
            t_end = moves[step.end - 1].t_end_ms
        else:
            t_start = t_end = (
                moves[step.start - 1].t_end_ms
                if step.start > 0
                else (moves[0].t_start_ms if moves else 0.0)
            )
        segments.append(
            Segment(
                step=step.step,
                t_start_ms=t_start,
                t_end_ms=t_end,
                move_range=(step.start, step.end),
                case_id=None if step.case is None else step.case.case_id,
            )
        )
    return segments


def _counts(moves: Sequence[TimedMove]) -> dict[str, int]:
    rotations = sum(m.parsed().is_rotation for m in moves)
    return {"moves_etm": len(moves), "moves_stm": len(moves) - rotations, "rotations": rotations}


def _tps(count: int, duration_ms: float) -> float:
    return _r(count * 1000.0 / duration_ms) if duration_ms > 0 else 0.0


def compute_stats(
    moves: Sequence[TimedMove],
    segments: Sequence[Segment],
    pause_threshold_ms: float = DEFAULT_PAUSE_THRESHOLD_MS,
) -> dict[str, Any]:
    """Global and per-step stats. Inspection moves are excluded from the solve.

    Move counts: ETM counts every token, STM excludes rotations (a slice or a wide
    move counts as one). A step's duration runs from the end of the previous step
    to its last move, so it includes recognition (the gap before its first move).
    """
    inspection = next((s for s in segments if s.step == "inspection"), None)
    first = inspection.move_range[1] if inspection else 0
    timed = list(moves[first:])
    stats: dict[str, Any] = {"pause_threshold_ms": pause_threshold_ms}
    total = timed[-1].t_end_ms - timed[0].t_start_ms if timed else 0.0
    counts = _counts(timed)
    stats.update(total_time_ms=_r(total), **counts)
    stats["tps_etm"] = _tps(counts["moves_etm"], total)
    stats["tps_stm"] = _tps(counts["moves_stm"], total)

    pauses = []
    for i in range(first, len(moves) - 1):
        gap = moves[i + 1].t_start_ms - moves[i].t_end_ms
        if gap >= pause_threshold_ms:
            pauses.append({"after_move": i, "duration_ms": _r(gap)})
    stats["pauses"] = pauses
    stats["total_pause_ms"] = _r(sum(p["duration_ms"] for p in pauses))

    per_step: dict[str, Any] = {}
    prev_end: float | None = None
    for seg in segments:
        if seg.step == "inspection":
            continue
        start, end = seg.move_range
        if prev_end is None:
            prev_end = seg.t_start_ms
        duration = seg.t_end_ms - prev_end
        recognition = seg.t_start_ms - prev_end if end > start else 0.0
        step_counts = _counts(moves[start:end])
        per_step[seg.step] = {
            "duration_ms": _r(duration),
            "recognition_ms": _r(recognition),
            "execution_ms": _r(seg.t_end_ms - seg.t_start_ms),
            **step_counts,
            "tps_etm": _tps(step_counts["moves_etm"], duration),
            "tps_stm": _tps(step_counts["moves_stm"], duration),
        }
        prev_end = seg.t_end_ms
    stats["steps"] = per_step
    return stats


def analyze(solve: Solve, pause_threshold_ms: float = DEFAULT_PAUSE_THRESHOLD_MS) -> Solve:
    """Return a copy of ``solve`` with ``segments`` and ``stats`` computed."""
    result = segment(solve.scramble, solve.parsed_moves())
    segments = timed_segments(result, solve.moves)
    stats = compute_stats(solve.moves, segments, pause_threshold_ms)
    stats["complete"] = result.complete
    stats["cross_color"] = (
        None if result.cross_color is None else solve.color_scheme[result.cross_color]
    )
    return replace(solve, segments=segments, stats=stats)
