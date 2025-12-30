# This file is part of https://github.com/KurtBoehm/svg_path_editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from .path_operations import optimize_path
from .sub_path_bounds import get_sub_path_bounds
from .svg import SvgItem, SvgPath


def change_path_origin(
    svg: SvgPath, new_origin_index: int, subpath: bool | None = None
) -> SvgPath:
    """
    Return a new path where the origin of a (sub)path is moved.

    The command at ``new_origin_index`` becomes the first command of the
    affected subpath segment; all items of that subpath are rotated
    accordingly.
    If ``subpath`` is ``True``, only the subpath containing ``new_origin_index`` is
    transformed; if ``False``/``None``, the whole path is treated as a single segment.

    :param svg: Original path to transform.
    :param new_origin_index:
        Index of the command that should become the new origin within its subpath.
    :param subpath:
        If ``True``, restrict the change to the subpath containing ``new_origin_index``;
        if ``False`` or ``None``, treat the full path segment as one subpath.
    :returns: A new :class:`~svg_path_editor.SvgPath` instance with the
        origin moved and the path representation optimized.
    """
    if len(svg.path) <= new_origin_index or new_origin_index == 0:
        # Nothing to change or invalid index; just return a clone.
        return svg.clone()

    new_svg = svg.clone()
    path = new_svg.path

    start, end = get_sub_path_bounds(new_svg, new_origin_index if subpath else None)
    segment_len = end - start

    is_before_relative = end < len(path) and path[end].relative
    if is_before_relative:
        # Make following item absolute to simplify rewrites.
        path[end].relative = False

    new_first_item = path[new_origin_index]
    new_last_item = path[new_origin_index - 1]

    # Shorthands must be converted to explicit forms before becoming new origin.
    match new_first_item.get_type().upper():
        case "S":
            new_svg.change_type(
                new_first_item,
                "c" if new_first_item.relative else "C",
            )
        case "T":
            new_svg.change_type(
                new_first_item,
                "q" if new_first_item.relative else "Q",
            )
        case _:
            pass

    # Z that comes after new origin must be converted to L, up to the next M.
    for i in range(new_origin_index, end):
        item = path[i]
        match item.get_type().upper():
            case "Z":
                new_svg.change_type(item, "L")
            case "M":
                break
            case _:
                pass

    output_path: list[SvgItem] = []
    sub_path = path[start:end]
    first_item = sub_path[0]
    last_item = sub_path[segment_len - 1]

    for i in range(segment_len):
        if i == 0:
            # Insert a new M at the origin of the previous item.
            new_origin = new_last_item.target_location()
            item = SvgItem.make(["M", str(new_origin.x), str(new_origin.y)])
            output_path.append(item)

        if new_origin_index + i == start + segment_len:
            # We may be able to remove the initial M if last item has the same target.
            tg1 = first_item.target_location()
            tg2 = last_item.target_location()
            if tg1.x == tg2.x and tg1.y == tg2.y:
                following_m = next(
                    (
                        idx
                        for idx, it in enumerate(sub_path)
                        if idx > 0 and it.get_type().upper() == "M"
                    ),
                    -1,
                )
                first_z = next(
                    (
                        idx
                        for idx, it in enumerate(sub_path)
                        if it.get_type().upper() == "Z"
                    ),
                    -1,
                )
                if first_z == -1 or (following_m != -1 and first_z > following_m):
                    # We can remove initial M if there is no Z in the following subpath.
                    continue

        output_path.append(sub_path[(new_origin_index - start + i) % segment_len])

    new_svg.path = [*path[:start], *output_path, *path[end:]]
    new_svg.refresh_absolute_positions()

    if is_before_relative:
        # Restore relativity of the first item after the modified segment.
        new_svg.path[start + len(output_path)].relative = True

    # Optimize representation of the resulting path.
    return optimize_path(
        new_svg,
        remove_useless_commands=True,
        use_shorthands=True,
        use_close_path=True,
    )
