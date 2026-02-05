from collections.abc import Iterable
from decimal import Decimal, getcontext
from typing import Literal, NamedTuple, TypeGuard

from .geometry import Line, ParametricEllipticalArc, Point, polygon_signed_area
from .intersect import (
    ArcArcAroundIntersection,
    ArcArcExtIntersection,
    Intersection,
    LineArcAroundIntersection,
    LineArcExtIntersection,
    LineAroundIntersection,
    intersect,
)
from .math import Number, Precision, dec_to_rat
from .svg import ClosePath, EllipticalArcTo, L, M, MoveTo, SvgItem, SvgPath, Z

type Shape = Line | ParametricEllipticalArc

additional_digits: int = 8
"""Extra decimal digits used when ``prec="auto"``."""


def _all_non_none[T](elems: list[T | None]) -> TypeGuard[list[T]]:
    """Return ``True`` iff ``elems`` contains no ``None`` values."""
    return all(e is not None for e in elems)


class _OffsetData(NamedTuple):
    """Precomputed data for offsetting a simple closed path."""

    items: list[SvgItem]
    offsets: list[Shape]
    inters: list[Intersection]


def _prepare_offset_data(
    path: SvgPath,
    *,
    d: Number,
    prec: Precision | Literal["auto", "auto-intersections"] | None,
) -> _OffsetData:
    """
    Validate ``path`` and compute offset segments and their intersections.
    """
    d = Decimal(d)
    δ = dec_to_rat(d)

    if prec == "auto" or prec == "auto-intersections":
        # iprec: numeric precision for intersections, oprec: for offset geometry.
        iprec = Precision(getcontext().prec, additional_digits)
        oprec = iprec if prec == "auto" else None
    else:
        oprec = iprec = prec

    # Require a single closed subpath: M ... Z.
    items = path.path
    assert items, "Empty path."
    assert isinstance(items[0], MoveTo), "Path must start with MoveTo."
    assert isinstance(items[-1], ClosePath), "Path must end with ClosePath."

    # Absolute vertex positions (omit final Z).
    pts = [it.target_location.vec2 for it in items[:-1]]
    n = len(pts)
    assert n >= 2, "Path must contain at least one segment."

    # Negative signed area ⇒ CCW polygon.
    is_ccw = polygon_signed_area(pts) < 0

    # Offset each segment (cyclic).
    offsets = [
        it.to_geometry(n=oprec).offset(d=δ, is_ccw=is_ccw, n=oprec)
        if isinstance(it := items[i + 1], EllipticalArcTo)
        else Line(pts[i], pts[(i + 1) % n]).offset(d=δ, is_ccw=is_ccw, n=oprec)
        for i in range(n)
    ]

    # Intersections between consecutive offset segments (cyclic).
    inters: list[Intersection | None] = [
        intersect(offsets[i - 1], offsets[i], d=d, n=iprec) for i in range(n)
    ]
    assert _all_non_none(inters), "Offset intersection computation failed."

    return _OffsetData(items=items, offsets=offsets, inters=inters)


def _line_outgoing_point(inter1: Intersection) -> Point:
    """Outgoing point of a line offset segment (after ``inter1``)."""
    if isinstance(
        inter1,
        (LineAroundIntersection, LineArcAroundIntersection, ArcArcAroundIntersection),
    ):
        return inter1.ante_extended.point
    return inter1.intersection.point


def _arc_outgoing_point(inter1: Intersection) -> Point:
    """Outgoing point of an arc offset segment (after ``inter1``)."""
    if isinstance(inter1, LineArcExtIntersection):
        return inter1.post_intersection.point
    if isinstance(inter1, ArcArcExtIntersection):
        return inter1.ante_intersection.point
    if isinstance(inter1, (LineArcAroundIntersection, ArcArcAroundIntersection)):
        return inter1.ante_intersection.point
    return inter1.intersection.point


class Tri(NamedTuple):
    """Small bevel triangle between original and offset geometry."""

    orig0: Point
    off0: Point
    off1: Point

    @property
    def path(self) -> SvgPath:
        """Return this triangle as a closed ``SvgPath``."""
        return SvgPath([M(*self.orig0), L(*self.off1), L(*self.off0), Z()])


def _iter_segment_contexts(
    offsets: list[Shape],
    inters: list[Intersection],
    items: list[SvgItem],
) -> Iterable[tuple[SvgItem, Shape, Intersection, Intersection]]:
    """
    Yield ``(orig_item, offset_geom, incoming_inter, outgoing_inter)`` per segment.
    """
    for item, offset, inter0, inter1 in zip(
        items[1:], offsets, inters[:-1], inters[1:]
    ):
        yield item, offset, inter0, inter1


def _arc_ante(
    orig: EllipticalArcTo,
    inter0: Intersection,
) -> tuple[Point, tuple[Tri, ...]]:
    """
    Handle the incoming side of an offset arc.

    Returns the ante point on the offset arc plus bevel triangles
    to emit before the arc segment.
    """
    p0 = orig.previous_point
    if isinstance(inter0, (LineArcExtIntersection, ArcArcExtIntersection)):
        # Enter via ante extension: one small triangle.
        assert not isinstance(inter0, LineArcExtIntersection) or inter0.ext == "ante"
        ante = inter0.post_intersection.point
        tris = (Tri(p0, inter0.intersection.point, ante),)
    elif isinstance(inter0, ArcArcAroundIntersection):
        # Incoming arc wraps around this arc: three triangles.
        p1, p2 = inter0.ante_intersection.point, inter0.ante_extended.point
        p3, ante = inter0.post_extended.point, inter0.post_intersection.point
        tris = (Tri(p0, p1, p2), Tri(p0, p2, p3), Tri(p0, p3, ante))
    elif isinstance(inter0, LineArcAroundIntersection):
        # Incoming line wraps around arc: two triangles.
        p1 = inter0.ante_extended.point
        p2, ante = inter0.post_extended.point, inter0.post_intersection.point
        tris = (Tri(p0, p1, p2), Tri(p0, p2, ante))
    else:
        ante = inter0.intersection.point
        tris = ()
    return ante, tris


def _arc_post(orig: EllipticalArcTo, inter1: Intersection) -> Iterable[Tri]:
    """
    Handle the outgoing side of an offset arc.

    Yields bevel triangles to emit after the arc segment.
    """
    if isinstance(inter1, LineArcExtIntersection):
        # Leave via post extension (line–arc).
        assert inter1.ext == "post"
        p1, p2 = inter1.post_intersection.point, inter1.intersection.point
        yield Tri(orig.target_location, p1, p2)
    if isinstance(inter1, ArcArcExtIntersection):
        # Leave via post extension (arc–arc).
        p1, p2 = inter1.ante_intersection.point, inter1.intersection.point
        yield Tri(orig.target_location, p1, p2)


def _line_ante(orig: SvgItem, inter0: Intersection) -> tuple[Point, tuple[Tri, ...]]:
    """
    Handle the incoming side of a straight segment.

    Returns the ante point on the offset line plus bevel triangles
    to emit before the line segment.
    """
    p0 = orig.previous_point
    if isinstance(inter0, LineAroundIntersection):
        p1, ante = inter0.ante_extended.point, inter0.post_extended.point
        tris = (Tri(p0, p1, ante),)
    elif isinstance(inter0, LineArcAroundIntersection):
        p1, p2 = inter0.ante_intersection.point, inter0.ante_extended.point
        ante = inter0.post_extended.point
        tris = (Tri(p0, p1, p2), Tri(p0, p2, ante))
    else:
        ante = inter0.intersection.point
        tris = ()
    return ante, tris


def offset_path(
    path: SvgPath,
    *,
    d: Number,
    prec: Precision | Literal["auto", "auto-intersections"] | None = None,
) -> SvgPath:
    """
    Offset a simple closed SVG path.

    The input must be a single closed subpath ``M … Z`` of straight lines and
    elliptical arcs. Every segment is offset by distance ``d`` (inwards for ``d > 0``),
    and consecutive offset segments are intersected to form the output path.

    :param path: Closed :class:`SvgPath` with exactly one subpath ``M … Z``, using only
                 line and elliptical-arc segments.
    :param d: Offset distance. Positive values move edges towards the interior.
    :param  prec: Intersection and offsetting precision:

        * ``"auto"``: decimal precision + :data:`additional_digits`
          for both offset geometry and intersections.
        * ``"auto-intersections"``: same automatic precision for intersections only;
          offsets remain symbolic.
        * :class:`Precision`: use this precision everywhere.
        * ``None``: purely symbolic where supported.

    :return: The offset closed path.
    :raises AssertionError: If ``path`` is not a single closed subpath of the
        expected form, or if an offset intersection cannot be computed.
    """
    data = _prepare_offset_data(path, d=d, prec=prec)
    items, offsets, inters = data

    # Start at the first offset intersection.
    new_items: list[SvgItem] = [M(*inters[0].intersection.point)]

    # Walk segments and construct the offset geometry.
    for orig, offset, inter0, inter1 in _iter_segment_contexts(offsets, inters, items):
        if isinstance(offset, ParametricEllipticalArc):
            # Offset of an EllipticalArcTo segment.
            assert isinstance(orig, EllipticalArcTo)

            _, tris = _arc_ante(orig, inter0)
            new_items.extend(L(*tri.off1) for tri in tris)

            # Keep rotation and flags; update radii and endpoint.
            new_items.append(
                EllipticalArcTo(
                    [
                        *offset.r.point,
                        orig.values[2],  # rotation
                        orig.values[3],  # large-arc-flag
                        orig.values[4],  # sweep-flag
                        *_arc_outgoing_point(inter1),
                    ],
                    relative=False,
                )
            )

            new_items.extend(L(*tri.off1) for tri in _arc_post(orig, inter1))
        else:
            # Offset of a straight segment.
            _, tris = _line_ante(orig, inter0)
            new_items.extend(L(*tri.off1) for tri in tris)
            new_items.append(L(*_line_outgoing_point(inter1)))

    new_items.append(Z())
    return SvgPath(new_items)


def bevel_path(
    path: SvgPath,
    *,
    d: Number,
    prec: Precision | Literal["auto", "auto-intersections"] | None = None,
) -> Iterable[SvgPath]:
    """
    Construct bevel faces for an offset of a simple closed path.

    Unlike :func:`offset_path`, this yields only the auxiliary faces that fill
    the bevel region between the original path and its offset.

    :param path: Closed :class:`SvgPath` with exactly one subpath ``M … Z``, using only
                 line and elliptical-arc segments.
    :param d: Offset distance. Positive values move edges towards the interior.
    :param prec: Same semantics as in :func:`offset_path`.
    :return: Closed paths covering the bevel surface between original and offset.
    :raises AssertionError: If ``path`` is not a single closed subpath of the
        expected form, or if an offset intersection cannot be computed.
    """
    data = _prepare_offset_data(path, d=d, prec=prec)
    items, offsets, inters = data

    # Emit bevel faces per segment.
    for orig, offset, inter0, inter1 in _iter_segment_contexts(offsets, inters, items):
        if isinstance(offset, ParametricEllipticalArc):
            # Bevel for an arc segment.
            assert isinstance(orig, EllipticalArcTo)

            ante_pt, tris = _arc_ante(orig, inter0)
            for tri in tris:
                yield tri.path

            # Bevel between original arc and its offset.
            r_off = offset.r.point
            rot, larc, s = orig.values[2:5]
            mov = M(*orig.previous_point)
            lin = L(*_arc_outgoing_point(inter1))
            arc = EllipticalArcTo([*r_off, rot, larc, 1 - s, *ante_pt], relative=False)
            yield SvgPath([mov, orig, lin, arc, Z()])

            for tri in _arc_post(orig, inter1):
                yield tri.path
        else:
            # Bevel for a straight segment.
            ante_pt, tris = _line_ante(orig, inter0)
            for tri in tris:
                yield tri.path

            p0, p1 = orig.previous_point, orig.target_location
            p2 = _line_outgoing_point(inter1)
            yield SvgPath([M(*p0), L(*p1), L(*p2), L(*ante_pt), Z()])

    # Final bevel closing the loop between last and first offsets.
    orig_last = items[-1]
    p0, p1 = orig_last.previous_point, orig_last.target_location
    p2, p3 = inters[0].intersection.point, inters[-1].intersection.point
    yield SvgPath([M(*p0), L(*p1), L(*p2), L(*p3), Z()])
