# This file is part of https://github.com/KurtBoehm/svg-path-editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from decimal import Decimal
from typing import Callable

from svg_path_editor.geometry import Point, dot, rotation_matrix
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
    Round the corners between straight-line segments in closed subpaths.

    The input must be a sequence of closed subpaths ``M … Z``. Every corner between two
    straight line segments (``L``/``H``/``V``/``Z``) is replaced by:

    * a shortened segment from :math:`A` to :math:`P` (on :math:`AB`),
    * a circular arc (``A`` command) from :math:`P` to :math:`Q` of radius ``radius``,
    * a shortened segment from :math:`Q` to :math:`C` (on :math:`BC`),

    where the corner is at point :math:`B` between segments :math:`AB` and :math:`BC`.

    Only corners with both adjacent segments line-like are processed.
    The original path is not modified.

    :param path: :class:`SvgPath` containing one or more closed subpaths ``M … Z``.
    :param radius: Corner rounding radius. Must be positive.
    :param selector: Optional callback ``selector(a, b, c) -> bool`` that decides
                     whether to round the corner at ``b`` between the segments ``ab``
                     and ``bc``. If it returns ``False`` the corner is left unchanged.

    :return: A new :class:`SvgPath` where the selected corners between line-like
             segments are rounded with circular arcs.

    :raises ValueError: If ``radius`` is not positive.
    """
    import sympy as sp

    r = Decimal(radius)
    if r <= 0:
        raise ValueError("The radius must be positive!")
    rr = dec_to_rat(r)

    # Work on a clone and convert everything to absolute to simplify logic
    new_path = path.clone()
    new_path.relative = False

    def is_line_like(it: SvgItem) -> bool:
        return isinstance(it, (LineTo, HorizontalLineTo, VerticalLineTo, ClosePath))

    items = new_path.path
    n = len(items)
    if n < 3:
        return new_path

    result: list[SvgItem] = []

    for i, curr in enumerate(items):
        post = items[(i + 1) % n]

        if isinstance(curr, MoveTo):
            j = i + 1
            while not isinstance(items[j], ClosePath):
                assert not isinstance(items[j], MoveTo)
                j += 1
            ante = items[j]
        else:
            ante = curr

        if not (is_line_like(ante) and is_line_like(post)):
            result.append(curr)
            continue

        # Geometry: a → b → c, corner at b
        a = ante.previous_point
        b = curr.target_location
        c = post.target_location

        if not selector(a, b, c):
            result.append(curr)
            continue

        a, b, c = a.vec2, b.vec2, c.vec2

        # Vectors from the corner
        v1, v2 = a - b, c - b

        l1, l2 = v1.length, v2.length
        if l1 == 0 or l2 == 0:
            result.append(curr)
            continue

        # Unit vectors
        u1, u2 = v1 / l1, v2 / l2
        if u1 == u2:
            result.append(curr)
            continue

        # Angle between segments
        udot = dot(u1, u2)
        # Clamp to valid range for acos
        udot = max(min(udot, sp.S.One), -sp.S.One)

        theta = sp.acos(udot)

        # Distance from corner along each segment to tangent points
        d = rr * sp.cot(theta / 2)

        # Ensure we don’t overshoot the segment length
        if d >= l1 or d >= l2:
            # Corner too sharp or segments too short: skip rounding here
            result.append(curr)
            continue

        # New tail/head points on each segment
        tail1, head2 = (b + u1 * d).point, (b + u2 * d).point

        # Shorten `curr` so it ends at tail1 and add it to the path
        curr.set_target_location(tail1)
        result.append(curr)

        # Compute the angle of v1, rotate v2 by that angle, and compute the angle
        # to determine the sweep
        v1deg = sp.deg(sp.atan2(v1.y, v1.x))
        v2rot = rotation_matrix(-v1deg) @ v2
        sweep = as_bool(sp.atan2(v2rot.y, v2rot.x) < 0)

        # Arc from tail1 to head2 with radius r
        # Sweep chosen so it rounds the outside of the corner
        arc = A(
            rx=r,
            ry=r,
            angle=0,
            large_arc_flag=False,
            sweep_flag=sweep,
            x=head2.x,
            y=head2.y,
        )

        result.append(arc)

        # Update `post` start so it will start at head2.
        post.previous_point = SvgPoint(head2.x, head2.y)

    new_path.path = result
    new_path.refresh_absolute_positions()
    return new_path
