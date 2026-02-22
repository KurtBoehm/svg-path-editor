# This file is part of https://github.com/KurtBoehm/svg-path-editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from .geometry import Point
from .math import Precision
from .path_change_origin import change_path_origin
from .path_offset import BevelArced, BevelPolygon, bevel_path, offset_path
from .path_operations import optimize_path, reverse_path
from .path_shade import (
    PNG,
    WEBP,
    ImageFormat,
    PathShading,
    lambert_from_angle,
    lambert_shading_base64,
    shade_path,
)
from .svg import SvgItem, SvgPath

__version__ = "3.1.1"

__all__ = [
    "PNG",
    "WEBP",
    "BevelArced",
    "BevelPolygon",
    "ImageFormat",
    "PathShading",
    "Point",
    "Precision",
    "SvgPath",
    "SvgItem",
    "bevel_path",
    "change_path_origin",
    "lambert_from_angle",
    "lambert_shading_base64",
    "offset_path",
    "optimize_path",
    "reverse_path",
    "shade_path",
]
