# This file is part of https://github.com/KurtBoehm/svg_path_editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from .path_change_origin import change_path_origin
from .path_operations import optimize_path, reverse_path
from .svg import Point, SvgItem, SvgPath

__version__ = "3.0.0"

__all__ = [
    "Point",
    "SvgPath",
    "SvgItem",
    "optimize_path",
    "reverse_path",
    "change_path_origin",
]
