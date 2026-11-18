"""Geometry of the 3x3 cube: sticker coordinates, pieces and layer-turn permutations.

Facelet layout follows the usual URFDLB order (as in Kociemba's facelet string):
indices 0-8 are U, 9-17 R, 18-26 F, 27-35 D, 36-44 L, 45-53 B. Each face is read
row by row as seen from outside the cube, with U on top for the side faces, B on
top for U and F on top for D.

Coordinates: x points to R, y to U, z to F. Each sticker is identified by the
position of its cubie and the normal of the face it lies on.
"""

from __future__ import annotations

Vec = tuple[int, int, int]
Perm = tuple[int, ...]

FACES: tuple[str, ...] = ("U", "R", "F", "D", "L", "B")
NORMALS: dict[str, Vec] = {
    "U": (0, 1, 0),
    "R": (1, 0, 0),
    "F": (0, 0, 1),
    "D": (0, -1, 0),
    "L": (-1, 0, 0),
    "B": (0, 0, -1),
}
OPPOSITE: dict[str, str] = {"U": "D", "D": "U", "R": "L", "L": "R", "F": "B", "B": "F"}


def _sticker_position(face: str, row: int, col: int) -> Vec:
    if face == "U":
        return (col - 1, 1, row - 1)
    if face == "R":
        return (1, 1 - row, 1 - col)
    if face == "F":
        return (col - 1, 1 - row, 1)
    if face == "D":
        return (col - 1, -1, 1 - row)
    if face == "L":
        return (-1, 1 - row, col - 1)
    return (1 - col, 1 - row, -1)  # B


STICKERS: tuple[tuple[Vec, Vec], ...] = tuple(
    (_sticker_position(face, i // 3, i % 3), NORMALS[face]) for face in FACES for i in range(9)
)
_INDEX: dict[tuple[Vec, Vec], int] = {s: i for i, s in enumerate(STICKERS)}

IDENTITY: Perm = tuple(range(54))


def face_of(index: int) -> str:
    """Face letter of the position holding facelet ``index``."""
    return FACES[index // 9]


def center_index(face: str) -> int:
    return FACES.index(face) * 9 + 4


def _pieces(n_nonzero: int) -> tuple[tuple[int, ...], ...]:
    groups: dict[Vec, list[int]] = {}
    for i, (pos, _) in enumerate(STICKERS):
        if sum(1 for c in pos if c) == n_nonzero:
            groups.setdefault(pos, []).append(i)
    return tuple(tuple(v) for v in groups.values())


EDGES: tuple[tuple[int, ...], ...] = _pieces(2)
CORNERS: tuple[tuple[int, ...], ...] = _pieces(3)


def _dot(a: Vec, b: Vec) -> int:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _rotate(v: Vec, axis: Vec) -> Vec:
    """Quarter turn of ``v`` around ``axis``, clockwise when seen from the +axis side."""
    d = _dot(axis, v)
    c = _cross(axis, v)
    return (axis[0] * d - c[0], axis[1] * d - c[1], axis[2] * d - c[2])


def quarter_turn_permutation(axis: Vec, layers: frozenset[int]) -> Perm:
    """Permutation of a clockwise quarter turn of the given layers.

    ``layers`` holds values of ``dot(position, axis)`` (1 = the face itself, 0 = the
    middle slice, -1 = the opposite face). The result ``p`` means
    ``new[j] = old[p[j]]``.
    """
    perm = list(IDENTITY)
    for i, (pos, normal) in enumerate(STICKERS):
        if _dot(pos, axis) in layers:
            perm[_INDEX[(_rotate(pos, axis), _rotate(normal, axis))]] = i
    return tuple(perm)


def compose(first: Perm, second: Perm) -> Perm:
    """Permutation equivalent to applying ``first`` then ``second``."""
    return tuple(first[j] for j in second)


def invert_permutation(perm: Perm) -> Perm:
    inverse = [0] * len(perm)
    for j, i in enumerate(perm):
        inverse[i] = j
    return tuple(inverse)
