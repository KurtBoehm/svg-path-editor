# This file is part of https://github.com/KurtBoehm/svg_path_editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Callable, Literal, Protocol, Self, overload

from .geometry import Line, ParametricEllipticalArc, Vec2
from .math import (
    Boolean,
    Precision,
    are_equal,
    as_bool,
    dec_to_rat,
    evalf,
    expand,
    ge,
    is_zero,
    le,
    polynomial_roots,
    resultant,
    subs,
)

if TYPE_CHECKING:
    import sympy as sp


type Expr = "sp.Expr"
type Symbol = "sp.Symbol"
type AnyBoolean = bool | Boolean


# ------------------------------------------------------------------------------
# Intersection protocol and dispatcher
# ------------------------------------------------------------------------------


class Intersection(Protocol):
    """
    Common protocol for intersection results.

    :ivar intersection: The intersection point.
    """

    intersection: Vec2


@overload
def intersect(
    a: Line, b: Line, *, d: Decimal | None = None, n: Precision | None = None
) -> LineIntersection | LineCoincidentIntersection | LineAroundIntersection | None: ...
@overload
def intersect(
    a: Line,
    b: ParametricEllipticalArc,
    *,
    d: Decimal | None = None,
    n: Precision | None = None,
) -> (
    LineArcIntersection | LineArcExtIntersection | LineArcAroundIntersection | None
): ...
@overload
def intersect(
    a: ParametricEllipticalArc,
    b: Line,
    *,
    d: Decimal | None = None,
    n: Precision | None = None,
) -> (
    LineArcIntersection | LineArcExtIntersection | LineArcAroundIntersection | None
): ...
@overload
def intersect(
    a: ParametricEllipticalArc,
    b: ParametricEllipticalArc,
    *,
    d: Decimal | None = None,
    n: Precision | None = None,
) -> ArcArcIntersection | ArcArcExtIntersection | ArcArcAroundIntersection | None: ...


def intersect(
    a: Line | ParametricEllipticalArc,
    b: Line | ParametricEllipticalArc,
    *,
    d: Decimal | None = None,
    n: Precision | None = None,
) -> Intersection | None:
    """
    Public intersection helper.

    Dispatches to the appropriate specialized routine using structural pattern
    matching on the argument types.

    :param a: First primitive (line or arc).
    :param b: Second primitive (line or arc).
    :param d: Optional offset distance used only in “around” fallbacks.
    :param n: Optional precision for SymPy evaluations.
    :return: An intersection record or ``None`` if nothing applicable is found.
    """
    match (a, b):
        case (Line() as l0, Line() as l1):
            return intersect_lines(l0, l1, d=d, n=n)
        case (Line() as lin, ParametricEllipticalArc() as arc):
            return intersect_line_arc(lin, arc, line_before_arc=True, d=d, n=n)
        case (ParametricEllipticalArc() as arc, Line() as lin):
            return intersect_line_arc(lin, arc, line_before_arc=False, d=d, n=n)
        case (ParametricEllipticalArc() as arc0, ParametricEllipticalArc() as arc1):
            return intersect_arc_arc(arc0, arc1, d=d, n=n)


# ------------------------------------------------------------------------------
# Line-line intersection
# ------------------------------------------------------------------------------


@dataclass
class LineIntersection:
    r"""
    Intersection of two parameterized lines.

    Parameters :attr:`t` and :attr:`u` satisfy

    .. math::

        p_0 + (q_0 - p_0)\,t = p_1 + (q_1 - p_1)\,u.

    :ivar t: Parameter on the first line.
    :ivar u: Parameter on the second line.
    :ivar intersection: Common point.
    """

    t: Expr
    u: Expr
    intersection: Vec2

    @property
    def swapped(self) -> Self:
        """
        Swap coordinates of the intersection point.
        """
        return type(self)(t=self.t, u=self.u, intersection=self.intersection.swapped)


@dataclass
class LineCoincidentIntersection:
    """
    Degenerate “intersection” of coincident parametric lines.

    Used when two lines lie on top of each other.
    A single representative point is stored.

    :ivar t: Chosen parameter on the first line.
    :ivar u: Corresponding parameter on the second line.
    :ivar intersection: Common endpoint on the coincident line.
    """

    t: Expr
    u: Expr
    intersection: Vec2

    @property
    def swapped(self) -> Self:
        """
        Swap coordinates of the intersection point.
        """
        return type(self)(t=self.t, u=self.u, intersection=self.intersection.swapped)


@dataclass
class LineAroundIntersection:
    """
    Fallback “around” configuration for two line segments.

    The segments neither meet nor their endpoint-endpoint connector lies on
    both segments. This synthesizes a connection via an intermediate point.

    :ivar intersection: Midpoint of the constructed connection.
    :ivar ante_intersection: End of the first segment.
    :ivar post_intersection: Start of the second segment.
    :ivar ante_extended: Offset from :attr:`ante_intersection` along the first line.
    :ivar post_extended: Offset from :attr:`post_intersection` along the second line.
    """

    intersection: Vec2
    ante_intersection: Vec2
    post_intersection: Vec2
    ante_extended: Vec2
    post_extended: Vec2


def intersect_lines_raw(
    l0: Line,
    l1: Line,
    *,
    n: Precision | None = None,
) -> LineIntersection | LineCoincidentIntersection | None:
    """
    Raw line-line intersection without segment clipping.

    Solves for parameters :math:`t, u` such that the two parametric lines meet.
    Returns ``None`` when they are parallel and distinct.

    Degenerate collinear overlap is represented by picking the end of :math:`l_0`.

    :param l0: First parametric line (infinite).
    :param l1: Second parametric line (infinite).
    :param n: Optional precision for intermediate evaluation.
    """
    import sympy as sp

    def intersect_non_vertical(
        l0: Line,
        l1: Line,
    ) -> LineIntersection | LineCoincidentIntersection | None:
        t = sp.Symbol("t", real=True)
        # Express t(s) from x-coordinates, then enforce y-coordinates equality
        u = ((l0.p.x - l1.p.x) + l0.delta.x * t) / l1.delta.x
        poly = l0(t).y - l1(u).y

        poly0, poly1 = subs(poly, {t: sp.S.Zero}, n=n), subs(poly, {t: sp.S.One}, n=n)
        slope = poly1 - poly0
        if are_equal(slope, 0):
            # Parallel (possibly coincident)
            if are_equal(poly, 0):
                tv = sp.Integer(1)
                uv = subs(u, {t: tv}, n=n)
                return LineCoincidentIntersection(tv, uv, l0.q)
            return None

        tv = -poly0 / slope
        uv = subs(u, {t: tv}, n=n)
        return LineIntersection(tv, uv, l0(tv))

    if not is_zero(l1.delta.x, n=n):
        return intersect_non_vertical(l0, l1)

    # Avoid division by zero for vertical l1 by swapping x,y
    i = intersect_non_vertical(
        Line(l0.p.swapped, l0.q.swapped),
        Line(l1.p.swapped, l1.q.swapped),
    )
    return i.swapped if i is not None else None


def intersect_lines(
    l0: Line,
    l1: Line,
    *,
    d: Decimal | None = None,
    n: Precision | None = None,
) -> LineIntersection | LineCoincidentIntersection | LineAroundIntersection | None:
    """
    Segment-segment intersection.

    Returns the line-line intersection if it lies within both segments,
    i.e. :math:`t, u ∈ [0, 1]`.

    If no intersection exists and ``d`` is given, returns a
    :class:`LineAroundIntersection` constructed from the closest endpoints.

    :param l0: First line segment.
    :param l1: Second line segment.
    :param d: Optional offset distance for constructing an “around” connector.
    :param n: Optional precision for :func:`intersect_lines_raw`.
    """
    import sympy as sp

    i = intersect_lines_raw(l0, l1, n=n)
    if i is not None and as_bool(i.t >= 0) and as_bool(i.u <= 1):
        return i

    # No proper segment intersection: build “around” configuration if requested.
    if not d:
        return None

    δ = dec_to_rat(d)

    # Choose “ante” / “post” points as endpoints of the two segments.
    # Here we simply use l0.q (end of first) and l1.p (start of second)
    # and offset them by δ along the segment directions.
    d0, d1 = l0.delta.normalized, l1.delta.normalized
    ante_extended, post_extended = l0.q + d0 * δ, l1.p - d1 * δ

    return LineAroundIntersection(
        intersection=(ante_extended + post_extended) * sp.Rational(1, 2),
        ante_intersection=l0.q,
        post_intersection=l1.p,
        ante_extended=ante_extended,
        post_extended=post_extended,
    )


# ------------------------------------------------------------------------------
# Line-arc intersection
# ------------------------------------------------------------------------------


@dataclass
class LineArcIntersection:
    """
    Intersection of a line with the interior of an elliptical arc.

    :attr:`t` is the line parameter, :attr:`theta` is the ellipse parameter in degrees.

    :ivar t: Parameter along the line segment.
    :ivar theta: Angle parameter on the arc in degrees.
    :ivar intersection: Common point.
    """

    t: Expr
    theta: Expr
    intersection: Vec2


@dataclass
class LineArcExtIntersection:
    r"""
    Intersection of a line with an arc’s tangent half-line.

    Covers the half-lines defined by tangents at the arc endpoints:

    * ``ext="ante"``: tangent at start angle, extended backwards.
    * ``ext="post"``: tangent at end angle, extended forwards.

    :ivar t: Parameter along the line.
    :ivar u: Parameter along the tangent half-line.
    :ivar intersection: Common point of the line and tangent.
    :ivar post_intersection: Endpoint of the arc used for the tangent.
    :ivar theta: Angle of the tangent point in degrees.
    :ivar ext: Which endpoint tangent is used (``"ante"`` or ``"post"``).
    """

    t: Expr
    u: Expr
    intersection: Vec2
    post_intersection: Vec2
    theta: Expr
    ext: Literal["ante", "post"]


@dataclass
class LineArcAroundIntersection:
    """
    Fallback “around” configuration for a line and an arc.

    Used when the line segment does not intersect the arc or its endpoint
    tangent half-lines. Synthesizes a connection via offset points.

    :ivar intersection: Midpoint of the constructed connection.
    :ivar ante_intersection: End of the line or arc reached first.
    :ivar post_intersection: Start of the following primitive.
    :ivar ante_extended: Offset point from :attr:`ante_intersection`.
    :ivar post_extended: Offset point from :attr:`post_intersection`.
    """

    intersection: Vec2
    ante_intersection: Vec2
    post_intersection: Vec2
    ante_extended: Vec2
    post_extended: Vec2


def intersect_line_arc(
    lin: Line,
    arc: ParametricEllipticalArc,
    *,
    line_before_arc: bool,
    d: Decimal | None,
    n: Precision | None,
) -> LineArcIntersection | LineArcExtIntersection | LineArcAroundIntersection | None:
    """
    Intersect a line segment with an elliptical arc and its tangents.

    1. Intersect the line with the full ellipse in ellipse-local coordinates.
    2. Filter hits whose line-parameter and arc-angle lie on the segment/arc.
    3. If none, intersect the appropriate endpoint tangent half-line.
    4. If still none and ``d`` is given, synthesize an “around” configuration.

    The first valid solution encountered is returned.

    :param lin: Line segment.
    :param arc: Elliptical arc.
    :param line_before_arc: If ``True``, the line precedes the arc in path order.
    :param d: Optional offset distance for an “around” configuration.
    :param n: Optional precision for internal SymPy calls.
    """
    import sympy as sp

    t = sp.Symbol("t", real=True)

    # Tangent at arc start, backward half-line
    if line_before_arc:
        p0, t0 = arc.point_tangent(arc.theta0, n=n)
        ante_line = Line(p0, p0 - t0)
        lint0 = intersect_lines_raw(lin, ante_line, n=n)
        if (
            isinstance(lint0, LineIntersection)
            and as_bool(lint0.t >= 0)
            and as_bool(lint0.u > 0)
        ):
            return LineArcExtIntersection(
                t=lint0.t,
                u=lint0.u,
                intersection=lint0.intersection,
                post_intersection=p0,
                theta=arc.theta0,
                ext="ante",
            )

    # Tangent at arc end, forward half-line
    if not line_before_arc:
        p1, t1 = arc.point_tangent(arc.theta1, n=n)
        post_line = Line(p1, p1 + t1)
        lint1 = intersect_lines_raw(lin, post_line, n=n)
        if (
            isinstance(lint1, LineIntersection)
            and as_bool(lint1.t <= 1)
            and as_bool(lint1.u > 0)
        ):
            return LineArcExtIntersection(
                t=lint1.t,
                u=lint1.u,
                intersection=lint1.intersection,
                post_intersection=p1,
                theta=arc.theta1,
                ext="post",
            )

    # Transform the line into unit-circle coordinates
    lu = arc.transform(lin(t), inverse=True).evalf(n=n)

    # Circle equation: u(t)^2 + v(t)^2 = 1
    sols_t = polynomial_roots(lu.x * lu.x + lu.y * lu.y - 1, t, n=n)

    def compute_angle(tv: sp.Expr) -> sp.Expr:
        """
        Convert a line parameter to an angular position (in degrees) on the unit circle.
        """
        p = lu.subs({t: tv}, n=n)
        return sp.deg(sp.atan2(p.y, p.x))

    line_condition: Callable[[sp.Expr], Boolean]
    line_condition = (
        (lambda τ: ge(τ, sp.S.Zero, n=n))
        if line_before_arc
        else (lambda τ: le(τ, sp.S.One, n=n))
    )

    # Interior intersection with the arc
    for tv in sols_t.keys():
        thetav = compute_angle(tv)
        if line_condition(tv) and as_bool(arc.angle_condition(thetav, n=n)):
            return LineArcIntersection(tv, thetav, lin(tv))

    # No interior or extension intersection: construct “around” configuration
    if not d:
        return None

    δ = dec_to_rat(d)

    # For "ante" we connect the end of the line to the start of the arc,
    # for "post" we connect the start of the line to the end of the arc.
    if line_before_arc:
        # line then arc
        ante_intersection = lin.q
        post_intersection, d_arc = arc.point_tangent(arc.theta0, n=n)
        d_line, d_arc_norm = lin.delta.normalized, d_arc.normalized
    else:
        # arc then line
        ante_intersection, d_arc = arc.point_tangent(arc.theta1, n=n)
        post_intersection = lin.p
        d_line, d_arc_norm = -lin.delta.normalized, -d_arc.normalized

    ante_extended = ante_intersection + d_line * δ
    post_extended = post_intersection - d_arc_norm * δ

    intersection = (ante_extended + post_extended) * sp.Rational(1, 2)

    return LineArcAroundIntersection(
        intersection=intersection,
        ante_intersection=ante_intersection,
        post_intersection=post_intersection,
        ante_extended=ante_extended,
        post_extended=post_extended,
    )


# ------------------------------------------------------------------------------
# Arc-arc intersection
# ------------------------------------------------------------------------------


@dataclass
class ArcArcIntersection:
    """
    Intersection of two elliptical arcs.

    :attr:`theta0` and :attr:`theta1` are the ellipse parameters at the common point
    on the first and second arc, respectively (in degrees).

    :ivar theta0: Angle on the first arc in degrees.
    :ivar theta1: Angle on the second arc in degrees.
    :ivar intersection: Common point.
    """

    theta0: Expr
    theta1: Expr
    intersection: Vec2


@dataclass
class ArcArcExtIntersection:
    """
    Intersection of the tangent half-lines of two arcs.

    :attr:`t` and :attr:`u` are the parameters along those half-lines.

    :ivar t: Parameter along the tangent from the first arc.
    :ivar u: Parameter along the tangent from the second arc.
    :ivar intersection: Intersection of the two tangent half-lines.
    :ivar ante_intersection: Tangent point on the first arc.
    :ivar post_intersection: Tangent point on the second arc.
    """

    t: Expr
    u: Expr
    intersection: Vec2
    ante_intersection: Vec2
    post_intersection: Vec2


@dataclass
class ArcArcAroundIntersection:
    """
    Fallback “around” configuration when arcs neither meet nor converge.

    Used to synthesize a connection via offset tangent points.

    :ivar intersection: Midpoint of the constructed connection.
    :ivar ante_intersection: End of the first arc.
    :ivar post_intersection: Start of the second arc.
    :ivar ante_extended: Offset from :attr:`ante_intersection`.
    :ivar post_extended: Offset from :attr:`post_intersection`.
    """

    intersection: Vec2
    ante_intersection: Vec2
    post_intersection: Vec2
    ante_extended: Vec2
    post_extended: Vec2


def intersect_arc_arc(
    arc0: ParametricEllipticalArc,
    arc1: ParametricEllipticalArc,
    *,
    d: Decimal | None = None,
    n: Precision | None = None,
) -> ArcArcIntersection | ArcArcExtIntersection | ArcArcAroundIntersection | None:
    """
    Intersect two elliptical arcs.

    1. Compute the resultant of their implicit equations to eliminate :math:`y`.
    2. Solve for candidate :math:`x` and refine to :math:`(x, y)` intersection points.
    3. Map to angular parameters on both arcs and check angle ranges.
    4. If no interior intersection exists, intersect the endpoint tangents.
    5. As a last resort, construct an “around” configuration using offsets.

    :param arc0: First elliptical arc.
    :param arc1: Second elliptical arc.
    :param d: Optional offset distance for an “around” configuration.
    :param n: Optional precision for internal SymPy roots.
    :return: Any of the arc-arc intersection variants, or ``None``.
    """
    import sympy as sp

    x, y = sp.Symbol("x", real=True), sp.Symbol("y", real=True)

    imp0, imp1 = arc0.implicit(x, y), arc1.implicit(x, y)
    res = expand(resultant(imp0, imp1, y, n=n))

    # Resultant is constant: either coincident or disjoint.
    if not res.free_symbols:
        if is_zero(res, n=n):
            # Arbitrarily connect end of arc0 to start of arc1
            intersection, _ = arc0.point_tangent(arc0.theta1, n=n)
            return ArcArcIntersection(arc0.theta1, arc1.theta0, intersection)
        return None

    # Try interior intersections
    for xv in polynomial_roots(res, x, n=n).keys():
        yimp0, yimp1 = subs(imp0, {x: xv}, n=n), subs(imp1, {x: xv}, n=n)
        for yv in polynomial_roots(yimp0, y, n=n).keys():
            if not is_zero(subs(yimp1, {y: yv}), n=n):
                continue
            intersection = Vec2(xv, yv)
            u0 = arc0.transform(intersection, inverse=True).evalf(n=n)
            u1 = arc1.transform(intersection, inverse=True).evalf(n=n)
            theta0 = evalf(sp.deg(sp.atan2(u0.y, u0.x)), n=n)
            theta1 = evalf(sp.deg(sp.atan2(u1.y, u1.x)), n=n)
            assert isinstance(theta0, sp.Expr) and isinstance(theta1, sp.Expr)
            c0 = arc0.angle_condition(theta0, n=n)
            c1 = arc1.angle_condition(theta1, n=n)
            if as_bool(c0) and as_bool(c1):
                return ArcArcIntersection(theta0, theta1, intersection)

    # No interior intersection: intersect the tangent half-lines
    p0, d0 = arc0.point_tangent(arc0.theta1, n=n)
    p1, d1 = arc1.point_tangent(arc1.theta0, n=n)
    tan0, tan1 = Line(p0, p0 + d0), Line(p1, p1 - d1)
    ext_intersection = intersect_lines_raw(tan0, tan1, n=n)
    if (
        ext_intersection
        and as_bool(ext_intersection.t > 0)
        and as_bool(ext_intersection.u > 0)
    ):
        return ArcArcExtIntersection(
            t=ext_intersection.t,
            u=ext_intersection.u,
            intersection=ext_intersection.intersection,
            ante_intersection=p0,
            post_intersection=p1,
        )

    # No interior or extension intersection: construct "around" configuration
    if d:
        δ = dec_to_rat(d)
        ext0, ext1 = p0 + d0.normalized * δ, p1 - d1.normalized * δ
        return ArcArcAroundIntersection(
            intersection=(ext0 + ext1) * sp.Rational(1, 2),
            ante_intersection=p0,
            post_intersection=p1,
            ante_extended=ext0,
            post_extended=ext1,
        )
