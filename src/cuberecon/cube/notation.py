"""WCA-style move notation: parsing, formatting and inversion.

Supported: face turns (R U F L D B), wide turns (Rw or r ...), slices (M E S),
rotations (x y z), each with an optional ' or 2 suffix. ``R2'`` is accepted and
read as ``R2``. Parentheses are ignored and ``//`` starts a comment.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

FACE_LETTERS = "URFDLB"
SLICE_LETTERS = "MES"
ROTATION_LETTERS = "xyz"

VALID_BASES: frozenset[str] = frozenset(
    [
        *FACE_LETTERS,
        *(f + "w" for f in FACE_LETTERS),
        *FACE_LETTERS.lower(),
        *SLICE_LETTERS,
        *ROTATION_LETTERS,
    ]
)

_TOKEN_RE = re.compile(r"([URFDLB]w|[URFDLBrufdlbMESxyz])(2'|'2|2|'|)")
_SUFFIX_AMOUNT = {"": 1, "'": -1, "2": 2, "2'": 2, "'2": 2}
_AMOUNT_SUFFIX = {1: "", -1: "'", 2: "2"}
_PRIME_VARIANTS = str.maketrans({"’": "'", "‘": "'", "´": "'", "`": "'"})


class NotationError(ValueError):
    """Raised when a move token cannot be parsed."""


@dataclass(frozen=True, slots=True)
class Move:
    """A single move. ``amount`` is 1 (clockwise), -1 (counterclockwise) or 2."""

    base: str
    amount: int = 1

    def __post_init__(self) -> None:
        if self.base not in VALID_BASES:
            raise NotationError(f"unknown move base {self.base!r}")
        if self.amount not in _AMOUNT_SUFFIX:
            raise NotationError(f"invalid move amount {self.amount!r}")

    @property
    def kind(self) -> str:
        """One of ``face``, ``wide``, ``slice``, ``rotation``."""
        if self.base in ROTATION_LETTERS:
            return "rotation"
        if self.base in SLICE_LETTERS:
            return "slice"
        if self.base in FACE_LETTERS:
            return "face"
        return "wide"

    @property
    def is_rotation(self) -> bool:
        return self.base in ROTATION_LETTERS

    @property
    def quarter_turns(self) -> int:
        """Number of clockwise quarter turns (1, 2 or 3)."""
        return self.amount % 4

    def inverse(self) -> Move:
        return Move(self.base, 2 if self.amount == 2 else -self.amount)

    def __str__(self) -> str:
        return self.base + _AMOUNT_SUFFIX[self.amount]


MovesLike = str | Iterable[Move | str]


def parse_move(token: str) -> Move:
    match = _TOKEN_RE.fullmatch(token.strip().translate(_PRIME_VARIANTS))
    if match is None:
        raise NotationError(f"cannot parse move {token!r}")
    return Move(match.group(1), _SUFFIX_AMOUNT[match.group(2)])


def parse_moves(text: str) -> list[Move]:
    """Parse a whitespace separated sequence such as ``"R U R' U' (r U2 r')"``."""
    code = " ".join(line.split("//", 1)[0] for line in text.splitlines())
    code = code.replace("(", " ").replace(")", " ")
    return [parse_move(tok) for tok in code.split()]


def as_moves(moves: MovesLike) -> list[Move]:
    """Normalize a string or an iterable of moves / tokens into a list of ``Move``."""
    if isinstance(moves, str):
        return parse_moves(moves)
    return [m if isinstance(m, Move) else parse_move(m) for m in moves]


def format_moves(moves: MovesLike) -> str:
    return " ".join(str(m) for m in as_moves(moves))


def invert(moves: MovesLike) -> list[Move]:
    """Inverse sequence: reversed order, each move inverted."""
    return [m.inverse() for m in reversed(as_moves(moves))]
