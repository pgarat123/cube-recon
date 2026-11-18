"""CFOP segmentation, OLL/PLL recognition and stats.

The full solves below are CFOP solves written step by step (inspection rotation,
cross, four pair inserts, OLL with pre-AUF, PLL with pre-AUF, AUF). Their scramble
is derived as the inverse of the solution with rotations stripped, so the expected
step boundaries are known exactly.
"""

import pytest

from cuberecon.analysis import (
    OLL_ALGS,
    PLL_ALGS,
    analyze,
    recognize_oll,
    recognize_pll,
    segment,
)
from cuberecon.analysis.cases import oll_table, pll_table
from cuberecon.cube import Cube, format_moves, invert, parse_moves, strip_rotations
from cuberecon.io import Solve, TimedMove

# White cross on D after x2, a y' during F2L, Antisune and T perm.
SOLVE_A = [
    ("inspection", "x2"),
    ("cross", "R' D' F L' U2 B2 D"),
    ("f2l_1", "U R U' R'"),
    ("f2l_2", "y' L' U' L"),
    ("f2l_3", "U R U2 R' U R U' R'"),
    ("f2l_4", "U L U' L'"),
    ("oll", "U2 R U2 R' U' R U' R'"),
    ("pll", "U R U R' U' R' F R2 U' R' U' R U R' F'"),
    ("auf", "U'"),
]

# Yellow cross (no inspection rotation), wide d in F2L, OLL 24 with r, Ua perm with M.
SOLVE_B = [
    ("inspection", ""),
    ("cross", "F2 D' L2 B' D R2"),
    ("f2l_1", "R U R'"),
    ("f2l_2", "d L' U L"),
    ("f2l_3", "U' F' U F"),
    ("f2l_4", "U L U2 L'"),
    ("oll", "r U R' U' r' F R F'"),
    ("pll", "M2 U M U2 M' U M2"),
    ("auf", "U2"),
]


def build(parts):
    solution = " ".join(p for _, p in parts if p)
    scramble = format_moves(invert(strip_rotations(solution)))
    expected, i = {}, 0
    for step, p in parts:
        n = len(parse_moves(p))
        expected[step] = (i, i + n)
        i += n
    return scramble, solution, expected


def test_case_tables_are_complete():
    # 57 OLL and 21 PLL classes, all distinct up to AUF and orientation.
    assert len(oll_table()) == len(OLL_ALGS) == 57
    assert len(pll_table()) == len(PLL_ALGS) == 21


@pytest.mark.parametrize("alg", list(OLL_ALGS.values()) + list(PLL_ALGS.values()))
def test_reference_algs_preserve_f2l(alg):
    # Each reference alg solves a last-layer case: F2L stays solved on the yellow side.
    result = segment(format_moves(invert(strip_rotations(alg))), alg)
    assert result.complete and result.cross_color == "D"
    assert result.step("f2l_4").end == result.step("inspection").end


@pytest.mark.parametrize("number", sorted(OLL_ALGS))
@pytest.mark.parametrize("pre", ["", "U", "U2", "U'"])
def test_oll_recognition_any_auf_and_orientation(number, pre):
    # Case set up with an extra AUF, then seen in a random orientation.
    state = Cube().apply(invert(OLL_ALGS[number])).apply(invert(pre))
    match = recognize_oll(state)
    assert match is not None and match.case_id == f"OLL {number}"
    assert state.apply(match.pre_auf).apply(OLL_ALGS[number]).face_stickers("U") == "U" * 9
    turned = state.apply("z y")
    assert recognize_oll(turned, ll_color="U").case_id == f"OLL {number}"


@pytest.mark.parametrize("name", sorted(PLL_ALGS))
@pytest.mark.parametrize("pre", ["", "U", "U2", "U'"])
@pytest.mark.parametrize("post", ["", "U", "U2"])
def test_pll_recognition_any_auf_and_orientation(name, pre, post):
    state = Cube().apply(invert(post)).apply(invert(PLL_ALGS[name])).apply(invert(pre))
    match = recognize_pll(state)
    assert match is not None and match.case_id == f"PLL {name}"
    after = state.apply(match.pre_auf).apply(PLL_ALGS[name])
    assert any(after.apply(a).is_solved() for a in ["", "U", "U2", "U'"])
    assert recognize_pll(state.apply("x2 y"), ll_color="U").case_id == f"PLL {name}"


def test_skips():
    assert recognize_oll(Cube().apply("U")).case_id == "OLL skip"
    assert recognize_pll(Cube().apply("U2")).case_id == "PLL skip"
    assert recognize_pll(Cube().apply(invert(OLL_ALGS[27]))) is None


@pytest.mark.parametrize("parts", [SOLVE_A, SOLVE_B], ids=["A", "B"])
def test_full_cfop_solve_segmentation(parts):
    scramble, solution, expected = build(parts)
    assert Cube().apply(scramble).apply(solution).is_solved()
    result = segment(scramble, solution)
    assert result.complete
    assert {s.step: (s.start, s.end) for s in result.steps} == expected


def test_solve_a_details():
    scramble, solution, _ = build(SOLVE_A)
    result = segment(scramble, solution)
    assert result.cross_color == "U"  # white
    assert result.step("oll").case.case_id == "OLL 26"
    assert result.step("oll").case.pre_auf == "U2"
    assert result.step("pll").case.case_id == "PLL T"
    assert result.step("pll").case.pre_auf == "U"


def test_solve_b_details():
    scramble, solution, _ = build(SOLVE_B)
    result = segment(scramble, solution)
    assert result.cross_color == "D"  # yellow
    assert result.step("oll").case.case_id == "OLL 24"
    assert result.step("pll").case.case_id == "PLL Ua"


def test_ll_skips_and_xcross_give_empty_steps():
    # Only a T perm: cross and F2L already solved, OLL skip.
    result = segment(format_moves(invert(PLL_ALGS["T"])), PLL_ALGS["T"])
    assert result.complete
    assert all(result.step(s).start == result.step(s).end for s in ("cross", "f2l_1", "oll"))
    assert result.step("oll").case.case_id == "OLL skip"
    assert result.step("pll").case.case_id == "PLL T"
    # Sune that also permutes: PLL skip, no AUF.
    result = segment(format_moves(invert(OLL_ALGS[27])), OLL_ALGS[27])
    assert result.step("oll").case.case_id == "OLL 27"
    assert result.step("pll").case.case_id == "PLL skip"
    assert result.step("auf").start == result.step("auf").end


def test_incomplete_solve():
    scramble, solution, expected = build(SOLVE_A)
    moves = parse_moves(solution)[: expected["f2l_3"][0] + 2]
    result = segment(scramble, moves)
    assert not result.complete
    assert [s.step for s in result.steps] == ["inspection", "cross", "f2l_1", "f2l_2"]


def timed(solution, move_ms=100.0, gap_ms=50.0, pauses=None):
    pauses = pauses or {}
    out, t = [], 0.0
    for i, m in enumerate(parse_moves(solution)):
        t += pauses.get(i, 0.0)
        out.append(TimedMove(str(m), t, t + move_ms))
        t += move_ms + gap_ms
    return out


def test_analyze_solve_stats():
    scramble, solution, expected = build(SOLVE_A)
    oll_start = expected["oll"][0]
    moves = timed(solution, pauses={1: 2000.0, oll_start: 600.0})
    solve = analyze(Solve(scramble=scramble, moves=moves))

    assert [s.step for s in solve.segments] == [s for s, _ in SOLVE_A]
    assert {s.step: s.move_range for s in solve.segments} == expected
    oll = next(s for s in solve.segments if s.step == "oll")
    assert oll.case_id == "OLL 26"
    assert oll.t_start_ms == moves[oll_start].t_start_ms

    st = solve.stats
    assert st["complete"] and st["cross_color"] == "white"
    n = len(moves) - 1  # inspection x2 excluded
    assert st["moves_etm"] == n
    assert st["rotations"] == 1  # the y' in F2L
    assert st["moves_stm"] == n - 1
    total = moves[-1].t_end_ms - moves[1].t_start_ms
    assert st["total_time_ms"] == pytest.approx(total)
    assert st["tps_etm"] == pytest.approx(n * 1000 / total, abs=1e-3)
    # The 2 s pause is during inspection (before move 1), so only the OLL one counts.
    assert st["pauses"] == [{"after_move": oll_start - 1, "duration_ms": 650.0}]
    assert st["steps"]["oll"]["recognition_ms"] == 650.0
    assert st["steps"]["cross"]["recognition_ms"] == 0.0
    assert st["steps"]["f2l_2"]["rotations"] == 1
    steps_total = sum(s["duration_ms"] for s in st["steps"].values())
    assert steps_total == pytest.approx(total)
