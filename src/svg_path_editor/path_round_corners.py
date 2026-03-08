# This file is part of https://github.com/KurtBoehm/svg-path-editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from decimal import Decimal
from typing import Callable, Literal

from svg_path_editor.geometry import Point, Vec2, dot, rotation_matrix
from svg_path_editor.math import Number, as_bool, dec_to_rat
from svg_path_editor.svg import (
    A,
    ClosePath,
    HorizontalLineTo,
    LineTo,
    MoveTo,
    SvgItem,
    SvgPath,
    SvgPoint,
    VerticalLineTo,
)


def round_corners(
    path: SvgPath,
    radius: Number,
    *,
    selector: Callable[[Point, Point, Point], bool] = lambda a, b, c: True,
) -> SvgPath:
    """
    Round corners between straight segments in closed subpaths.

    The input must be one or more closed subpaths ``M … Z``. Each corner between two
    straight segments (``L``/``H``/``V``/``Z``) at point :math:`B` between
    :math:`AB` and :math:`BC` is replaced by:

    * a shortened segment from :math:`A` to :math:`P` on :math:`AB`,
    * a circular arc from :math:`P` to :math:`Q` with radius ``radius``,
    * a shortened segment from :math:`Q` to :math:`C` on :math:`BC`.

    Only corners with straight incoming and outgoing segments are modified.
    The input path is not modified.

    :param path: :class:`SvgPath` with one or more closed subpaths ``M … Z``.
    :param radius: Corner radius; must be positive.
    :param selector: Optional ``selector(a, b, c) -> bool``; if it returns ``False``
                     for corner :math:`B` between :math:`AB` and :math:`BC`,
                     that corner is left unchanged.

    :return: New :class:`SvgPath` with chosen line-line corners rounded by arcs.
    :raises ValueError: If ``radius`` is not positive.
    """
    import sympy as sp

    r = Decimal(radius)
    if r <= 0:
        raise ValueError("The radius must be positive!")
    rr = dec_to_rat(r)

    # Work on a cloned, fully absolute path to simplify logic
    new_path = path.clone()
    new_path.relative = False

    def is_line_like(it: SvgItem) -> bool:
        return isinstance(it, (LineTo, HorizontalLineTo, VerticalLineTo, ClosePath))

    items = new_path.path
    n = len(items)
    if n < 3:
        return new_path

    result: list[SvgItem] = []
    # Per-item adjusted points after shortening/offsetting segments
    off_pts: dict[tuple[int, Literal["prv", "tgt"]], Vec2] = {}

    for i, curr in enumerate(items):
        post_idx = (i + 1) % n
        post = items[post_idx]

        if isinstance(curr, MoveTo):
            # For the first item of a subpath, "ante" is the closing segment
            j = i + 1
            while not isinstance(items[j], ClosePath):
                assert not isinstance(items[j], MoveTo)
                j += 1
            ante_idx = j
        else:
            ante_idx = i
        ante = items[ante_idx]

        if not (is_line_like(ante) and is_line_like(post)):
            result.append(curr)
            continue

        # Corner geometry: a → b → c, corner at b
        a = ante.previous_point
        b = curr.target_location
        c = post.target_location

        if not selector(a, b, c):
            result.append(curr)
            continue

        # Use previously adjusted endpoints if this segment was already shortened
        a = off_pts.get((ante_idx, "prv"), a.vec2)
        b = off_pts.get((i, "tgt"), b.vec2)
        c = off_pts.get((post_idx, "tgt"), c.vec2)

        # Vectors from corner b along incoming and outgoing segments
        v1, v2 = a - b, c - b

        l1, l2 = v1.length, v2.length
        if l1 == 0 or l2 == 0:
            result.append(curr)
            continue

        # Unit directions
        u1, u2 = v1 / l1, v2 / l2
        if u1 == u2:
            result.append(curr)
            continue

        # Angle between segments
        udot = dot(u1, u2)
        # Clamp for acos
        udot = max(min(udot, sp.S.One), -sp.S.One)
        theta = sp.acos(udot)

        # Distance from corner to tangent points on each segment
        d = rr * sp.cot(theta / 2)

        # Skip if the fillet would be longer than a segment
        if d >= l1 or d >= l2:
            result.append(curr)
            continue

        # New endpoints: tail of incoming, head of outgoing
        tail1, head2 = b + u1 * d, b + u2 * d
        head2x, head2y = head2.point

        # Shorten current segment to end at tail1
        curr.set_target_location(tail1.point)
        off_pts[i, "tgt"] = tail1
        result.append(curr)

        # Determine sweep direction: rotate v2 into v1’s frame and check sign
        v1deg = sp.deg(sp.atan2(v1.y, v1.x))
        v2rot = rotation_matrix(-v1deg) @ v2
        sweep = as_bool(sp.atan2(v2rot.y, v2rot.x) < 0)

        # Arc from tail1 to head2 with radius r, rounding the external corner
        arc = A(
            rx=r,
            ry=r,
            angle=0,
            large_arc_flag=False,
            sweep_flag=sweep,
            x=head2x,
            y=head2y,
        )
        result.append(arc)

        # Make following segment start at head2
        post.previous_point = SvgPoint(head2x, head2y)
        off_pts[post_idx, "prv"] = head2

    new_path.path = result
    new_path.refresh_absolute_positions()
    return new_path
