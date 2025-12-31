from __future__ import annotations

import pytest

from svg_path_editor.path_parser import PathParser


def test_move_to() -> None:
    """``m`` command parsing and validation."""
    with pytest.raises(ValueError):
        PathParser.parse("m 10")
    assert PathParser.parse("m 10 20") == [["m", "10", "20"]]


def test_exponents() -> None:
    """Exponent notation is supported."""
    assert PathParser.parse("m 1e3 2e-3") == [["m", "1e3", "2e-3"]]


def test_no_whitespace_between_negative_sign() -> None:
    """Allow negative sign to follow a number without whitespace."""
    assert PathParser.parse("M46-86") == [["M", "46", "-86"]]


def test_overloaded_move_to() -> None:
    """Implicit ``l`` following an ``m`` are expanded correctly."""
    assert PathParser.parse("m 12.5,52 39,0 0,-40 -39,0 z") == [
        ["m", "12.5", "52"],
        ["l", "39", "0"],
        ["l", "0", "-40"],
        ["l", "-39", "0"],
        ["z"],
    ]


def test_initial_move_missing() -> None:
    """Path must start with an ``M``/``m`` command."""
    with pytest.raises(ValueError, match="malformed"):
        PathParser.parse("l 1 1")


def test_curve_to() -> None:
    """``c`` command parsing and implicit repetition of command."""
    a = PathParser.parse("m0 0c 50,0 50,100 100,100 50,0 50,-100 100,-100")
    b = PathParser.parse("m0 0c 50,0 50,100 100,100 c 50,0 50,-100 100,-100")
    assert a == [
        ["m", "0", "0"],
        ["c", "50", "0", "50", "100", "100", "100"],
        ["c", "50", "0", "50", "-100", "100", "-100"],
    ]
    assert a == b


def test_line_to() -> None:
    """``l`` command parsing and validation."""
    with pytest.raises(ValueError, match="malformed"):
        PathParser.parse("m0 0l 10 10 0")

    assert PathParser.parse("m0 0l 10,10") == [["m", "0", "0"], ["l", "10", "10"]]
    assert PathParser.parse("m0 0l10 10 10 10") == [
        ["m", "0", "0"],
        ["l", "10", "10"],
        ["l", "10", "10"],
    ]


def test_horizontal_to() -> None:
    """``h`` command parsing."""
    assert PathParser.parse("m0 0 h 10.5") == [["m", "0", "0"], ["h", "10.5"]]


def test_vertical_to() -> None:
    """``v`` command parsing."""
    assert PathParser.parse("m0 0 v 10.5") == [["m", "0", "0"], ["v", "10.5"]]


def test_arc_to() -> None:
    """``A`` command parsing."""
    assert PathParser.parse("M0 0A 30 50 0 0 1 162.55 162.45") == [
        ["M", "0", "0"],
        ["A", "30", "50", "0", "0", "1", "162.55", "162.45"],
    ]
    assert PathParser.parse("M0 0A 60 60 0 01100 100") == [
        ["M", "0", "0"],
        ["A", "60", "60", "0", "0", "1", "100", "100"],
    ]


def test_quadratic_curve_to() -> None:
    """``Q`` command parsing."""
    assert PathParser.parse("M10 80 Q 95 10 180 80") == [
        ["M", "10", "80"],
        ["Q", "95", "10", "180", "80"],
    ]


def test_smooth_curve_to() -> None:
    """``S`` command parsing."""
    assert PathParser.parse("M0 0 S 1 2, 3 4") == [
        ["M", "0", "0"],
        ["S", "1", "2", "3", "4"],
    ]


def test_smooth_quadratic_curve_to() -> None:
    """``M`` command parsing."""
    with pytest.raises(ValueError):
        PathParser.parse("M0 0 t 1 2 3")
    assert PathParser.parse("M0 0 T 1 -200") == [
        ["M", "0", "0"],
        ["T", "1", "-200"],
    ]


def test_close() -> None:
    """``z`` command parsing."""
    assert PathParser.parse("m0 0z") == [["m", "0", "0"], ["z"]]
