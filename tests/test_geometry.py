# This file is part of https://github.com/KurtBoehm/svg-path-editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import itertools
from decimal import localcontext
from typing import Final

import pytest

from svg_path_editor import SvgPath
from svg_path_editor.geometry import Line, ParametricEllipticalArc, Point
from svg_path_editor.intersect import intersect
from svg_path_editor.math import Precision, as_bool
from svg_path_editor.svg import EllipticalArcTo

test_points: Final = [
    Point(0, 0),
    Point(1, 2),
    Point(-3, 4),
    Point("10.5", -7),
    Point(-8, "3.14"),
    Point("-7.25", "9.0"),
    Point(100, "0.001"),
    Point("-0.5", -2),
    Point(42, 0),
    Point("1e3", "-2.5"),
]

elliptical_arcs: Final = [
    ("M 0 0 A 10 5 0 0 0 50 50", True),
    ("M 10 10 A 20 10 45 0 1 100 0", True),
    ("M -5 20 A 5 5 90 1 0 0 100", True),
    ("M -10 -10 A 15 25 30 1 1 -50 -50", False),
    ("M 3 -3 A 3 8 0 0 1 10 -10", False),
    ("M 0 0 A 25 25 0 0 1 50 0", False),
    ("M -20 -20 A 30 15 60 1 0 40 40", False),
    ("M 5 5 A 12 6 15 0 1 60 30", False),
    ("M -15 10 A 8 12 120 1 1 -40 -30", False),
    ("M 100 -50 A 40 20 30 0 0 150 -10", False),
]


def test_point_eq() -> None:
    a, b = Point(1, 1), Point(2, 2)
    assert a == a
    assert not a == b
    assert not a == 1


def test_point_str_repr() -> None:
    assert str(Point(1, 2)) == "(1, 2)"
    assert str(Point("1.2", "3.14")) == "(1.2, 3.14)"

    assert repr(Point(1, 2)) == "Point(1, 2)"
    assert repr(Point("1.2", "3.14")) == "Point(1.2, 3.14)"


def test_vec2_normalize_zero() -> None:
    z = Point(0, 0).vec2
    assert z.normalized == z


def test_line_length() -> None:
    import sympy as sp

    a, b = Point(1, 1).vec2, Point(2, 2).vec2
    line = Line(a, b)
    assert as_bool(line.length == sp.sqrt(2))
    assert as_bool(line.length == (a - b).length)


def test_line_str_repr() -> None:
    a, b = Point(1, 1).vec2, Point(2, 2).vec2
    line = Line(a, b)
    assert str(line) == f"({a!s}, {b!s})"
    assert repr(line) == f"Line({a!r}, {b!r})"


def test_elliptical_arc_line() -> None:
    with localcontext(prec=25):
        arc = SvgPath("M 0 0 A 0 0 0 0 0 1 1").path[1]
        assert isinstance(arc, EllipticalArcTo)
        arc = arc.to_geometry(n=Precision(24, 8))
        assert isinstance(arc, Line)
        assert arc.p.point == Point(0, 0) and arc.q.point == Point(1, 1)


@pytest.mark.parametrize(
    "p, arc_sym",
    list(itertools.product(test_points, elliptical_arcs)),
)
def test_elliptical_arc_transform(p: Point, arc_sym: tuple[str, bool]) -> None:
    arc, sym = arc_sym
    with localcontext(prec=25):
        arc = SvgPath(arc).path[1]
        assert isinstance(arc, EllipticalArcTo)
        arc = arc.geometry if sym else arc.to_geometry(n=Precision(24, 8))
        assert isinstance(arc, ParametricEllipticalArc)
        q = arc.transform(p.vec2, inverse=False)
        q = arc.transform(q, inverse=True)
        assert p == q.point


def test_lines_disjoint() -> None:
    l0 = Line(Point(1, 1).vec2, Point(2, 2).vec2)
    l1 = Line(Point(2, 1).vec2, Point(3, 2).vec2)
    assert intersect(l0, l1) is None


def test_line_arc_disjoint() -> None:
    import sympy as sp

    R = sp.Rational
    arc = ParametricEllipticalArc(Point(0, 0).vec2, Point(1, 2).vec2, R(0), R(90), R(0))
    line = Line(Point(0, 0).vec2, Point(0, 1).vec2)
    assert intersect(arc, line) is None


def test_arcs_disjoint() -> None:
    import sympy as sp

    R = sp.Rational
    a0 = ParametricEllipticalArc(Point(0, 0).vec2, Point(1, 2).vec2, R(0), R(360), R(0))
    a1 = ParametricEllipticalArc(Point(0, 0).vec2, Point(2, 4).vec2, R(0), R(360), R(0))
    assert intersect(a0, a1) is None
