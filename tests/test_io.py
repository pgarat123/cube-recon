import json

import pytest

from cuberecon.analysis import analyze
from cuberecon.io import Solve, SolveFormatError, TimedMove, VideoInfo


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
    )


def test_json_round_trip(tmp_path):
    solve = analyze(sample_solve())
    assert solve.segments and solve.stats
    path = tmp_path / "solve.json"
    solve.save(path)
    data = json.loads(path.read_text())
    assert data["schema_version"] == 1
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
