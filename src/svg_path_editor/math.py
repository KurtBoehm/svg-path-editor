# This file is part of https://github.com/KurtBoehm/svg-path-editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    import sympy as sp

Number = Decimal | int | float | str

type Symbol = "sp.Symbol"
type Expr = "sp.Expr"
type Poly = "sp.Poly"
type Boolean = "sp.logic.boolalg.Boolean"


@dataclass(frozen=True)
class Precision:
    """
    Control numerical precision for mixed symbolic/numeric operations.

    ``baseline`` defines the primary target precision, while ``additional``
    can be used to carry extra guard digits during intermediate computations.

    :ivar baseline: Baseline number of significant digits.
    :ivar additional: Additional guard digits to be used internally.
    """

    baseline: int
    additional: int

    @property
    def full(self) -> int:
        """
        Full number of significant digits to use.

        :return: ``baseline + additional``.
        """
        return self.baseline + self.additional


def canonical_decimal(x: Decimal) -> Decimal:
    """
    Normalize a :class:`~decimal.Decimal` to a canonical form.

    :return: ``Decimal(0)`` for any zero value, otherwise ``x.normalize()``.
    """
    return Decimal(0) if x == 0 else x.normalize()


def dec_to_rat(x: Decimal) -> Expr:
    """
    Convert a :class:`~decimal.Decimal` to a SymPy :class:`sympy.Rational`.

    The conversion is exact with respect to the decimal representation:
    the :class:`~decimal.Decimal` is first converted to a string and then
    passed to :class:`sympy.Rational`.
    """
    import sympy as sp

    return sp.Rational(str(x))


def rat_to_dec(x: Expr) -> Decimal:
    """
    Convert a SymPy expression to :class:`~decimal.Decimal` with current precision.

    The expression is evaluated numerically using :meth:`sympy.Expr.evalf`
    with ``n = getcontext().prec`` and then converted to :class:`~decimal.Decimal`.
    The result is normalized via :func:`canonical_decimal`.
    """
    return canonical_decimal(Decimal(str(x.evalf(n=getcontext().prec))))


def as_bool(r: Boolean) -> bool:
    """
    Coerce a SymPy Boolean to builtin :class:`bool`.

    :raises ValueError: If ``r`` cannot be simplified to a definite Boolean.
    """
    import sympy as sp

    r = sp.simplify(r)
    if isinstance(r, sp.logic.boolalg.BooleanTrue):
        return True
    if isinstance(r, sp.logic.boolalg.BooleanFalse):
        return False
    raise ValueError(f"Cannot be evaluated to a Boolean: {r}")


def are_equal(a: Expr | int, b: Expr | int) -> bool:
    """
    Test symbolic equality :math:`a = b` using SymPy.

    :return: ``True`` if SymPy proves ``a`` and ``b`` equal, otherwise ``False``.
    :raises ValueError: If the equality cannot be decided symbolically.
    """
    import sympy as sp

    eq = sp.Eq(a, b)
    assert isinstance(eq, sp.logic.boolalg.Boolean)
    return as_bool(eq)


def eq(a: Expr, b: Expr, *, n: Precision | None = None) -> Boolean:
    """
    Construct an (optionally relaxed) equality constraint :math:`a = b`.

    If ``n`` is ``None``, an exact symbolic equality :class:`sympy.Eq` is returned.
    Otherwise a relaxed inequality :math:`|a - b| < 10^{-\\texttt{baseline}}`
    is constructed.
    """
    import sympy as sp

    return (
        sp.LessThan(sp.Abs(a - b), sp.Rational(1, 10**n.baseline))
        if n is not None
        else sp.Eq(a, b)
    )


def le(a: Expr, b: Expr, *, n: Precision | None = None) -> Boolean:
    """
    Construct an (optionally relaxed) inequality :math:`a ≤ b`.

    If ``n`` is ``None``, returns :class:`sympy.LessThan(a, b)`.
    Otherwise compares ``a`` with :math:`b + 10^{-\\texttt{baseline}}`.
    """
    import sympy as sp

    b = b + sp.Rational(1, 10**n.baseline) if n is not None else b
    return sp.LessThan(a, b)


def ge(a: Expr, b: Expr, *, n: Precision | None = None) -> Boolean:
    """
    Construct an (optionally relaxed) inequality :math:`a \\ge b`.

    See :func:`le` for details.
    """
    return le(b, a, n=n)


def lt(a: Expr, b: Expr, *, n: Precision | None = None) -> Boolean:
    """
    Construct an (optionally relaxed) strict inequality :math:`a < b`.

    If ``n`` is ``None``, returns :class:`sympy.StrictLessThan(a, b)`.
    Otherwise compares ``a`` with :math:`b + 10^{-\\texttt{baseline}}`.
    """
    import sympy as sp

    b = b + sp.Rational(1, 10**n.baseline) if n is not None else b
    return sp.StrictLessThan(a, b)


def gt(a: Expr, b: Expr, *, n: Precision | None = None) -> Boolean:
    """
    Construct an (optionally relaxed) strict inequality :math:`a > b`.

    See :func:`lt` for details.
    """
    return lt(b, a, n=n)


def is_zero(expr: Expr, *, n: Precision | None = None) -> bool:
    """
    Test whether an expression is zero.

    If ``n`` is ``None``, use exact symbolic comparison ``expr == 0``.
    Otherwise, evaluate numerically to ``n.full`` significant digits and
    test :math:`|\\mathtt{expr}| ≤ 10^{-\\texttt{baseline}}`.

    :return: ``True`` if ``expr`` is considered zero, otherwise ``False``.
    :raises ValueError: If the exact symbolic comparison cannot be decided.
    """
    import sympy as sp

    if n is None:
        eq = sp.Eq(expr, 0)
        assert isinstance(eq, sp.logic.boolalg.Boolean)
        return as_bool(eq)
    return abs(expr.evalf(n=n.full)) <= 10 ** (-n.baseline)


def subs(
    expr: Expr,
    subs: dict[Symbol, Expr],
    *,
    n: Precision | None = None,
) -> Expr:
    """
    Substitute symbols in an expression, optionally with numeric evaluation.

    If the expression contains floating-point numbers and ``n`` is not ``None``,
    :meth:`sympy.Expr.evalf` is used with the given precision and substitutions.
    Otherwise, standard symbolic substitution via :meth:`sympy.Expr.subs` is performed.

    :param expr: Expression in which to perform substitutions.
    :param subs: Mapping from symbols to replacement expressions.
    :param n: Optional precision for numerical evaluation.
    """
    import sympy as sp

    if expr.atoms(sp.Float) and n is not None:
        bsubs = cast(dict[sp.Basic, sp.Basic | float] | None, subs)
        return expr.evalf(n=n.full, subs=bsubs)
    return expr.subs(subs.items())


def evalf(expr: Expr, *, n: Precision | None) -> Expr:
    """
    Optionally evaluate an expression numerically.

    If ``n`` is ``None``, return ``expr`` unchanged.
    Otherwise, return ``expr.evalf(n=n.full)``; if the imaginary part is at most
    :math:`10^{-\\texttt{baseline}}`, the real part is returned.
    """
    import sympy as sp

    if n is None:
        return expr
    res = expr.evalf(n=n.full)
    return sp.re(res) if sp.im(res) <= 10 ** (-n.baseline) else res


def _as_real_poly(poly: Expr, x: Symbol) -> Poly | None:
    """
    Try to interpret ``poly`` as a univariate real polynomial in ``x``.

    :return: A :class:`sympy.Poly` over a real domain, or ``None`` if
             this is not possible.
    """
    import sympy as sp

    ppoly = sp.Poly(poly, x)
    dom = ppoly.domain
    if dom.is_RealField or (
        isinstance(dom, sp.PolynomialRing) and dom.domain.is_RealField
    ):
        return ppoly
    return None


def cutoff_tiny(v: Expr, n: Precision | None = None) -> Expr:
    """
    Replace numerically tiny floating values by exact zero.

    If ``v`` is a :class:`sympy.Float` and ``is_zero(v, n=n)`` holds,
    :data:`sympy.S.Zero` is returned, otherwise ``v`` is returned unchanged.
    """
    import sympy as sp

    if n is not None and isinstance(v, sp.Float) and is_zero(v, n=n):
        return sp.S.Zero
    return v


def quadratic_roots(
    a1: Expr,
    a0: Expr,
    *,
    real_only: bool = True,
    n: Precision | None = None,
):
    r"""
    Solve the monic quadratic equation

    .. math::

        z^2 + a_1 z + a_0 = 0

    and return only the real roots if ``real_only=True`` (default).

    The function implements the standard quadratic formula.

    :param a1: Coefficient :math:`a_1` of :math:`z`.
    :param a0: Constant term :math:`a_0`.
    :param real_only: If ``True``, discard non-real roots.
    :param n: Optional precision used when classifying the discriminant
              as positive/non-negative via :func:`cutoff_tiny` and :func:`ge`.
    :return: A list of roots of :math:`z^2 + a_1 z + a_0 = 0`
             sorted in nondecreasing order (if they are real).
    """
    import sympy as sp

    disc = cutoff_tiny(a1**2 - 4 * a0, n=n)
    if not real_only or as_bool(ge(disc, sp.S.Zero, n=n)):
        sqrt_disc = sp.sqrt(disc)
        z1 = (-a1 + sqrt_disc) / 2
        z2 = (-a1 - sqrt_disc) / 2
        return [z1, z2]
    return []


def cubic_roots(
    a2: Expr,
    a1: Expr,
    a0: Expr,
    *,
    real_only: bool = True,
    n: Precision | None = None,
) -> list[Expr]:
    r"""
    Solve the monic cubic equation

    .. math::

        z^3 + a_2 z^2 + a_1 z + a_0 = 0

    using the algorithm from https://quarticequations.com/Selected_Algorithms.pdf.
    Only the real roots are returned if ``real_only=True``.

    The algorithm follows the two main cases in the reference:

    * Case 1 (:math:`r^2 + q^3 > 0`): one real root.
    * Case 2 (:math:`r^2 + q^3 ≤ 0`): three real roots (Viète’s trigonometric form).

    :param a2: Coefficient :math:`a_2` of :math:`z^2`.
    :param a1: Coefficient :math:`a_1` of :math:`z`.
    :param a0: Constant term :math:`a_0`.
    :param real_only: If ``True``, return only the real roots; otherwise all three
                      (possibly complex) roots are returned.
    :param n: Optional precision used in :func:`is_zero`, :func:`gt`,
              :func:`eq`, and trigonometric evaluations.
    :return: A list of roots of :math:`z^3 + a_2 z^2 + a_1 z + a_0 = 0`
             sorted in nondecreasing order (if they are real).
    """
    import sympy as sp

    q = a1 / 3 - a2**2 / 9
    r = (a1 * a2 - 3 * a0) / 6 - a2**3 / 27
    disc = cutoff_tiny(r**2 + q**3, n=n)

    if as_bool(gt(disc, sp.S.Zero)):
        # Case 1: one real root (Numerical Recipes 5.6)
        aa = (sp.Abs(r) + sp.sqrt(disc)) ** sp.Rational(1, 3)
        t1 = sp.Piecewise((aa - q / aa, sp.Ge(r, 0)), (q / aa - aa, True))
        z1 = t1 - a2 / 3
        if real_only:
            return [z1]
        x2 = -t1 / 2 - a2 / 3
        y2 = sp.sqrt(sp.Integer(3)) / 2 * (aa + q / aa)
        return [z1, x2 + sp.I * y2, x2 - sp.I * y2]
    else:
        # Case 2: three real roots (Viète)
        if is_zero(q, n=n):
            theta = 0
        else:
            arg = r / ((-q) ** sp.Rational(3, 2))
            theta = sp.S.Zero if eq(arg, sp.S.One, n=n) else sp.acos(arg)
        phi1 = theta / 3
        phi2 = phi1 - 2 * sp.pi / 3
        phi3 = phi1 + 2 * sp.pi / 3

        z1 = 2 * sp.sqrt(-q) * sp.cos(phi1) - a2 / 3
        z2 = 2 * sp.sqrt(-q) * sp.cos(phi2) - a2 / 3
        z3 = 2 * sp.sqrt(-q) * sp.cos(phi3) - a2 / 3
        return [z1, z2, z3]


def quartic_roots(
    a3: Expr,
    a2: Expr,
    a1: Expr,
    a0: Expr,
    *,
    real_only: bool = True,
    n: Precision | None = None,
) -> list[Expr]:
    r"""
    Solve the monic quartic equation

    .. math::

        z^4 + a_3 z^3 + a_2 z^2 + a_1 z + a_0 = 0

    using the modified Euler algorithm of Wolters, as described in
    https://quarticequations.com/Selected_Algorithms.pdf.

    Only real roots are returned if ``real_only=True``.

    The method uses the resolvent cubic

    .. math::

        r^3 + \frac{b_2}{2}\,r^2 + \frac{b_2^2-4 b_0}{16}\,r - \frac{b_1^2}{64}=0,

    whose three solutions :math:`r_1,r_2,r_3` are obtained via :func:`cubic_roots`.
    The greatest real solution :math:`r_1` with :math:`r_1 ≥ 0` is then used
    to compute the four quartic roots.

    :param a3: Coefficient :math:`a_3` of :math:`z^3`.
    :param a2: Coefficient :math:`a_2` of :math:`z^2`.
    :param a1: Coefficient :math:`a_1` of :math:`z`.
    :param a0: Constant term :math:`a_0`.
    :param real_only: If ``True``, discard complex roots derived from
                      negative radicands.
    :param n: Optional precision used in the classification of real
              radicands via :func:`ge` and in cubic root computation.
    :return: A list of real roots of
             :math:`z^4 + a_3 z^3 + a_2 z^2 + a_1 z + a_0 = 0`.
    """
    import sympy as sp

    # Coefficients used in the modified Euler algorithm (Selected Algorithms)
    c = a3 / 4
    b2 = a2 - 6 * c**2
    b1 = a1 - 2 * a2 * c + 8 * c**3
    b0 = a0 - a1 * c + a2 * c**2 - 3 * c**4
    sigma = sp.sign(b1)

    # Solve the resolvent cubic
    # r^3 + b2/2 r^2 + (b2^2 - 4 b0)/16 r - b1^2 / 64 = 0
    r1, r2, r3 = cubic_roots(
        b2 / 2,
        (b2**2 - 4 * b0) / 16,
        -(b1**2) / 64,
        real_only=False,
        n=n,
    )
    x2, y2, x3 = sp.re(r2), sp.im(r2), sp.re(r3)

    # Step 2: Compute the roots based on the greatest real solution r1
    #   T1,2 =  sqrt(r1) ± sqrt(x2 + x3 - 2 Σ sqrt(x2 x3) + y2^2)
    #   T3,4 = -sqrt(r1) ± sqrt(x2 + x3 + 2 Σ sqrt(x2 x3) + y2^2)

    r1sqrt = sp.sqrt(r1)
    x23 = x2 + x3
    inner = sp.sqrt(x2 * x3 + y2**2)

    radicant1 = x23 - 2 * sigma * inner
    radicant2 = x23 + 2 * sigma * inner

    solutions: list[Expr] = []
    if not real_only or as_bool(ge(radicant1, sp.S.Zero)):
        root1 = sp.sqrt(radicant1)
        solutions.append(r1sqrt + root1 - c)
        solutions.append(r1sqrt - root1 - c)
    if not real_only or as_bool(ge(radicant2, sp.S.Zero)):
        root2 = sp.sqrt(radicant2)
        solutions.append(-r1sqrt + root2 - c)
        solutions.append(-r1sqrt - root2 - c)
    return solutions


def polynomial_roots(
    poly: Expr,
    x: Symbol,
    *,
    real_only: bool = True,
    n: Precision | None = None,
) -> dict[Expr, int]:
    """
    Compute roots of a univariate polynomial up to degree 4.

    The input expression is converted to :class:`sympy.Poly` in ``x`` and dispatched
    to the appropriate specialized solver:

    * degree 4: :func:`quartic_roots`
    * degree 3: :func:`cubic_roots`
    * degree 2: :func:`quadratic_roots`
    * degree 1: explicit linear solution
    * degree 0: either no solution or infinitely many solutions

    The returned dictionary maps each root to its multiplicity using
    :class:`collections.Counter`.

    :param poly: Polynomial expression in the variable ``x``.
    :param x: Polynomial variable.
    :param real_only: If ``True``, only real roots are produced by the
                      specialized solvers.
    :param n: Optional precision forwarded to the root solvers.
    :return: A mapping ``{root: multiplicity}``.
    :raises ValueError: If the polynomial degree is greater than 4 or for the
                        identically zero polynomial (infinitely many solutions).
    """
    import sympy as sp

    ppoly = sp.Poly(poly, x)
    res: list[Expr] | None
    match ppoly.all_coeffs():
        case [a4, a3, a2, a1, a0]:
            res = quartic_roots(
                a3 / a4, a2 / a4, a1 / a4, a0 / a4, real_only=real_only, n=n
            )
        case [a3, a2, a1, a0]:
            res = cubic_roots(a2 / a3, a1 / a3, a0 / a3, real_only=real_only, n=n)
        case [a2, a1, a0]:
            res = quadratic_roots(a1 / a2, a0 / a2, real_only=real_only, n=n)
        case [a1, a0]:
            res = [-a0 / a1]
        case [a0]:
            if is_zero(a0):
                raise ValueError("Infinitely many solutions!")
            res = []
        case _:
            raise ValueError(
                f"Only polynomials up to degree 4 are supported, got {poly}"
            )
    return Counter(res)


def _sylvester_matrix(p: Poly, q: Poly) -> "sp.Matrix":
    """
    Construct the Sylvester matrix of two polynomials :math:`p(x), q(x)`.

    The input polynomials must be in the same variable and given
    as :class:`sympy.Poly` instances.  The resulting square matrix has size
    :math:`(\\deg(p) + \\deg(q)) × (\\deg(p) + \\deg(q))` and is constructed
    from shifted coefficient rows.
    """
    import sympy as sp

    m, n = p.degree(), q.degree()
    assert isinstance(m, int) and isinstance(n, int)
    size = m + n

    # Coefficients in *descending* powers: a_m, ..., a_0
    a, b = p.all_coeffs(), q.all_coeffs()

    # Helper to create a row that is a shifted version of coefficients
    def shifted_row(coeffs, shift):
        # shift = number of leading zeros
        return [0] * shift + coeffs + [0] * (size - shift - len(coeffs))

    rows = [shifted_row(a, k) for k in range(n)] + [shifted_row(b, k) for k in range(m)]

    return sp.Matrix(rows)


def resultant(
    f: Expr,
    g: Expr,
    x: Symbol,
    y: Symbol,
    n: Precision | None = None,
) -> Expr:
    """
    Resultant :math:`\\operatorname{res}_y(f, g)`.

    Eliminates variable :math:`y` from the system :math:`f(x, y) = 0`,
    :math:`g(x, y) = 0`.

    If both expressions are real polynomials in :math:`y`,
    the resultant is computed as the determinant of the Sylvester matrix,
    then numerically evaluated with :func:`evalf` using precision ``n``.
    Coefficients that are numerically zero (according to :func:`is_zero`
    with precision ``n``) are normalized to exact zero.

    Otherwise, :func:`sympy.resultant` is used.
    """
    import sympy as sp

    fp, gp = _as_real_poly(f, y), _as_real_poly(g, y)
    if fp and gp:
        res = _sylvester_matrix(fp, gp).det(method="laplace")
        assert isinstance(res, sp.Expr)
        res = evalf(res, n=n)
        assert isinstance(res, sp.Expr)

        new_coeffs: list[sp.Expr] = []
        rpoly = sp.Poly(res, x)
        for c in rpoly.all_coeffs():
            if is_zero(c, n=n):
                new_coeffs.append(sp.S.Zero)
            else:
                new_coeffs.append(c)
        return sp.Poly(new_coeffs, rpoly.gens).as_expr()
    r = sp.resultant(f, g, y)
    assert isinstance(r, sp.Expr)
    return r


def expand(expr: Expr) -> Expr:
    """
    Algebraically expand a SymPy expression.

    Thin wrapper around :func:`sympy.expand`.
    """
    import sympy as sp

    return sp.expand(expr)
