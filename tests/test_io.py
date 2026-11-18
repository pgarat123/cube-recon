import json

import pytest

from cuberecon.analysis import analyze
from cuberecon.io import SCHEMA_VERSION, Solve, SolveFormatError, TimedMove, TimeWindow, VideoInfo


def sample_solve() -> Solve:
    return Solve(
        scramble="R U R' U'",
        moves=[
            TimedMove("U", 0.0, 80.0),
            TimedMove("R", 120.0, 200.0, confidence=0.7, source="auto"),
            TimedMove("U'", 230.0, 300.0, source="corrected"),
            TimedMove("R'", 330.0, 400.0),
        ],
        video=VideoInfo(
            path="data/videos/solve_001.mov",
            fps=240.0,
            width=1920,
            height=1080,
            duration_ms=15000.0,
        ),
        calibration={"white": [[95.0, 0.0, 1.0]]},
        solve_window=TimeWindow(0.0, 450.0),
        scramble_source="derived",
        labeling_time_ms=61000.0,
    )


def test_json_round_trip(tmp_path):
    solve = analyze(sample_solve())
    assert solve.segments and solve.stats
    path = tmp_path / "solve.json"
    solve.save(path)
    data = json.loads(path.read_text())
    assert data["schema_version"] == SCHEMA_VERSION == 2
    assert data["solve_window"] == {"t_start_ms": 0.0, "t_end_ms": 450.0}
    assert data["moves"][1] == {
        "move": "R",
        "t_start_ms": 120.0,
        "t_end_ms": 200.0,
        "confidence": 0.7,
        "source": "auto",
    }
    assert data["segments"][0]["move_range"] == [0, 0]
    assert Solve.load(path) == solve


def test_defaults():
    s = Solve(scramble="R")
    assert s.color_scheme["U"] == "white" and s.color_scheme["F"] == "green"
    assert s.id and s.created_at and s.moves == [] and s.video is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"move": "Q", "t_start_ms": 0, "t_end_ms": 1},
        {"move": "R", "t_start_ms": 10, "t_end_ms": 5},
        {"move": "R", "t_start_ms": 0, "t_end_ms": 1, "confidence": 1.5},
        {"move": "R", "t_start_ms": 0, "t_end_ms": 1, "source": "guess"},
    ],
)
def test_invalid_moves_rejected(kwargs):
    with pytest.raises(SolveFormatError):
        TimedMove(**kwargs)


def test_invalid_solves_rejected():
    with pytest.raises(SolveFormatError):
        Solve(scramble="R Q")
    with pytest.raises(SolveFormatError):
        Solve(scramble="R", color_scheme={"U": "white"})
    with pytest.raises(SolveFormatError):
        Solve.from_dict({"scramble": "R"})
    with pytest.raises(SolveFormatError):
        Solve.from_dict({**sample_solve().to_dict(), "schema_version": 99})


def test_v1_files_still_load():
    data = sample_solve().to_dict()
    for key in ("solve_window", "scramble_source", "labeling_time_ms"):
        del data[key]
    data["schema_version"] = 1
    solve = Solve.from_dict(data)
    assert solve.solve_window is None
    assert solve.scramble_source == "manual" and solve.labeling_time_ms == 0.0


def test_invalid_labeling_fields_rejected():
    with pytest.raises(SolveFormatError):
        TimeWindow(10.0, 5.0)
    with pytest.raises(SolveFormatError):
        Solve(scramble="R", scramble_source="guess")
    with pytest.raises(SolveFormatError):
        Solve(scramble="R", labeling_time_ms=-1.0)


CSTIMER = """No.;Time;Comment;Scramble;Date;P.1
6;13.52;;B D' F' U2 D R B' L' D L2 D F2 U' L2 B2 R2 B2 U' R2 L';02/05/2026 17:41;13.52
7;15.47+;oops;B2 U' B2;02/05/2026 17:42;13.47
8;DNF(11.03);;L2 U2 B;02/05/2026 17:43;11.03
9;1:02.50;;R U;02/05/2026 17:45;62.50
"""


def test_parse_cstimer_csv(tmp_path):
    from cuberecon.io import load_cstimer_csv, parse_cstimer_csv

    solves = parse_cstimer_csv("﻿" + CSTIMER)
    assert [s.no for s in solves] == [6, 7, 8, 9]
    assert solves[0].scramble.startswith("B D' F'") and solves[0].time_ms == 13520.0
    assert solves[0].date == "02/05/2026 17:41" and solves[0].penalty is None
    assert (solves[1].penalty, solves[1].time_ms, solves[1].comment) == ("+2", 15470.0, "oops")
    assert (solves[2].penalty, solves[2].time_ms) == ("DNF", 11030.0)
    assert solves[3].time_ms == 62500.0
    path = tmp_path / "export.csv"
    path.write_text(CSTIMER)
    assert load_cstimer_csv(path) == solves
    with pytest.raises(ValueError):
        parse_cstimer_csv("a,b,c\n1,2,3\n")
