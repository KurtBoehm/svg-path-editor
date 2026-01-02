# This file is part of https://github.com/KurtBoehm/svg_path_editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from decimal import Decimal
from typing import final

import pytest

from svg_path_editor import SvgItem, SvgPath, reverse_path


def test_reverse_with_close_path() -> None:
    """Reverse a simple multi-subpath path with ``Z`` commands."""
    ante = "M 5 2 L 9 2 L 9 6 Z L 1 7 L 4 9 Z L 6 9 L 8 7 Z"
    post = "M 8 7 L 6 9 L 5 2 Z M 4 9 L 1 7 L 5 2 Z M 9 6 L 9 2 L 5 2 Z"

    ante_svg = SvgPath(ante)
    post_svg = reverse_path(ante_svg)

    # Original must not be mutated
    assert str(ante_svg) == ante
    assert str(post_svg) == post


def test_reverse_smooth_bezier():
    """Reverse a path containing smooth Bézier curves."""
    ante = "M 10 10 C 20 20 30 20 40 10 S 60 0 70 10 T 60 22.5 T 30 35 Z"
    post = "M 30 35 Q 50 35 60 22.5 T 70 10 C 60 0 50 0 40 10 S 20 20 10 10 Z"

    ante_svg = SvgPath(ante)
    post_svg = reverse_path(ante_svg)

    # Original must not be mutated
    assert str(ante_svg) == ante
    assert str(post_svg) == post

    # Check the control points
    assert [(p.x, p.y) for p in post_svg.control_locations] == [
        (Decimal(50), Decimal(35)),
        (Decimal(70), Decimal(10)),
        (Decimal(60), Decimal(0)),
        (Decimal(50), Decimal(0)),
        (Decimal(30), Decimal(20)),
        (Decimal(20), Decimal(20)),
    ]


def test_reverse_complex_path() -> None:
    """Reverse a complex path mixing curves, arcs, and multiple subpaths."""
    ante = (
        "M 4 8 L 10 1 L 13 0 L 12 3 L 5 9 C 6 10 6 11 7 10 "
        "C 7 11 8 12 7 12 A 1.42 1.42 0 0 1 6 13 "
        "A 5 5 0 0 0 4 10 Q 3.5 9.9 3.5 10.5 T 2 11.8 T 1.2 11 "
        "T 2.5 9.5 T 3 9 A 5 5 90 0 0 0 7 A 1.42 1.42 0 0 1 1 6 "
        "C 1 5 2 6 3 6 C 2 7 3 7 4 8 "
        "M 10 1 L 10 3 L 12 3 L 10.2 2.8 L 10 1 "
        "M 10 8 C 9 7 11 7 12 7 S 14 7 13 8 S 13 9 13 10 Z "
        "M 9 10 L 10 10 L 10 11 "
        "M 11 11 L 12 11 L 12 12 L 10 12 Z "
        "M 14 3 C 14.3333 2.6667 14 2 15 2 C 16 2 15.6667 2.6667 16 3"
    )
    post = (
        "M 16 3 C 15.6667 2.6667 16 2 15 2 S 14.3333 2.6667 14 3 "
        "M 10 12 L 12 12 L 12 11 L 11 11 Z "
        "M 10 11 L 10 10 L 9 10 "
        "M 13 10 C 13 9 12 9 13 8 S 13 7 12 7 S 9 7 10 8 Z "
        "M 10 1 L 10.2 2.8 L 12 3 L 10 3 L 10 1 "
        "M 4 8 C 3 7 2 7 3 6 C 2 6 1 5 1 6 "
        "A 1.42 1.42 0 0 0 0 7 A 5 5 90 0 1 3 9 "
        "Q 3.1 9.5 2.5 9.5 T 1.2 11 T 2 11.8 T 3.5 10.5 T 4 10 "
        "A 5 5 0 0 1 6 13 A 1.42 1.42 0 0 0 7 12 "
        "C 8 12 7 11 7 10 C 6 11 6 10 5 9 "
        "L 12 3 L 13 0 L 10 1 L 4 8"
    )

    ante_svg = SvgPath(ante)
    post_svg = reverse_path(ante_svg)

    # Original must not be mutated
    assert str(ante_svg) == ante
    # There are slight rounding imprecisions
    assert str(post_svg) == post


def test_reverse_handles_shorthands() -> None:
    """Reverse a path using cubic shorthands ``C``/``S``."""
    ante = "M 2 2 C 3 1 5 1 6 2 S 7 5 6 6 C 6 7 3 9 2 6"
    post = "M 2 6 C 3 9 6 7 6 6 C 7 5 7 3 6 2 S 3 1 2 2"

    ante_svg = SvgPath(ante)
    post_svg = reverse_path(ante_svg)

    # Original must not be mutated
    assert str(ante_svg) == ante
    assert str(post_svg) == post


def test_reverse_subpath_only() -> None:
    """Reverse only the subpath containing a given item index."""
    ante = (
        "M 3 4 L 4 4 L 4 5 L 3 5 Z "
        "M 5 5 L 6 4 L 7 4 L 8 5 L 8 6 L 7 7 L 6 7 L 5 6 Z "
        "M 9 6 L 10 6 L 10 7 L 9 7 Z"
    )
    post = (
        "M 3 4 L 4 4 L 4 5 L 3 5 Z "
        "M 5 6 L 6 7 L 7 7 L 8 6 L 8 5 L 7 4 L 6 4 L 5 5 Z "
        "M 9 6 L 10 6 L 10 7 L 9 7 Z"
    )

    ante_svg = SvgPath(ante)
    post_svg = reverse_path(ante_svg, subpath_of_item=8)

    # Original must not be mutated
    assert str(ante_svg) == ante
    assert str(post_svg) == post


def test_reverse_preserves_relative_move_to() -> None:
    """Reverse a subpath while preserving ``m`` commands."""
    ante = (
        "M 3 4 L 4 4 L 4 5 L 3 5 Z "
        "M 5 5 L 6 4 L 7 4 L 8 5 L 8 6 L 7 7 L 6 7 L 5 6 Z "
        "m 9 6 L 10 6 L 10 7 L 9 7 Z"
    )
    post = (
        "M 3 4 L 4 4 L 4 5 L 3 5 Z "
        "M 5 6 L 6 7 L 7 7 L 8 6 L 8 5 L 7 4 L 6 4 L 5 5 Z "
        "m 9 5 L 10 6 L 10 7 L 9 7 Z"
    )

    ante_svg = SvgPath(ante)
    post_svg = reverse_path(ante_svg, subpath_of_item=8)

    # Original must not be mutated
    assert str(ante_svg) == ante
    assert str(post_svg) == post


def test_invalid_item() -> None:
    """Invalid :class:`SvgItem` instances lead to a :class:`ValueError`."""

    @final
    class InvalidItem(SvgItem):
        key = "?"

    svg = SvgPath("")
    svg.path = [InvalidItem([0, 0], relative=False), InvalidItem([0, 0], relative=True)]
    with pytest.raises(ValueError):
        reverse_path(svg)
