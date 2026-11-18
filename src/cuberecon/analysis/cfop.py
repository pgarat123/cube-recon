"""CFOP segmentation of a solve, from the scramble and the move list.

Steps: inspection (leading rotations), cross, four F2L pairs, OLL, PLL, AUF.
The cross color is detected (any of the six colors). Every check is made relative
to the centers, so rotations, wide moves and slices are handled naturally.

Boundaries are move indices: a step covers the half-open range
``[start, end)`` of the move list. A step can be empty (x-cross, multislotting,
skips).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import cache

from cuberecon.cube import (
    CORNERS,
    EDGES,
    FACES,
    OPPOSITE,
    Cube,
    Move,
    MovesLike,
    as_moves,
    center_index,
    face_of,
)

from .cases import CaseMatch, recognize_oll, recognize_pll

STEPS: tuple[str, ...] = (
    "inspection",
    "cross",
    "f2l_1",
    "f2l_2",
    "f2l_3",
    "f2l_4",
    "oll",
    "pll",
    "auf",
)

Piece = tuple[int, ...]


def _faces(piece: Piece) -> frozenset[str]:
    return frozenset(face_of(i) for i in piece)


@cache
def _cross_edges(face: str) -> tuple[Piece, ...]:
    return tuple(e for e in EDGES if face in _faces(e))


@cache
def _slots(face: str) -> tuple[tuple[Piece, Piece], ...]:
    """(corner, middle-layer edge) of each F2L slot around ``face``."""
    slots = []
    for corner in CORNERS:
        faces = _faces(corner)
        if face in faces:
            sides = faces - {face}
            edge = next(e for e in EDGES if _faces(e) == sides)
            slots.append((corner, edge))
    return tuple(slots)


def _piece_solved(facelets: str, piece: Piece) -> bool:
    return all(facelets[i] == facelets[center_index(face_of(i))] for i in piece)


def cross_solved(cube: Cube, color: str) -> bool:
    f = cube.facelets
    return all(_piece_solved(f, e) for e in _cross_edges(cube.face_of_color(color)))


def solved_pairs(cube: Cube, color: str) -> int:
    f = cube.facelets
    return sum(
        _piece_solved(f, corner) and _piece_solved(f, edge)
        for corner, edge in _slots(cube.face_of_color(color))
    )


def f2l_solved(cube: Cube, color: str) -> bool:
    return cross_solved(cube, color) and solved_pairs(cube, color) == 4


def ll_oriented(cube: Cube, color: str) -> bool:
    """True when the face opposite the ``color`` cross is a single color."""
    return len(set(cube.face_stickers(OPPOSITE[cube.face_of_color(color)]))) == 1


def solved_up_to_auf(cube: Cube, color: str) -> bool:
    if cube.is_solved():
        return True
    ll_face = OPPOSITE[cube.face_of_color(color)]
    return any(cube.apply([Move(ll_face, a)]).is_solved() for a in (1, 2, -1))


@dataclass(frozen=True)
class StepRange:
    step: str
    start: int
    end: int
    case: CaseMatch | None = None


@dataclass(frozen=True)
class CfopResult:
    cross_color: str | None
    """Color letter of the cross (as in ``Cube.facelets``), None if no cross."""
    steps: tuple[StepRange, ...]
    complete: bool
    """True when every step up to the final AUF was found."""

    def step(self, name: str) -> StepRange | None:
        return next((s for s in self.steps if s.step == name), None)


def segment(scramble: MovesLike, moves: MovesLike) -> CfopResult:
    """Split ``moves`` (a solve of ``scramble``) into CFOP steps."""
    move_list = as_moves(moves)
    states = [Cube().apply(scramble)]
    for move in move_list:
        states.append(states[-1].apply([move]))
    n = len(move_list)

    def first(pred: Callable[[Cube], bool], start: int) -> int | None:
        return next((i for i in range(start, n + 1) if pred(states[i])), None)

    rot_end = 0
    while rot_end < n and move_list[rot_end].is_rotation:
        rot_end += 1
    steps = [StepRange("inspection", 0, rot_end)]

    # The cross color is the one whose F2L is completed first.
    best: tuple[float, float, str] | None = None
    for color in FACES:
        cross_i = first(lambda s, c=color: cross_solved(s, c), rot_end)
        if cross_i is None:
            continue
        f2l_i = first(lambda s, c=color: f2l_solved(s, c), rot_end)
        key = (float("inf") if f2l_i is None else f2l_i, cross_i, color)
        if best is None or key < best:
            best = key
    if best is None:
        return CfopResult(None, tuple(steps), False)
    color = best[2]
    ll_color = OPPOSITE[color]

    def done() -> CfopResult:
        return CfopResult(color, tuple(steps), False)

    cross_end = int(best[1])
    steps.append(StepRange("cross", rot_end, cross_end))
    prev = cross_end
    for k in range(1, 5):
        end = first(lambda s, k=k: cross_solved(s, color) and solved_pairs(s, color) >= k, prev)
        if end is None:
            return done()
        steps.append(StepRange(f"f2l_{k}", prev, end))
        prev = end

    oll_end = first(lambda s: f2l_solved(s, color) and ll_oriented(s, color), prev)
    if oll_end is None:
        return done()
    steps.append(StepRange("oll", prev, oll_end, recognize_oll(states[prev], ll_color)))

    pll_end = first(
        lambda s: f2l_solved(s, color) and ll_oriented(s, color) and solved_up_to_auf(s, color),
        oll_end,
    )
    if pll_end is None:
        return done()
    steps.append(StepRange("pll", oll_end, pll_end, recognize_pll(states[oll_end], ll_color)))

    auf_end = first(Cube.is_solved, pll_end)
    if auf_end is None:
        return done()
    steps.append(StepRange("auf", pll_end, auf_end))
    return CfopResult(color, tuple(steps), True)
