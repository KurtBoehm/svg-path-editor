# This file is part of https://github.com/KurtBoehm/svg_path_editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any, overload, override

from .math import (
    Boolean,
    Expr,
    Number,
    Precision,
    Symbol,
    are_equal,
    as_bool,
    dec_to_rat,
    evalf,
    ge,
    le,
    rat_to_dec,
    subs,
)

if TYPE_CHECKING:
    import sympy as sp

# ------------------------------------------------------------------------------
# SymPy helpers
# ------------------------------------------------------------------------------


def _rotation_matrix(phi: Expr) -> Mat2:
    r"""
    Rotation matrix for angle :math:`φ` in degrees.

    Uses

    .. math::

        R(φ) = \begin{pmatrix}
            \cos φ & -\sin φ \\
            \sin φ &  \cos φ
        \end{pmatrix}.
    """
    import sympy as sp

    rad: sp.Expr = sp.rad(phi)
    c, s = sp.cos(rad), sp.sin(rad)
    return Mat2(c, -s, s, c)


# ------------------------------------------------------------------------------
# Basic geometric primitives
# ------------------------------------------------------------------------------


class Point:
    """2D point with :class:`decimal.Decimal` coordinates."""

    def __init__(self, x: Number, y: Number) -> None:
        self.x: Decimal = Decimal(x)
        self.y: Decimal = Decimal(y)

    def __iter__(self) -> Iterator[Decimal]:
        """Iterate as ``(x, y)``."""
        yield self.x
        yield self.y

    @override
    def __eq__(self, other: Any) -> bool:
        """
        Compare coordinates for exact equality.

        :return: ``True`` iff ``other`` is a :class:`Point` with equal ``x`` and ``y``.
        """
        if isinstance(other, Point):
            return self.x == other.x and self.y == other.y
        return False

    @property
    def vec2(self) -> Vec2:
        """
        Exact conversion to :class:`Vec2`.

        Coordinates are converted to SymPy rationals via :func:`dec_to_rat`.
        """
        return Vec2.from_point(self)

    @override
    def __str__(self) -> str:
        """Human-readable representation ``(x, y)`` with decimal formatting."""
        return f"({self.x:f}, {self.y:f})"

    @override
    def __repr__(self) -> str:
        """Debug representation ``Point(x, y)`` with decimal formatting."""
        return f"Point({self.x:f}, {self.y:f})"

    @property
    def length(self) -> Decimal:
        """Euclidean norm :math:`‖v‖_2 = \\sqrt{x^2 + y^2}`."""
        return (self.x * self.x + self.y * self.y).sqrt()

    @property
    def normalized(self) -> Point:
        """
        Unit vector :math:`v / ‖v‖_2`.

        The zero vector is returned unchanged.
        """
        length = self.length
        if length == 0:
            return Point(0, 0)
        return self / length

    # ---- vector arithmetic -------------------------------------------------------

    def __neg__(self) -> Point:
        """Unary minus :math:`-v`."""
        return Point(-self.x, -self.y)

    def __add__(self, other: Point) -> Point:
        """Vector addition :math:`v + w`."""
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Point) -> Point:
        """Vector subtraction :math:`v - w`."""
        return Point(self.x - other.x, self.y - other.y)

    def __mul__(self, other: Number) -> Point:
        r"""Scalar multiplication :math:`v ⋅ λ`."""
        other = Decimal(other)
        return Point(self.x * other, self.y * other)

    def __truediv__(self, other: Number) -> Point:
        """Scalar division :math:`v / λ`."""
        other = Decimal(other)
        return Point(self.x / other, self.y / other)


@dataclass
class Vec2:
    """
    2D vector with SymPy coordinates.

    Supports exact arithmetic and simple linear operations.
    """

    x: Expr
    y: Expr

    # ---- construction / conversion -----------------------------------------------

    @staticmethod
    def from_point(p: Point) -> Vec2:
        """
        Construct a :class:`Vec2` from a :class:`Point`.

        Coordinates are converted to SymPy rationals via :func:`dec_to_rat`.
        """
        return Vec2(dec_to_rat(p.x), dec_to_rat(p.y))

    @property
    def point(self) -> Point:
        """
        Convert to numeric :class:`Point`.

        Uses :func:`rat_to_dec` to convert SymPy expressions to
        :class:`~decimal.Decimal`.
        """
        return Point(rat_to_dec(self.x), rat_to_dec(self.y))

    # ---- basic protocol ----------------------------------------------------------

    def __iter__(self) -> Iterator[Expr]:
        """Iterate as ``(x, y)``."""
        yield self.x
        yield self.y

    def subs(self, sub: dict[Symbol, Expr], *, n: Precision | None = None) -> Vec2:
        """
        Substitute symbols in both coordinates.

        :param sub: Substitution dictionary mapping symbols to expressions.
        :param n: Optional precision passed through to :func:`subs`.
        """
        return Vec2(subs(self.x, sub, n=n), subs(self.y, sub, n=n))

    @property
    def swapped(self) -> Vec2:
        """Swap coordinates: :math:`(x, y) ↦ (y, x)`."""
        return Vec2(self.y, self.x)

    def evalf(self, *, n: Precision | None = None) -> Vec2:
        """
        Evaluate coordinates numerically.

        :param n: Optional precision passed to :func:`evalf`.
        """
        return Vec2(evalf(self.x, n=n), evalf(self.y, n=n))

    # ---- elementary geometry -----------------------------------------------------

    @property
    def length(self) -> Expr:
        """Euclidean norm :math:`‖v‖_2 = \\sqrt{x^2 + y^2}`."""
        import sympy as sp

        return sp.sqrt(self.x * self.x + self.y * self.y)

    @property
    def normalized(self) -> Vec2:
        """
        Unit vector :math:`v / ‖v‖_2`.

        The zero vector is returned unchanged.
        """
        import sympy as sp

        length = self.length
        if are_equal(length, 0):
            return Vec2(sp.Integer(0), sp.Integer(0))
        return self / length

    # ---- vector arithmetic -------------------------------------------------------

    def __neg__(self) -> Vec2:
        """Unary minus :math:`-v`."""
        return Vec2(-self.x, -self.y)

    def __add__(self, other: Vec2) -> Vec2:
        """Vector addition :math:`v + w`."""
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2) -> Vec2:
        """Vector subtraction :math:`v - w`."""
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, other: Expr) -> Vec2:
        r"""Scalar multiplication :math:`v ⋅ λ`."""
        return Vec2(self.x * other, self.y * other)

    def __truediv__(self, other: Expr) -> Vec2:
        """Scalar division :math:`v / λ`."""
        return Vec2(self.x / other, self.y / other)


@dataclass
class Mat2:
    r"""
    :math:`2×2` matrix

    .. math::

        M =
        \begin{pmatrix}
            a & b \\
            c & d
        \end{pmatrix}

    acting on :class:`Vec2` by standard matrix-vector multiplication.

    :ivar a: Entry :math:`a_{11}`.
    :ivar b: Entry :math:`a_{12}`.
    :ivar c: Entry :math:`a_{21}`.
    :ivar d: Entry :math:`a_{22}`.
    """

    a: Expr
    b: Expr
    c: Expr
    d: Expr

    def __matmul__(self, v: Vec2) -> Vec2:
        """
        Matrix-vector product ``M @ v``.

        .. math::

            (x', y') = (a x + b y, \\; c x + d y).
        """
        return Vec2(self.a * v.x + self.b * v.y, self.c * v.x + self.d * v.y)


# ------------------------------------------------------------------------------
# Polygon utility
# ------------------------------------------------------------------------------


def polygon_signed_area(poly: Sequence[Vec2]) -> Expr:
    r"""
    Signed area of a simple polygon.

    Uses the shoelace formula

    .. math::

        A = \frac12 \sum_i (x_i y_{i+1} - x_{i+1} y_i),

    with positive area for counter-clockwise vertex order.

    :param poly: Vertex sequence, implicitly closed.
    """
    import sympy as sp

    area: sp.Expr = sp.Integer(0)
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return area / 2


# ------------------------------------------------------------------------------
# Line segment
# ------------------------------------------------------------------------------


class Line:
    r"""
    Line segment from :attr:`p` to :attr:`q`.

    Parametric form

    .. math::

        L(t) = p + (q - p)\,t, \quad t \in \mathbb{R}.
    """

    def __init__(self, p: Vec2, q: Vec2) -> None:
        self.p: Vec2 = p
        self.q: Vec2 = q

    @property
    def delta(self) -> Vec2:
        """Direction vector :math:`q - p` of the segment."""
        return Vec2(x=self.q.x - self.p.x, y=self.q.y - self.p.y)

    @property
    def length(self) -> Expr:
        """Euclidean segment length :math:`‖q - p‖_2`."""
        return self.delta.length

    def inward_normal(self, is_ccw: bool) -> Vec2:
        r"""
        Unit inward normal.

        For a CCW-oriented boundary, the inward normal is obtained by rotating
        the edge direction :math:`(Δx, Δy)` 90° clockwise; for a CW boundary,
        by rotating 90° counter-clockwise:

        .. math::

            n = \begin{cases}
                (Δy, -Δx) & \text{if CCW} \\
                (-Δy, Δx) & \text{if CW}
            \end{cases}

        The resulting vector is then normalized.

        :param is_ccw: ``True`` if the enclosing polygon is CCW oriented.
        """
        dx, dy = self.delta
        n = Vec2(dy, -dx) if is_ccw else Vec2(-dy, dx)
        return n.normalized

    def offset(self, *, d: Expr, is_ccw: bool, n: Precision | None = None) -> Line:
        r"""
        Offset the line along its inward normal by distance ``d``.

        Both endpoints are translated by :math:`d ⋅ n_{\mathit{in}}`.

        :param d: Signed offset distance.
        :param is_ccw: Orientation of the surrounding boundary.
        :param n: Optional precision used in :meth:`Vec2.evalf`.
        """
        normal = self.inward_normal(is_ccw=is_ccw) * d
        normal = normal.evalf(n=n)
        return Line(self.p + normal, self.q + normal)

    def __call__(self, t: Expr) -> Vec2:
        r"""
        Evaluate the parametric line :math:`L(t) = p + (q - p)\,t`.
        """
        return self.p + (self.q - self.p) * t

    @override
    def __str__(self) -> str:
        """Human-readable representation ``(p, q)``."""
        return f"({self.p}, {self.q})"

    @override
    def __repr__(self) -> str:
        """Debug representation ``Line(p, q)``."""
        return f"Line({self.p!r}, {self.q!r})"


# ------------------------------------------------------------------------------
# Elliptical arc
# ------------------------------------------------------------------------------


@dataclass
class ParametricEllipticalArc:
    r"""
    Elliptical arc in parametric form.

    The underlying full ellipse is

    .. math::

        E(θ) &= R(φ) ⋅
        \begin{pmatrix}
            r_x \cos θ \\
            r_y \sin θ
        \end{pmatrix}
        +
        \begin{pmatrix}
            c_x \\
            c_y
        \end{pmatrix}

    where :math:`θ` and :math:`φ` are in degrees and :math:`(c_x, c_y)` is the center.

    This arc covers the interval :math:`[θ_0, θ_0 + Δθ]` (mod 360°).

    :ivar c: Center :math:`(c_x, c_y)`.
    :ivar r: Radii :math:`(r_x, r_y)`.
    :ivar theta0: Start angle :math:`θ_0` in degrees.
    :ivar dtheta: Sweep :math:`Δθ` in degrees (signed).
    :ivar phi: Rotation angle :math:`φ` in degrees.
    """

    c: Vec2
    r: Vec2
    theta0: Expr
    dtheta: Expr
    phi: Expr

    # ---- conversion --------------------------------------------------------------

    @property
    def theta1(self) -> Expr:
        """
        End angle of the arc.

        :return: :math:`θ_1 = θ_0 + Δθ` in degrees.
        """
        return self.theta0 + self.dtheta

    def locally_convex(self, *, is_ccw: bool) -> bool:
        """
        Test if the arc is locally convex with respect to the boundary orientation.

        :return: ``True`` iff the interior lies on the convex side of the arc
                 for a boundary with orientation ``is_ccw``.
        """
        return as_bool(self.dtheta < 0) == is_ccw

    def offset(
        self,
        *,
        d: Expr,
        is_ccw: bool,
        n: Precision | None = None,
    ) -> ParametricEllipticalArc:
        """
        Offset the arc by changing its radii.

        * :math:`d > 0`: move inward
        * :math:`d < 0`: move outward

        “Inward” is defined with respect to the polygon orientation:
        for a CCW boundary, the interior is to the *left* of the path,
        for a CW boundary to the *right*.

        :param d: Signed offset distance applied to both radii.
        :param is_ccw: Orientation of the surrounding boundary.
        :param n: Unused; kept for API symmetry with :meth:`Line.offset`.
        """
        radial_delta = -d if self.locally_convex(is_ccw=is_ccw) else d
        return ParametricEllipticalArc(
            c=self.c,
            r=Vec2(self.r.x + radial_delta, self.r.y + radial_delta),
            theta0=self.theta0,
            dtheta=self.dtheta,
            phi=self.phi,
        )

    # ---- angle range condition ---------------------------------------------------

    @overload
    def angle_condition(
        self, theta: Symbol, *, n: Precision | None = None
    ) -> Boolean: ...
    @overload
    def angle_condition(
        self, theta: Expr, *, n: Precision | None = None
    ) -> Boolean: ...

    def angle_condition(self, theta: Expr, *, n: Precision | None = None) -> Boolean:
        """
        Test whether ``theta`` (in degrees) lies on this arc, modulo 360°.

        Works for positive and negative :math:`Δθ` and wrap-around intervals.

        :param n: Optional precision passed to :func:`evalf`, :func:`ge`,
                  and :func:`le`.
        """
        import sympy as sp

        t0, t1 = evalf(self.theta0, n=n) % 360, evalf(self.theta1, n=n) % 360
        dtheta = evalf(self.dtheta, n=n)
        theta = evalf(theta, n=n) % 360

        lo, hi = (t0, t1) if as_bool(ge(dtheta, sp.S.Zero, n=n)) else (t1, t0)
        if as_bool(le(lo, hi, n=n)):
            return sp.And(le(lo, theta, n=n), le(theta, hi, n=n))
        return sp.Or(le(lo, theta, n=n), le(theta, hi, n=n))

    # ---- evaluation and differential geometry -----------------------------------

    def point_tangent(
        self,
        theta: Expr,
        n: Precision | None = None,
    ) -> tuple[Vec2, Vec2]:
        r"""
        Point and tangent at parameter ``theta`` (in degrees).

        Returns :math:`(p(θ), ±p'(θ))`, where the derivative is w.r.t. :math:`θ`
        in degrees and not normalized. The sign of the derivative is chosen so that
        the tangent at :math:`θ_0` points along the arc and that at :math:`θ_1`
        points away from the arc.

        :param n: Optional precision used in :func:`evalf` and sign checks.
        """
        import sympy as sp

        rphi = sp.rad(self.phi)
        cos_phi, sin_phi = sp.cos(rphi), sp.sin(rphi)
        rtheta = sp.rad(theta)
        cos_theta, sin_theta = sp.cos(rtheta), sp.sin(rtheta)
        c, r = self.c, self.r

        # Position
        x = c.x + r.x * cos_theta * cos_phi - r.y * sin_theta * sin_phi
        y = c.y + r.x * cos_theta * sin_phi + r.y * sin_theta * cos_phi

        # Derivative w.r.t. θ (chain rule via d/dθ cos(rad(θ)), sin(rad(θ)))
        dxdt = -r.x * sin_theta * cos_phi - r.y * cos_theta * sin_phi
        dydt = -r.x * sin_theta * sin_phi + r.y * cos_theta * cos_phi

        if as_bool(evalf(self.dtheta, n=n) < 0):
            dxdt, dydt = -dxdt, -dydt

        return Vec2(x, y).evalf(n=n), Vec2(dxdt, dydt).evalf(n=n)

    # ---- transform / implicit form -----------------------------------------------

    def transform(self, p: Vec2, *, inverse: bool = False) -> Vec2:
        r"""
        Affine map between unit circle and this ellipse.

        * ``inverse=False``: :math:`(u, v) \mapsto (x, y)` on the ellipse.
        * ``inverse=True``: :math:`(x, y) \mapsto (u, v)` on the unit circle.

        The forward mapping is

        .. math::

            (x, y) = c + R(φ)\,\mathrm{diag}(r_x, r_y)\,(u, v),

        where all angles are in degrees.

        :param p: Point to transform, either on the unit circle (forward)
                  or on the ellipse (inverse).
        :param inverse: Select direction of the mapping.
        """
        if inverse:
            # subtract center
            xy = p - self.c
            # undo rotation
            xy = _rotation_matrix(-self.phi) @ xy
            # undo anisotropic scaling
            return Vec2(xy.x / self.r.x, xy.y / self.r.y)

        # apply scaling, rotation, then translation
        xy = Vec2(p.x * self.r.x, p.y * self.r.y)
        xy = _rotation_matrix(self.phi) @ xy
        return xy + self.c

    def implicit(self, x: Expr, y: Expr) -> Expr:
        r"""
        Implicit ellipse equation at ``(x, y)``.

        Returns

        .. math::

            F(x, y) = u^2 + v^2 - 1,

        where :math:`(u, v)` is the image of :math:`(x, y)` under the inverse transform
        to the unit circle.
        """
        uv = self.transform(Vec2(x, y), inverse=True)
        return uv.x**2 + uv.y**2 - 1
