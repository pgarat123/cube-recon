"""Recognition of OLL (57) and PLL (21) cases from the cube state.

Cases are identified by state, not by algorithm: each reference algorithm below
only serves to build the case table (case state = inverse of the algorithm
applied to a solved cube). Recognition is independent of the AUF and of the
cube orientation. The ``pre_auf`` of a match is the U turn to do, in the frame
of the given state, before the reference algorithm.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

from cuberecon.cube import Cube, invert

OLL_ALGS: dict[int, str] = {
    1: "R U2 R2 F R F' U2 R' F R F'",
    2: "F R U R' U' F' f R U R' U' f'",
    3: "f R U R' U' f' U' F R U R' U' F'",
    4: "f R U R' U' f' U F R U R' U' F'",
    5: "r' U2 R U R' U r",
    6: "r U2 R' U' R U' r'",
    7: "r U R' U R U2 r'",
    8: "l' U' L U' L' U2 l",
    9: "R U R' U' R' F R2 U R' U' F'",
    10: "R U R' U R' F R F' R U2 R'",
    11: "r U R' U R' F R F' R U2 r'",
    12: "M' R' U' R U' R' U2 R U' M",
    13: "r U' r' U' r U r' F' U F",
    14: "R' F R U R' F' R F U' F'",
    15: "r' U' r R' U' R U r' U r",
    16: "r U r' R U R' U' r U' r'",
    17: "R U R' U R' F R F' U2 R' F R F'",
    18: "r U R' U R U2 r2 U' R U' R' U2 r",
    19: "M U R U R' U' M' R' F R F'",
    20: "r U R' U' M2 U R U' R' U' M'",
    21: "R U2 R' U' R U R' U' R U' R'",
    22: "R U2 R2 U' R2 U' R2 U2 R",
    23: "R2 D' R U2 R' D R U2 R",
    24: "r U R' U' r' F R F'",
    25: "F' r U R' U' r' F R",
    26: "R U2 R' U' R U' R'",
    27: "R U R' U R U2 R'",
    28: "r U R' U' r' R U R U' R'",
    29: "R U R' U' R U' R' F' U' F R U R'",
    30: "F R' F R2 U' R' U' R U R' F2",
    31: "R' U' F U R U' R' F' R",
    32: "L U F' U' L' U L F L'",
    33: "R U R' U' R' F R F'",
    34: "R U R2 U' R' F R U R U' F'",
    35: "R U2 R2 F R F' R U2 R'",
    36: "L' U' L U' L' U L U L F' L' F",
    37: "F R' F' R U R U' R'",
    38: "R U R' U R U' R' U' R' F R F'",
    39: "L F' L' U' L U F U' L'",
    40: "R' F R U R' U' F' U R",
    41: "R U R' U R U2 R' F R U R' U' F'",
    42: "R' U' R U' R' U2 R F R U R' U' F'",
    43: "F' U' L' U L F",
    44: "F U R U' R' F'",
    45: "F R U R' U' F'",
    46: "R' U' R' F R F' U R",
    47: "R' U' R' F R F' R' F R F' U R",
    48: "F R U R' U' R U R' U' F'",
    49: "r U' r2 U r2 U r2 U' r",
    50: "r' U r2 U' r2 U' r2 U r'",
    51: "F U R U' R' U R U' R' F'",
    52: "R U R' U R U' B U' B' R'",
    53: "l' U2 L U L' U' L U L' U l",
    54: "r U2 R' U' R U R' U' R U' r'",
    55: "R U2 R2 U' R U' R' U2 F R F'",
    56: "r U r' U R U' R' U R U' R' r U' r'",
    57: "R U R' U' M' U R U' r'",
}

PLL_ALGS: dict[str, str] = {
    "Aa": "x R' U R' D2 R U' R' D2 R2 x'",
    "Ab": "x R2 D2 R U R' D2 R U' R x'",
    "E": "x' R U' R' D R U R' D' R U R' D R U' R' D' x",
    "F": "R' U' F' R U R' U' R' F R2 U' R' U' R U R' U R",
    "Ga": "R2 U R' U R' U' R U' R2 U' D R' U R D'",
    "Gb": "R' U' R U D' R2 U R' U R U' R U' R2 D",
    "Gc": "R2 U' R U' R U R' U R2 U D' R U' R' D",
    "Gd": "R U R' U' D R2 U' R U' R' U R' U R2 D'",
    "H": "M2 U M2 U2 M2 U M2",
    "Ja": "R' U L' U2 R U' R' U2 R L",
    "Jb": "R U R' F' R U R' U' R' F R2 U' R'",
    "Na": "R U R' U R U R' F' R U R' U' R' F R2 U' R' U2 R U' R'",
    "Nb": "R' U R U' R' F' U' F R U R' F R' F' R U' R",
    "Ra": "R U' R' U' R U R D R' U' R D' R' U2 R'",
    "Rb": "R2 F R U R U' R' F' R U2 R' U2 R",
    "T": "R U R' U' R' F R2 U' R' U' R U R' F'",
    "Ua": "M2 U M U2 M' U M2",
    "Ub": "M2 U' M U2 M' U' M2",
    "V": "R' U R' U' y R' F' R2 U' R' U R' F R F",
    "Y": "F R U' R' U' R U R' F' R U R' U' R' F R F'",
    "Z": "M' U M2 U M2 U M' U2 M2",
}

OLL_SKIP = "OLL skip"
PLL_SKIP = "PLL skip"

_U_FACE = tuple(range(9))
# Top-layer side stickers, read around the cube: F, R, B, L (left to right on each face).
_RING = (18, 19, 20, 9, 10, 11, 45, 46, 47, 36, 37, 38)
_RING_CENTERS = (22, 13, 49, 40)
_AUFS = ("", "U", "U'", "U2")


@dataclass(frozen=True)
class CaseMatch:
    case_id: str
    pre_auf: str = ""


def _oll_pattern(cube: Cube) -> tuple[bool, ...]:
    f = cube.facelets
    ll = cube.center("U")
    return tuple(f[i] == ll for i in _U_FACE + _RING)


def _oll_key(cube: Cube) -> tuple[bool, ...]:
    return min(_oll_pattern(cube.apply(a)) for a in _AUFS)


def _pll_offsets(cube: Cube) -> tuple[int, ...] | None:
    """Color of each ring sticker relative to the face it is on (0..3), or None."""
    f = cube.facelets
    ring_pos = {f[c]: k for k, c in enumerate(_RING_CENTERS)}
    if any(f[i] not in ring_pos for i in _RING):
        return None
    return tuple((ring_pos[f[i]] - n // 3) % 4 for n, i in enumerate(_RING))


def _pll_key(offsets: tuple[int, ...]) -> tuple[int, ...]:
    return min(
        tuple((offsets[(n + 3 * k) % 12] + m) % 4 for n in range(12))
        for k in range(4)
        for m in range(4)
    )


def _same_up_to_post_auf(a: tuple[int, ...], b: tuple[int, ...]) -> bool:
    return len({(x - y) % 4 for x, y in zip(a, b, strict=True)}) == 1


def _case_state(alg: str) -> Cube:
    return Cube().apply(invert(alg))


@cache
def oll_table() -> dict[tuple[bool, ...], tuple[str, tuple[bool, ...]]]:
    """Canonical pattern -> (case id, pattern in the reference algorithm's frame)."""
    table = {}
    for number, alg in OLL_ALGS.items():
        state = _case_state(alg)
        table[_oll_key(state)] = (f"OLL {number}", _oll_pattern(state))
    return table


@cache
def pll_table() -> dict[tuple[int, ...], tuple[str, tuple[int, ...]]]:
    table = {}
    for name, alg in PLL_ALGS.items():
        offsets = _pll_offsets(_case_state(alg))
        assert offsets is not None
        table[_pll_key(offsets)] = (f"PLL {name}", offsets)
    return table


def _ll_frame(cube: Cube, ll_color: str | None) -> Cube:
    if ll_color is None or cube.center("U") == ll_color:
        return cube
    return cube.reoriented(ll_color)


def recognize_oll(cube: Cube, ll_color: str | None = None) -> CaseMatch | None:
    """OLL case of ``cube`` (F2L must be solved, last layer color ``ll_color``).

    ``ll_color`` defaults to the color of the U center. Returns None when the top
    layer pattern is not a valid OLL case.
    """
    cube = _ll_frame(cube, ll_color)
    if all(_oll_pattern(cube)[:9]):
        return CaseMatch(OLL_SKIP)
    entry = oll_table().get(_oll_key(cube))
    if entry is None:
        return None
    case_id, reference = entry
    for auf in _AUFS:
        if _oll_pattern(cube.apply(auf)) == reference:
            return CaseMatch(case_id, auf)
    return None  # pragma: no cover (unreachable: the key matched)


def recognize_pll(cube: Cube, ll_color: str | None = None) -> CaseMatch | None:
    """PLL case of ``cube`` (F2L solved and last layer oriented)."""
    cube = _ll_frame(cube, ll_color)
    if not all(_oll_pattern(cube)[:9]):
        return None
    offsets = _pll_offsets(cube)
    if offsets is None:
        return None
    if len(set(offsets)) == 1:
        return CaseMatch(PLL_SKIP)
    entry = pll_table().get(_pll_key(offsets))
    if entry is None:
        return None
    case_id, reference = entry
    for auf in _AUFS:
        shifted = _pll_offsets(cube.apply(auf))
        if shifted is not None and _same_up_to_post_auf(shifted, reference):
            return CaseMatch(case_id, auf)
    return None  # pragma: no cover
