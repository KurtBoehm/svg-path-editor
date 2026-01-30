# This file is part of https://github.com/KurtBoehm/svg-path-editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from decimal import localcontext
from typing import Final

from svg_path_editor import (
    Point,
    SvgPath,
    change_path_origin,
    optimize_path,
    reverse_path,
)
from svg_path_editor.svg import QuadraticBezierCurveTo

base_svg: Final = SvgPath("M-15 14s5 7.5 15 7.5 15-7.5 15-7.5 z")
base: Final = "M -15 14 s 5 7.5 15 7.5 s 15 -7.5 15 -7.5 z"


def test_convert_to_str() -> None:
    """String conversions with and without minification."""

    # Plain string conversion
    assert str(base_svg) == base

    # Custom decimals and minified output
    ref = "M-15 14s5 7.5 15 7.5 15-7.5 15-7.5z"
    assert base_svg.as_string(decimals=1, minify=True) == ref
    assert f"{base_svg:m.1}" == ref
    assert f"{base_svg:.1m}" == ref


def test_geometric_transformations_mutating() -> None:
    """In-place geometric transformations."""

    path = base_svg.clone()

    path.scale(kx=2, ky=2)
    assert str(path) == "M -30 28 s 10 15 30 15 s 30 -15 30 -15 z"

    path.translate(dx=1, dy=0.5)
    assert str(path) == "M -29 28.5 s 10 15 30 15 s 30 -15 30 -15 z"

    path.rotate(ox=0, oy=0, degrees=90)
    assert str(path) == "M -28.5 -29 s -15 10 -15 30 s 15 30 15 30 z"


def test_geometric_transformations_nonmutating() -> None:
    """Out-of-place geometric transformations."""

    path = base_svg.scaled(kx=2, ky=2)
    assert str(base_svg) == base
    assert str(path) == "M -30 28 s 10 15 30 15 s 30 -15 30 -15 z"

    path = base_svg.translated(dx=1, dy=0.5)
    assert str(base_svg) == base
    assert str(path) == "M -14 14.5 s 5 7.5 15 7.5 s 15 -7.5 15 -7.5 z"

    path = base_svg.rotated(ox=0, oy=0, degrees=90)
    assert str(base_svg) == base
    assert str(path) == "M -14 -15 s -7.5 5 -7.5 15 s 7.5 15 7.5 15 z"


def test_absolute_relative() -> None:
    """Convert between absolute and relative command representations."""

    path = base_svg.clone()
    absolute = "M -15 14 S -10 21.5 0 21.5 S 15 14 15 14 Z"
    relative = "m -15 14 s 5 7.5 15 7.5 s 15 -7.5 15 -7.5 z"

    # Setting relative=False mutates the path in place
    path.relative = False
    assert str(path) == absolute
    assert not path.relative

    # `with_relative` is out-of-place; internally it sets `relative` on a clone
    relative_svg = path.with_relative(True)
    assert str(path) == absolute
    assert str(relative_svg) == relative
    assert relative_svg.relative


def test_reverse() -> None:
    """Reverse path out-of-place."""

    path = reverse_path(base_svg)
    assert str(path) == "M 15 14 S 10 21.5 0 21.5 S -15 14 -15 14 Z"
    assert str(base_svg) == base


def test_change_path_origin() -> None:
    """Change the origin of the path out-of-place."""

    path = change_path_origin(base_svg, new_origin_index=2)
    assert str(path) == "M 0 21.5 c 10 0 15 -7.5 15 -7.5 L -15 14 s 5 7.5 15 7.5"
    assert str(base_svg) == base


def test_optimize_path() -> None:
    """Optimize a path out-of-place."""

    # All options default to False; here we enable all of them.
    path = optimize_path(
        base_svg,
        # Remove redundant M/Z or degenerate L/H/V.
        remove_useless_commands=True,
        # Remove empty closed subpaths (M immediately followed by Z).
        remove_orphan_dots=True,
        # Convert eligible C/Q to S/T.
        use_shorthands=True,
        # Replace L with H/V where possible.
        use_horizontal_and_vertical_lines=True,
        # Choose relative/absolute per command to minimize size.
        use_relative_absolute=True,
        # Try reversing path direction if it reduces output length.
        # This may change the appearance of stroked paths!
        use_reverse=True,
        # Convert final line segments that return to start into Z.
        # This may change the appearance of stroked paths!
        use_close_path=True,
    )

    verb = "M -15 14 s 5 7.5 15 7.5 S 15 14 15 14 z"
    mini = "M-15 14s5 7.5 15 7.5S15 14 15 14z"

    assert str(path) == verb
    assert path.as_string(minify=True) == mini
    assert f"{path:m}" == mini
    assert str(base_svg) == base


def test_path_modification_api() -> None:
    """
    Path-level modifications: ``clone``, ``remove``, ``insert``, ``change_type``,
    ``set_location``.
    """

    path = SvgPath("M0 0L10 0V10Z")

    # Clone
    clone = path.clone()
    assert str(clone) == "M 0 0 L 10 0 V 10 Z"

    # Remove the `L` command
    path.remove(path.path[1])
    assert str(path) == "M 0 0 V 10 Z"

    # Insert quadratic Bézier curve where the `L` command was
    path.insert(1, QuadraticBezierCurveTo([5, -5, 10, 0], relative=False))
    assert str(path) == "M 0 0 Q 5 -5 10 0 V 10 Z"

    # Change type from `V` to `L`
    path.change_type(2, "L")
    assert str(path) == "M 0 0 Q 5 -5 10 0 L 10 10 Z"

    # Move a particular point
    path.set_location(path.target_locations[-2], to=Point(5, 10))
    assert str(path) == "M 0 0 Q 5 -5 10 0 L 5 10 Z"

    # The clone is unaffected
    assert str(clone) == "M 0 0 L 10 0 V 10 Z"


def test_decimal_based_geometry() -> None:
    """Decimal-based geometry: rotation precision and formatting."""

    base = SvgPath("M0 0h10v10z")

    rotated = base.rotated(0, 0, -45)
    expected = (
        "M 0 0 l 7.071067811865475244008443621 -7.071067811865475244008443621 "
        "l 7.071067811865475244008443621 7.071067811865475244008443621 z"
    )
    assert str(rotated) == expected

    assert f"{rotated:.5}" == "M 0 0 l 7.07107 -7.07107 l 7.07107 7.07107 z"


def test_decimal_based_geometry_localcontext() -> None:
    """Decimal context can lower precision while preserving printed result."""

    base = SvgPath("M0 0h10v10z")

    with localcontext() as ctx:
        ctx.prec = 6
        rotated = base.rotated(0, 0, -45)
        assert str(rotated) == "M 0 0 l 7.07107 -7.07107 l 7.07107 7.07107 z"
