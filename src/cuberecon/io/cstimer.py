"""Reader for csTimer session exports (CSV, ``;`` separated)."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from pathlib import Path

_TIME_RE = re.compile(r"(?:(\d+):)?(\d+(?:\.\d+)?)")


@dataclass(frozen=True)
class CsTimerSolve:
    no: int
    time: str
    """Time as exported (``13.52``, ``1:02.31``, ``13.52+``, ``DNF(13.52)``)."""
    time_ms: float | None
    """The number shown in ``time``, in ms (no penalty arithmetic), None if unreadable."""
    penalty: str | None
    """``+2``, ``DNF`` or None."""
    scramble: str
    date: str
    comment: str


def parse_time(text: str) -> tuple[float | None, str | None]:
    text = text.strip()
    penalty = None
    if text.upper().startswith("DNF"):
        penalty = "DNF"
    elif text.endswith("+"):
        penalty = "+2"
    match = _TIME_RE.search(text)
    if not match:
        return None, penalty
    minutes = int(match.group(1) or 0)
    seconds = float(match.group(2))
    return round((minutes * 60 + seconds) * 1000.0, 3), penalty


def is_cstimer_export(text: str) -> bool:
    return text.lstrip("\ufeff").startswith("No.;Time;")


def parse_cstimer_csv(text: str) -> list[CsTimerSolve]:
    """Solves of a csTimer CSV export. Raises ValueError if it is not one."""
    text = text.lstrip("\ufeff")
    if not is_cstimer_export(text):
        raise ValueError("not a csTimer CSV export (expected a 'No.;Time;...' header)")
    out = []
    for row in csv.DictReader(io.StringIO(text), delimiter=";"):
        if not row.get("No.") or not row.get("Scramble"):
            continue
        time_ms, penalty = parse_time(row.get("Time", ""))
        out.append(
            CsTimerSolve(
                no=int(row["No."]),
                time=row.get("Time", "").strip(),
                time_ms=time_ms,
                penalty=penalty,
                scramble=row["Scramble"].strip(),
                date=row.get("Date", "").strip(),
                comment=(row.get("Comment") or "").strip(),
            )
        )
    return out


def load_cstimer_csv(path: str | Path) -> list[CsTimerSolve]:
    return parse_cstimer_csv(Path(path).read_text(encoding="utf-8"))
