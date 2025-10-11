# This file is part of https://github.com/KurtBoehm/svg_path_editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from .path_operations import optimize_path
from .sub_path_bounds import get_sub_path_bounds
from .svg import SvgItem, SvgPath


def change_path_origin(
    svg: SvgPath, new_origin_index: int, subpath: bool | None = None
) -> None:
    if len(svg.path) <= new_origin_index or new_origin_index == 0:
        return

    start, end = get_sub_path_bounds(svg, new_origin_index if subpath else None)
    segment_len = end - start

    is_before_relative = end < len(svg.path) and svg.path[end].relative
    if is_before_relative:
        svg.path[end].set_relative(False)

    new_first_item = svg.path[new_origin_index]
    new_last_item = svg.path[new_origin_index - 1]

    match new_first_item.get_type().upper():
        # Shorthands must be converted to be used as origin
        case "S":
            svg.change_type(new_first_item, "c" if new_first_item.relative else "C")
        case "T":
            svg.change_type(new_first_item, "q" if new_first_item.relative else "Q")
        case _:
            pass

    for i in range(new_origin_index, end):
        # Z that comes after new origin must be converted to L, up to the first M
        item = svg.path[i]
        match item.get_type().upper():
            case "Z":
                svg.change_type(item, "L")
            case "M":
                break
            case _:
                pass

    output_path: list[SvgItem] = []
    sub_path = svg.path[start:end]
    first_item = sub_path[0]
    last_item = sub_path[segment_len - 1]

    for i in range(segment_len):
        if i == 0:
            new_origin = new_last_item.target_location()
            item = SvgItem.make(["M", str(new_origin.x), str(new_origin.y)])
            output_path.append(item)

        if new_origin_index + i == start + segment_len:
            # We may be able to remove the initial M if last item has the same target
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
                    # We can remove initial M if there is no Z in the following subpath
                    continue

        output_path.append(sub_path[(new_origin_index - start + i) % segment_len])

    svg.path = [*svg.path[:start], *output_path, *svg.path[end:]]
    svg.refresh_absolute_positions()

    if is_before_relative:
        svg.path[start + len(output_path)].set_relative(True)

    optimize_path(
        svg,
        remove_useless_commands=True,
        use_shorthands=True,
        use_close_path=True,
    )
