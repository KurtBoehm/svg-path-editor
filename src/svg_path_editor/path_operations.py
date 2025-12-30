# This file is part of https://github.com/KurtBoehm/svg_path_editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from typing import Final

from .sub_path_bounds import get_sub_path_bounds
from .svg import Point, SvgItem, SvgPath

__all__ = ["reverse_path", "optimize_relative_absolute", "optimize_path"]


def _to_str(pt: Point) -> tuple[str, str]:
    """Return a point’s coordinates as a pair of strings."""
    return str(pt.x), str(pt.y)


def reverse_path(svg: SvgPath, subpath_of_item: int | None = None) -> SvgPath:
    """
    Reverse the drawing direction of a path or sub-path.

    :param svg: Input path.
    :param subpath_of_item:
        Index of an item within the sub-path to reverse, or ``None`` to
        reverse the entire path.

    :returns:
        A new path with the selected segment reversed. Geometry is preserved,
        but command types and relative/absolute representation may change.
    """
    start, end = get_sub_path_bounds(svg, subpath_of_item)

    # Nothing to reverse if fewer than two items in the subpath.
    if end - start <= 1:
        return svg.clone()

    new_svg = svg.clone()
    path = new_svg.path

    # If the item following the subpath is relative, temporarily switch it
    # to absolute so we can rewrite the sub-path safely.
    is_before_relative = end < len(path) and path[end].relative
    if is_before_relative:
        path[end].relative = False

    sub_path = path[start:end]
    output_path: list[SvgItem] = []
    reversed_path = list(reversed(sub_path))[:-1]

    start_point = reversed_path[0].target_location()
    output_path.append(SvgItem.make(["M", *_to_str(start_point)]))
    previous_type = ""
    is_closed = False

    for component in reversed_path:
        pt = _to_str(component.previous_point)
        ctrl = [_to_str(p) for p in component.absolute_points]
        component_type = component.get_type(True)

        match component_type:
            case "M" | "Z":
                if is_closed:
                    output_path.append(SvgItem.make(["Z"]))
                is_closed = component_type == "Z"
                if output_path[-1].get_type(True) == "M":
                    output_path[-1] = SvgItem.make(["M", *pt])
                else:
                    output_path.append(SvgItem.make(["M", *pt]))
            case "L":
                output_path.append(SvgItem.make(["L", *pt]))
            case "H":
                output_path.append(SvgItem.make(["H", pt[0]]))
            case "V":
                output_path.append(SvgItem.make(["V", pt[1]]))
            case "C":
                # Swap control points when reversing cubic Bézier.
                output_path.append(SvgItem.make(["C", *ctrl[1], *ctrl[0], *pt]))
            case "S":
                # For smooth cubic, we may need to expand to C depending
                # on the previous command.
                a = _to_str(component.control_locations[0])
                if previous_type != "S":
                    output_path.append(SvgItem.make(["C", *ctrl[0], *a, *pt]))
                else:
                    output_path.append(SvgItem.make(["S", *a, *pt]))
            case "Q":
                output_path.append(SvgItem.make(["Q", *ctrl[0], *pt]))
            case "T":
                # For smooth quadratic, we may need to expand to Q.
                if previous_type != "T":
                    a = _to_str(component.control_locations[0])
                    output_path.append(SvgItem.make(["Q", *a, *pt]))
                else:
                    output_path.append(SvgItem.make(["T", *pt]))
            case "A":
                # Reverse arc: keep radii/angle/large-arc, flip sweep, swap endpoints.
                vals = [str(v) for v in component.values[:4]]
                sweep = str(1 - component.values[4])
                output_path.append(SvgItem.make(["A", *vals, sweep, *pt]))
            case _:
                # Unsupported/unknown types are ignored silently.
                pass

        previous_type = component_type

    if is_closed:
        output_path.append(SvgItem.make(["Z"]))

    new_svg.path = [*path[:start], *output_path, *path[end:]]
    new_svg.refresh_absolute_positions()

    # Restore the following item’s relativity if needed.
    if is_before_relative:
        new_svg.path[start + len(output_path)].relative = True

    # Optimize the new path to keep representation compact.
    return optimize_path(
        new_svg,
        remove_useless_commands=True,
        use_shorthands=True,
    )


def optimize_relative_absolute(svg: SvgPath) -> SvgPath:
    """
    Optimize the relative/absolute representation of a path.

    Each command is toggled between relative and absolute form, and the
    representation that yields a shorter minified path string is kept.

    :param svg: Input path.

    :returns:
        A new path with possibly changed relative/absolute commands.
        Geometry is preserved; only representation changes.
    """
    new_svg = svg.clone()
    length: int = len(new_svg.as_string(4, True))
    origin: Final[Point] = Point(0, 0)

    for i, comp in enumerate(new_svg.path):
        previous = new_svg.path[i - 1] if i > 0 else None
        if comp.get_type(True) == "Z":
            continue

        # Toggle relativity and test string length.
        comp.relative = not comp.relative
        new_length = len(new_svg.as_string(4, True))
        if new_length < length:
            length = new_length
            comp.refresh(origin, previous)
        else:
            comp.relative = not comp.relative

    return new_svg


def optimize_path(
    svg: SvgPath,
    *,
    remove_useless_commands: bool = False,
    remove_orphan_dots: bool = False,
    use_shorthands: bool = False,
    use_horizontal_and_vertical_lines: bool = False,
    use_relative_absolute: bool = False,
    use_reverse: bool = False,
    use_close_path: bool = False,
) -> SvgPath:
    """
    Optimize the representation of an SVG path.

    The function can apply several optional passes that can be enabled using
    the parameters.

    :param svg:
        Input path.
    :param remove_useless_commands:
        Remove redundant ``M``/``Z`` commands and degenerate ``L``/``H``/``V`` segments.
    :param remove_orphan_dots:
        Remove empty closed subpaths (``M`` immediately followed by ``Z``).
        This can affect stroked paths.
    :param use_shorthands:
        Convert eligible ``C``/``Q`` segments to ``S``/``T`` where possible.
    :param use_horizontal_and_vertical_lines:
        Replace ``L`` with ``H`` or ``V`` where possible.
    :param use_relative_absolute:
        Choose between relative and absolute commands per segment to minimize size.
    :param use_reverse:
        Reverse the path direction if that yields a shorter minified representation.
        This can affect stroked paths.
    :param use_close_path:
        Convert final line segments that return to start into ``Z``.
        This can affect stroked paths.

    :returns: A new, possibly shorter, but geometrically equivalent path.
    """
    new_svg = svg.clone()
    path = new_svg.path
    origin: Final[Point] = Point(0, 0)
    initial_pt = Point(0, 0)

    i = 1
    while i < len(path):
        c0 = path[i - 1]
        c1 = path[i]
        c0type = c0.get_type(True)
        c1type = c1.get_type(True)

        if c0type == "M":
            initial_pt = c0.target_location()

        if remove_useless_commands:
            if c0type == "M" and c1type == "M":
                c1.relative = False
                del path[i - 1]
                i -= 1
                continue
            if c0type == "Z" and c1type == "Z":
                del path[i]
                i -= 1
                continue
            if c0type == "Z" and c1type == "M":
                tg = c0.target_location()
                if tg.x == c1.absolute_points[0].x and tg.y == c1.absolute_points[0].y:
                    del path[i]
                    i -= 1
                    continue
            if c1type in ("L", "V", "H"):
                tg = c1.target_location()
                if tg.x == c1.previous_point.x and tg.y == c1.previous_point.y:
                    del path[i]
                    i -= 1
                    continue

        if remove_orphan_dots:
            if c0type == "M" and c1type == "Z":
                del path[i]
                i -= 1
                continue

        if use_horizontal_and_vertical_lines:
            if c1type == "L":
                tg = c1.target_location()
                if tg.x == c1.previous_point.x:
                    path[i] = SvgItem.make_from(c1, c0, "V")
                    i += 1
                    continue
                if tg.y == c1.previous_point.y:
                    path[i] = SvgItem.make_from(c1, c0, "H")
                    i += 1
                    continue

        if use_shorthands:
            if c0type in ("Q", "T") and c1type == "Q":
                pt = _to_str(path[i].target_location())
                candidate = SvgItem.make(["T", *pt])
                candidate.refresh(origin, c0)
                ctrl = candidate.control_locations
                if (
                    ctrl[0].x == c1.absolute_points[0].x
                    and ctrl[0].y == c1.absolute_points[0].y
                ):
                    path[i] = candidate

            if c0type in ("C", "S") and c1type == "C":
                pt = _to_str(path[i].target_location())
                ctrl = _to_str(path[i].absolute_points[1])
                candidate = SvgItem.make(["S", *ctrl, *pt])
                candidate.refresh(origin, c0)
                ctrl2 = candidate.control_locations
                if (
                    ctrl2[0].x == c1.absolute_points[0].x
                    and ctrl2[0].y == c1.absolute_points[0].y
                ):
                    path[i] = candidate

            if c0type not in ("C", "S") and c1type == "C":
                if (
                    c1.previous_point.x == c1.absolute_points[0].x
                    and c1.previous_point.y == c1.absolute_points[0].y
                ):
                    pt = _to_str(c1.target_location())
                    ctrl = _to_str(c1.absolute_points[1])
                    path[i] = SvgItem.make(["S", *ctrl, *pt])
                    path[i].refresh(origin, c0)

        if use_close_path:
            if c1type in ("L", "H", "V"):
                target = c1.target_location()
                if initial_pt.x == target.x and initial_pt.y == target.y:
                    path[i] = SvgItem.make(["Z"])
                    path[i].refresh(initial_pt, c0)

        i += 1

    if remove_useless_commands or remove_orphan_dots:
        if len(path) > 0 and path[-1].get_type(True) == "M":
            del path[-1]

        # With remove_useless_commands, links to previous items may become dirty:
        new_svg.refresh_absolute_positions()

    if use_relative_absolute:
        new_svg = optimize_relative_absolute(new_svg)

    if use_reverse:
        length = len(new_svg.as_string(4, True))
        non_reversed = new_svg.clone()
        new_svg = reverse_path(new_svg)
        if use_relative_absolute:
            new_svg = optimize_relative_absolute(new_svg)
        after_length = len(new_svg.as_string(4, True))
        if after_length >= length:
            new_svg = non_reversed

    return new_svg
