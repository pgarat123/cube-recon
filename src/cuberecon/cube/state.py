"""Cube state on 54 facelets and move application."""

from __future__ import annotations

from collections.abc import Iterable
from functools import cache

from .geometry import (
    FACES,
    IDENTITY,
    NORMALS,
    Perm,
    Vec,
    center_index,
    compose,
    invert_permutation,
    quarter_turn_permutation,
)
from .notation import VALID_BASES, Move, MovesLike, as_moves, parse_moves

_ALL_LAYERS = frozenset({-1, 0, 1})


def _move_specs() -> dict[str, tuple[Vec, frozenset[int]]]:
    specs: dict[str, tuple[Vec, frozenset[int]]] = {}
    for face in FACES:
        axis = NORMALS[face]
        specs[face] = (axis, frozenset({1}))
        specs[face + "w"] = (axis, frozenset({0, 1}))
        specs[face.lower()] = (axis, frozenset({0, 1}))
    # Slices follow the WCA convention: M like L, E like D, S like F.
    specs["M"] = (NORMALS["L"], frozenset({0}))
    specs["E"] = (NORMALS["D"], frozenset({0}))
    specs["S"] = (NORMALS["F"], frozenset({0}))
    # Rotations: x like R, y like U, z like F.
    specs["x"] = (NORMALS["R"], _ALL_LAYERS)
    specs["y"] = (NORMALS["U"], _ALL_LAYERS)
    specs["z"] = (NORMALS["F"], _ALL_LAYERS)
    return specs


_SPECS = _move_specs()


@cache
def _quarter(base: str) -> Perm:
    axis, layers = _SPECS[base]
    return quarter_turn_permutation(axis, layers)


@cache
def move_permutation(move: Move) -> Perm:
    perm = IDENTITY
    for _ in range(move.quarter_turns):
        perm = compose(perm, _quarter(move.base))
    return perm


def sequence_permutation(moves: MovesLike) -> Perm:
    perm = IDENTITY
    for move in as_moves(moves):
        perm = compose(perm, move_permutation(move))
    return perm


def _whole_cube_rotations() -> tuple[tuple[tuple[Move, ...], Perm], ...]:
    """The 24 orientations, each with a short rotation sequence reaching it."""
    generators = [Move(b, a) for b in "xyz" for a in (1, 2, -1)]
    seen: dict[Perm, tuple[Move, ...]] = {IDENTITY: ()}
    frontier = [IDENTITY]
    while frontier:
        nxt = []
        for perm in frontier:
            for gen in generators:
                new = compose(perm, move_permutation(gen))
                if new not in seen:
                    seen[new] = (*seen[perm], gen)
                    nxt.append(new)
        frontier = nxt
    return tuple((seq, perm) for perm, seq in seen.items())


ROTATIONS: tuple[tuple[tuple[Move, ...], Perm], ...] = _whole_cube_rotations()

SOLVED_FACELETS = "".join(face * 9 for face in FACES)


class Cube:
    """Immutable cube state.

    ``facelets`` is a 54 character string in URFDLB order. Each character is the
    color of the sticker, written as the letter of the face that color belongs to
    on a solved cube in the reference orientation (``U`` is the U color, white in
    the standard scheme, and so on).
    """

    __slots__ = ("_facelets",)

    def __init__(self, facelets: str = SOLVED_FACELETS) -> None:
        if len(facelets) != 54:
            raise ValueError(f"expected 54 facelets, got {len(facelets)}")
        self._facelets = facelets

    @property
    def facelets(self) -> str:
        return self._facelets

    def apply(self, moves: MovesLike) -> Cube:
        """Return the state after applying ``moves`` (a string or a list of moves)."""
        facelets = self._facelets
        for move in as_moves(moves):
            facelets = "".join(facelets[i] for i in move_permutation(move))
        return Cube(facelets)

    def apply_permutation(self, perm: Perm) -> Cube:
        return Cube("".join(self._facelets[i] for i in perm))

    def center(self, face: str) -> str:
        """Color of the center currently on ``face``."""
        return self._facelets[center_index(face)]

    def face_stickers(self, face: str) -> str:
        start = FACES.index(face) * 9
        return self._facelets[start : start + 9]

    def face_of_color(self, color: str) -> str:
        """Face currently holding the center of ``color``."""
        for face in FACES:
            if self.center(face) == color:
                return face
        raise ValueError(f"no center of color {color!r}")

    def is_solved(self) -> bool:
        """True when every face is a single color, whatever the orientation."""
        return all(len(set(self.face_stickers(face))) == 1 for face in FACES)

    def reoriented(self, up: str, front: str | None = None) -> Cube:
        """Same state seen in the orientation with ``up`` on U (and ``front`` on F)."""
        for _, perm in ROTATIONS:
            candidate = self.apply_permutation(perm)
            if candidate.center("U") == up and (front is None or candidate.center("F") == front):
                return candidate
        raise ValueError(f"no orientation with up={up!r} and front={front!r}")

    def equivalent(self, other: Cube) -> bool:
        """True when both states are equal up to a whole-cube rotation."""
        return any(self.apply_permutation(perm) == other for _, perm in ROTATIONS)

    def to_net(self) -> str:
        """Multi-line unfolded view, handy for debugging."""
        f = self.face_stickers

        def rows(face: str) -> list[str]:
            s = f(face)
            return [" ".join(s[r * 3 : r * 3 + 3]) for r in range(3)]

        pad = " " * 6
        lines = [pad + r for r in rows("U")]
        lines += [" ".join(parts) for parts in zip(*(rows(x) for x in "LFRB"), strict=True)]
        lines += [pad + r for r in rows("D")]
        return "\n".join(lines)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Cube) and other._facelets == self._facelets

    def __hash__(self) -> int:
        return hash(self._facelets)

    def __repr__(self) -> str:
        return f"Cube({self._facelets!r})"


def _style(move: Move) -> str:
    if move.kind == "wide":
        return "wide_lower" if move.base.islower() else "wide_upper"
    return move.kind


def _build_lookup() -> dict[tuple[str, Perm], Move]:
    lookup: dict[tuple[str, Perm], Move] = {}
    for base in sorted(VALID_BASES):
        for amount in (1, 2, -1):
            move = Move(base, amount)
            if not move.is_rotation:
                lookup[(_style(move), move_permutation(move))] = move
    return lookup


_LOOKUP = _build_lookup()


def strip_rotations(moves: MovesLike) -> list[Move]:
    """Rewrite ``moves`` without rotations.

    Rotations are pushed to the end of the sequence and dropped, so the result
    reaches the same state up to a whole-cube rotation. Wide moves and slices are
    kept as they are (only renamed to account for the rotations before them).
    """
    out: list[Move] = []
    rot = IDENTITY
    rot_inv = IDENTITY
    for move in as_moves(moves):
        perm = move_permutation(move)
        if move.is_rotation:
            rot = compose(rot, perm)
            rot_inv = invert_permutation(rot)
            continue
        conjugated = tuple(rot[perm[rot_inv[k]]] for k in range(54))
        out.append(_LOOKUP[(_style(move), conjugated)])
    return out


def solved() -> Cube:
    return Cube()


def scrambled(scramble: str | Iterable[Move | str]) -> Cube:
    """State of a solved cube after ``scramble`` in the reference orientation."""
    if isinstance(scramble, str):
        scramble = parse_moves(scramble)
    return Cube().apply(scramble)
