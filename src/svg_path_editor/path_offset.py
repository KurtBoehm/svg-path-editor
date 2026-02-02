from decimal import Decimal, getcontext
from typing import Literal, TypeGuard

from .geometry import Line, ParametricEllipticalArc, polygon_signed_area
from .intersect import (
    ArcArcAroundIntersection,
    ArcArcExtIntersection,
    LineArcAroundIntersection,
    LineArcExtIntersection,
    LineAroundIntersection,
    intersect,
)
from .math import Number, Precision, dec_to_rat
from .svg import ClosePath, EllipticalArcTo, LineTo, MoveTo, SvgItem, SvgPath

additional_digits: int = 8
"""Extra decimal digits used when ``prec="auto"``."""


def _all_non_none[T](elems: list[T | None]) -> TypeGuard[list[T]]:
    """
    Type helper asserting that a list contains no ``None`` values.

    :param elems: List potentially containing ``None``.
    :return: ``True`` iff all elements are non-``None``.
    """
    return all(e is not None for e in elems)


def offset_path(
    path: SvgPath,
    *,
    d: Number,
    prec: Precision | Literal["auto", "auto-intersections"] | None = None,
) -> SvgPath:
    """
    Offset a simple closed SVG path.

    The input must be a single closed subpath of the form ``M … Z``,
    consisting only of straight line segments and elliptical arcs.
    Each segment is offset inwards by ``d``, and consecutive offset
    segments are intersected pairwise to construct the new path.

    Algorithm outline
    -----------------
    1. Collect absolute vertex positions of the original path.
    2. Determine polygon orientation via :func:`polygon_signed_area`.
    3. For each segment, build an offset segment:
       * lines → offset :class:`Line` segments,
       * arcs → radius-reduced :class:`ParametricEllipticalArc` instances.
    4. Intersect consecutive offset segments using :func:`intersect`.
    5. Reconstruct an SVG path through the intersection points, preserving
       original arc flags and rotation but using the offset radii.

    :param path: Closed input :class:`SvgPath` consisting of exactly one subpath
        ``M … Z`` with line and elliptical-arc segments only.
    :param d: Offset distance. Positive values move edges inwards.
    :param prec: Optional intersection precision.

        * If ``"auto"``, use the current decimal precision plus
          :data:`additional_digits` for both offset geometry and intersections.
        * If ``"auto-intersections"``, use this automatic precision only for
          intersection computations and keep the original precision for
          geometry construction.
        * If a :class:`Precision` instance, pass it unchanged to geometric and
          intersection helpers.
        * If ``None``, no explicit precision control is applied.

    :return: New :class:`SvgPath` representing the offset polygon.
    :raises AssertionError: If the path is not a single closed subpath of the
        expected form, or if offset-intersection construction fails.
    """
    d = Decimal(d)
    δ = dec_to_rat(d)

    if prec == "auto" or prec == "auto-intersections":
        iprec = Precision(getcontext().prec, additional_digits)
        oprec = iprec if prec == "auto" else None
    else:
        oprec = iprec = prec

    # Validate that the path is a single closed subpath: M ... Z
    items = path.path
    assert items, "Empty path."
    assert isinstance(items[0], MoveTo), "Path must start with MoveTo."
    assert isinstance(items[-1], ClosePath), "Path must end with ClosePath."

    # Collect absolute vertex positions (skip closing Z)
    pts = [it.target_location().vec2 for it in items[:-1]]
    n = len(pts)
    assert n >= 2, "Path must contain at least one segment."

    # Orientation: negative signed area means counter-clockwise polygon.
    is_ccw = polygon_signed_area(pts) < 0

    # Construct offset segments for each original segment (cyclic).
    offsets = [
        it.to_geometry(n=oprec).offset(d=δ, is_ccw=is_ccw, n=oprec)
        if isinstance(it := items[i + 1], EllipticalArcTo)
        else Line(pts[i], pts[(i + 1) % n]).offset(d=δ, is_ccw=is_ccw, n=oprec)
        for i in range(n)
    ]

    # Compute pairwise intersections between consecutive offset segments (cyclic).
    # These intersections become the vertices of the offset path.
    inters = [intersect(offsets[i - 1], offsets[i], d=d, n=iprec) for i in range(n)]
    assert _all_non_none(inters), "Offset intersection computation failed."

    # Start the new path at the first intersection point (absolute M).
    new_items: list[SvgItem] = [MoveTo([*inters[0].intersection.point], relative=False)]

    # Reconstruct the offset path by walking offset segments and their intersections.
    for i, (offset, inter0, inter1) in enumerate(
        zip(offsets, inters[:-1], inters[1:]),
        start=1,
    ):
        if isinstance(offset, ParametricEllipticalArc):
            # Offset of an original EllipticalArcTo segment.
            orig = items[i]
            assert isinstance(orig, EllipticalArcTo)

            if isinstance(inter0, (LineArcExtIntersection, ArcArcExtIntersection)):
                # Enter arc via its ante extension; attach a straight segment first.
                assert (
                    not isinstance(inter0, LineArcExtIntersection)
                    or inter0.ext == "ante"
                )
                ante_pt = inter0.post_intersection.point
                new_items.append(LineTo([*ante_pt], relative=False))
            if isinstance(inter0, ArcArcAroundIntersection):
                # Incoming arc “wraps around” this arc: connect via extended points.
                new_items.append(LineTo([*inter0.ante_extended.point], relative=False))
                new_items.append(LineTo([*inter0.post_extended.point], relative=False))
                ante_pt = inter0.post_intersection.point
                new_items.append(LineTo([*ante_pt], relative=False))
            if isinstance(inter0, LineArcAroundIntersection):
                # Incoming line wraps around arc: connect through extended segment.
                new_items.append(LineTo([*inter0.post_extended.point], relative=False))
                new_items.append(
                    LineTo([*inter0.post_intersection.point], relative=False)
                )

            # Determine endpoint on the offset arc corresponding to the outgoing side.
            if isinstance(inter1, LineArcExtIntersection):
                post = inter1.post_intersection.point
            elif isinstance(inter1, ArcArcExtIntersection):
                post = inter1.ante_intersection.point
            elif isinstance(
                inter1,
                (LineArcAroundIntersection, ArcArcAroundIntersection),
            ):
                post = inter1.ante_intersection.point
            else:
                post = inter1.intersection.point

            # Preserve rotation and flags from the original arc; only radii and
            # endpoint are updated to match the offset geometry.
            r_off = offset.r.point
            new_items.append(
                EllipticalArcTo(
                    [
                        r_off.x,
                        r_off.y,
                        orig.values[2],  # rotation
                        orig.values[3],  # large-arc-flag
                        orig.values[4],  # sweep-flag
                        post.x,
                        post.y,
                    ],
                    relative=False,
                )
            )

            if isinstance(inter1, (LineArcExtIntersection, ArcArcExtIntersection)):
                # Leave arc via its post extension; follow with a straight segment.
                assert (
                    not isinstance(inter1, LineArcExtIntersection)
                    or inter1.ext == "post"
                )
                post_pt = inter1.intersection.point
                new_items.append(LineTo([post_pt.x, post_pt.y], relative=False))
        else:
            # Offset segment is a straight line; join using L commands.
            if isinstance(inter0, LineAroundIntersection):
                # Previous line continues around; use its extended endpoint.
                new_items.append(LineTo([*inter0.post_extended.point], relative=False))
            elif isinstance(inter0, LineArcAroundIntersection):
                # Previous segment wraps around an arc; bridge via both extensions.
                new_items.append(LineTo([*inter0.ante_extended.point], relative=False))
                new_items.append(LineTo([*inter0.post_extended.point], relative=False))

            # Determine endpoint for this offset line based on the outgoing intersection.
            if isinstance(
                inter1,
                (
                    LineAroundIntersection,
                    LineArcAroundIntersection,
                    ArcArcAroundIntersection,
                ),
            ):
                post = inter1.ante_extended
            else:
                post = inter1.intersection
            new_items.append(LineTo([*post.point], relative=False))

    # Close the reconstructed offset path.
    new_items.append(ClosePath([], False))
    return SvgPath(new_items)
