# This file is part of https://github.com/KurtBoehm/svg_path_editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from .sub_path_bounds import get_sub_path_bounds
from .svg import Point, SvgItem, SvgPath


def to_str(pt: Point) -> tuple[str, str]:
    return str(pt.x), str(pt.y)


def reverse_path(svg: SvgPath, subpath_of_item: int | None = None) -> None:
    start, end = get_sub_path_bounds(svg, subpath_of_item)

    if end - start <= 1:
        return

    is_before_relative = end < len(svg.path) and svg.path[end].relative
    if is_before_relative:
        svg.path[end].set_relative(False)

    sub_path = svg.path[start:end]
    output_path: list[SvgItem] = []
    reversed_path = list(reversed(sub_path))[:-1]

    start_point = reversed_path[0].target_location()
    output_path.append(SvgItem.make(["M", *to_str(start_point)]))
    previous_type = ""
    is_closed = False

    for component in reversed_path:
        pt = to_str(component.previous_point)
        ctrl = [to_str(p) for p in component.absolute_points]
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
                output_path.append(SvgItem.make(["C", *ctrl[1], *ctrl[0], *pt]))
            case "S":
                a = to_str(component.control_locations()[0])
                if previous_type != "S":
                    output_path.append(SvgItem.make(["C", *ctrl[0], *a, *pt]))
                else:
                    output_path.append(SvgItem.make(["S", *a, *pt]))
            case "Q":
                output_path.append(SvgItem.make(["Q", *ctrl[0], *pt]))
            case "T":
                if previous_type != "T":
                    a = to_str(component.control_locations()[0])
                    output_path.append(SvgItem.make(["Q", *a, *pt]))
                else:
                    output_path.append(SvgItem.make(["T", *pt]))
            case "A":
                vals = [str(v) for v in component.values[:4]]
                sweep = str(1 - component.values[4])
                output_path.append(SvgItem.make(["A", *vals, sweep, *pt]))
            case _:
                pass

        previous_type = component_type

    if is_closed:
        output_path.append(SvgItem.make(["Z"]))

    svg.path = [*svg.path[:start], *output_path, *svg.path[end:]]
    svg.refresh_absolute_positions()

    if is_before_relative:
        svg.path[start + len(output_path)].set_relative(True)

    optimize_path(svg, remove_useless_commands=True, use_shorthands=True)


def optimize_relative_absolute(svg: SvgPath) -> None:
    length = len(svg.as_string(4, True))
    o = Point(0, 0)
    for i in range(len(svg.path)):
        previous = svg.path[i - 1] if i > 0 else None
        comp = svg.path[i]
        if comp.get_type(True) == "Z":
            continue
        comp.set_relative(not comp.relative)
        new_length = len(svg.as_string(4, True))
        if new_length < length:
            length = new_length
            comp.refresh(o, previous)
        else:
            comp.set_relative(not comp.relative)


def optimize_path(
    svg: SvgPath,
    *,
    remove_useless_commands: bool = False,
    remove_orphan_dots: bool = False,  # Can have an impact on stroked paths
    use_shorthands: bool = False,
    use_horizontal_and_vertical_lines: bool = False,
    use_relative_absolute: bool = False,
    use_reverse: bool = False,
    use_close_path: bool = False,
) -> None:
    path = svg.path
    o = Point(0, 0)
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
                c1.set_relative(False)
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
                pt = to_str(path[i].target_location())
                candidate = SvgItem.make(["T", *pt])
                candidate.refresh(o, c0)
                ctrl = candidate.control_locations()
                if (
                    ctrl[0].x == c1.absolute_points[0].x
                    and ctrl[0].y == c1.absolute_points[0].y
                ):
                    path[i] = candidate

            if c0type in ("C", "S") and c1type == "C":
                pt = to_str(path[i].target_location())
                ctrl = to_str(path[i].absolute_points[1])
                candidate = SvgItem.make(["S", *ctrl, *pt])
                candidate.refresh(o, c0)
                ctrl2 = candidate.control_locations()
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
                    pt = to_str(c1.target_location())
                    ctrl = to_str(c1.absolute_points[1])
                    path[i] = SvgItem.make(["S", *ctrl, *pt])
                    path[i].refresh(o, c0)

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
        svg.refresh_absolute_positions()

    if use_relative_absolute:
        optimize_relative_absolute(svg)

    if use_reverse:
        length = len(svg.as_string(4, True))
        non_reversed = list(svg.path)
        reverse_path(svg)
        if use_relative_absolute:
            optimize_relative_absolute(svg)
        after_length = len(svg.as_string(4, True))
        if after_length >= length:
            svg.path = non_reversed
