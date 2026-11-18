import pytest

from cuberecon.cube import (
    CORNERS,
    EDGES,
    ROTATIONS,
    Cube,
    Move,
    NotationError,
    center_index,
    face_of,
    format_moves,
    invert,
    parse_move,
    parse_moves,
    strip_rotations,
)
from cuberecon.cube.notation import VALID_BASES

ALL_BASES = sorted(VALID_BASES)


def stickers(cube: Cube, indices) -> str:
    return "".join(cube.facelets[i] for i in indices)


# Expected effect of one clockwise move on a solved cube: (indices, expected colors).
# U face indices 0-8, R 9-17, F 18-26, D 27-35, L 36-44, B 45-53.
SINGLE_MOVE_EFFECTS = {
    "R": ((2, 5, 8), "FFF"),
    "U": ((18, 19, 20), "RRR"),
    "F": ((6, 7, 8), "LLL"),
    "L": ((0, 3, 6), "BBB"),
    "D": ((24, 25, 26), "LLL"),
    "B": ((0, 1, 2), "RRR"),
    "M": ((1, 4, 7), "BBB"),
    "E": ((21, 22, 23), "LLL"),
    "S": ((3, 4, 5), "LLL"),
    "r": ((1, 2, 4, 5, 7, 8), "FFFFFF"),
    "Rw": ((1, 2, 4, 5, 7, 8), "FFFFFF"),
    "x": (tuple(range(9)), "F" * 9),
    "y": (tuple(range(18, 27)), "R" * 9),
    "z": (tuple(range(9)), "L" * 9),
}


@pytest.mark.parametrize("move", SINGLE_MOVE_EFFECTS)
def test_single_move_on_solved_cube(move):
    indices, expected = SINGLE_MOVE_EFFECTS[move]
    assert stickers(Cube().apply(move), indices) == expected


@pytest.mark.parametrize("base", ALL_BASES)
def test_every_move_has_order_four_and_inverse(base):
    c = Cube().apply("R U2 F' L D B2")  # arbitrary start
    assert c.apply([Move(base)] * 4) == c
    assert c.apply([Move(base), Move(base, -1)]) == c
    assert c.apply([Move(base, 2)]) == c.apply([Move(base)] * 2)
    assert c.apply([Move(base)]) != c


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("r", "R M'"),
        ("Rw", "r"),
        ("l", "L M"),
        ("u", "U E'"),
        ("d", "D E"),
        ("f", "F S"),
        ("b", "B S'"),
        ("Uw2", "U2 E2"),
        ("x", "R M' L'"),
        ("y", "U E' D'"),
        ("z", "F S B'"),
        ("M2", "M' M'"),
    ],
)
def test_move_identities(left, right):
    start = Cube().apply("F2 R' D L2 B U'")
    assert start.apply(left) == start.apply(right)


def test_rotations_keep_cube_solved_and_count_24():
    assert len(ROTATIONS) == 24
    for seq, _ in ROTATIONS:
        assert Cube().apply(list(seq)).is_solved()
    assert not Cube().apply("M").is_solved()


def test_known_sequences():
    sexy = "R U R' U' "
    assert Cube().apply(sexy * 6).is_solved()
    assert not Cube().apply(sexy * 3).is_solved()
    tperm = "R U R' U' R' F R2 U' R' U' R U R' F'"
    assert Cube().apply(f"{tperm} {tperm}").is_solved()
    sune = "R U R' U R U2 R' "
    assert Cube().apply(sune * 6).is_solved()


def test_superflip():
    f = Cube().apply("U R2 F B R B2 R U2 L B2 R U' D' R2 F R' L B2 U2 F2").facelets

    def home(i: int) -> str:
        return f[center_index(face_of(i))]

    assert all(f[i] == home(i) for corner in CORNERS for i in corner)
    assert all(f[i] == home(j) and f[j] == home(i) for i, j in EDGES)


WCA_SCRAMBLES = [
    "D2 F2 U' R2 U' L2 U F2 D2 R2 U2 F' D' L B' R2 D2 L' F' U2",
    "R' U' F L2 D2 F2 R2 U' B2 U' R2 U' F2 L' D B' U2 L2 B2 R' U' F",
    "B' L2 D' R2 U F2 D' L2 D2 R2 U' B2 R' D U' F L' B' D2 L",
]


@pytest.mark.parametrize("scramble", WCA_SCRAMBLES)
def test_scramble_plus_inverse_is_solved(scramble):
    state = Cube().apply(scramble)
    assert not state.is_solved()
    assert state.apply(invert(scramble)).is_solved()


def test_known_solution_solves_its_scramble():
    # Scramble = inverse of a known sequence, solution with rotations, wide moves and slices.
    solution = "x2 y' r U R' U' r' F R F' M2 U M U2 M' U M2 z' S E' d2 x"
    scramble = format_moves(invert(strip_rotations(solution)))
    assert "x" not in scramble and "y" not in scramble
    assert Cube().apply(scramble).apply(solution).is_solved()


def test_strip_rotations_reaches_same_state_up_to_rotation():
    seq = "y R U x' F2 z M E' S2 r' u2 y2 B"
    stripped = strip_rotations(seq)
    assert not any(m.is_rotation for m in stripped)
    assert Cube().apply(seq).equivalent(Cube().apply(stripped))
    assert format_moves(strip_rotations("y R")) == "B"
    assert format_moves(strip_rotations("x2 r U")) == "r D"


def test_parse_and_format():
    moves = parse_moves("(R U R' U') r2 Rw' M E2 S' x y2 z' R2' // comment\nU")
    assert format_moves(moves) == "R U R' U' r2 Rw' M E2 S' x y2 z' R2 U"
    assert parse_move("R’") == Move("R", -1)
    assert parse_move("U'2") == Move("U", 2)
    assert Move("Rw").kind == "wide" and Move("r").kind == "wide"
    assert Move("M").kind == "slice" and Move("x").kind == "rotation"
    assert Move("D").kind == "face"


@pytest.mark.parametrize("bad", ["Q", "R3", "Mw", "xw", "R''", "2R"])
def test_parse_rejects_invalid_tokens(bad):
    with pytest.raises(NotationError):
        parse_move(bad)


def test_invert():
    assert format_moves(invert("R U2 F' Rw M x")) == "x' M' Rw' F U2 R'"
    assert invert("") == []


def test_reoriented_and_equivalent():
    c = Cube().apply("R U F")
    turned = c.apply("x y")
    assert turned != c and turned.equivalent(c)
    assert turned.reoriented(c.center("U"), c.center("F")) == c
    with pytest.raises(ValueError):
        Cube().reoriented("U", "D")
