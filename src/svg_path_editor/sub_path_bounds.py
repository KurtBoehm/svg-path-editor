# This file is part of https://github.com/KurtBoehm/svg_path_editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from .svg import SvgPath


def find_previous_move_to(svg: SvgPath, index: int) -> int:
    i = index
    while i > 0 and svg.path[i].get_type(True) != "M":
        i -= 1
    return i


def find_next_move_to(svg: SvgPath, index: int) -> int:
    i = index + 1
    while i < len(svg.path) and svg.path[i].get_type(True) != "M":
        i += 1
    return i


def get_sub_path_bounds(svg: SvgPath, index: int | None = None) -> tuple[int, int]:
    start = 0 if index is None else find_previous_move_to(svg, index)
    end = len(svg.path) if index is None else find_next_move_to(svg, index)
    return start, end
