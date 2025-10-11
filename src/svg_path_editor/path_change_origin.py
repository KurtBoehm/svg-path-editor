# This file is part of https://github.com/KurtBoehm/svg_path_editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from .path_operations import optimize_path
from .svg import SvgItem, SvgPath


def change_path_origin(svg: SvgPath, new_origin_index: int) -> None:
    if len(svg.path) <= new_origin_index or new_origin_index == 0:
        return

    output_path: list[SvgItem] = []
    path_len = len(svg.path)
    new_first_item = svg.path[new_origin_index]
    new_last_item = svg.path[new_origin_index - 1]
    first_item = svg.path[0]
    last_item = svg.path[path_len - 1]

    match new_first_item.get_type().upper():
        # Shorthands must be converted to be used as origin
        case "S":
            svg.change_type(new_first_item, "c" if new_first_item.relative else "C")
        case "T":
            svg.change_type(new_first_item, "q" if new_first_item.relative else "Q")
        case _:
            pass

    for i in range(new_origin_index, path_len):
        # Z that comes after new origin must be converted to L, up to the first M
        item = svg.path[i]
        match item.get_type().upper():
            case "Z":
                svg.change_type(item, "L")
            case "M":
                break
            case _:
                pass

    for i in range(path_len):
        if i == 0:
            new_origin = new_last_item.target_location()
            item = SvgItem.make(["M", str(new_origin.x), str(new_origin.y)])
            output_path.append(item)

        if new_origin_index + i == path_len:
            # We may be able to remove the initial M if last item has the same target
            tg1 = first_item.target_location()
            tg2 = last_item.target_location()
            if tg1.x == tg2.x and tg1.y == tg2.y:
                following_m = -1
                for idx, it in enumerate(svg.path):
                    if idx > 0 and it.get_type().upper() == "M":
                        following_m = idx
                        break
                first_z = -1
                for idx, it in enumerate(svg.path):
                    if it.get_type().upper() == "Z":
                        first_z = idx
                        break
                if first_z == -1 or (following_m != -1 and first_z > following_m):
                    # We can remove inital M if there is no Z in the following subpath
                    continue

        output_path.append(svg.path[(new_origin_index + i) % path_len])

    svg.path = output_path
    svg.refresh_absolute_positions()
    optimize_path(svg, remove_useless_components=True, use_shorthands=True)
