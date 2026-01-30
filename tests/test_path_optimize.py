# This file is part of https://github.com/KurtBoehm/svg-path-editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from svg_path_editor import SvgPath, optimize_path

useless_moves_section = (
    "M 1 1 M 2 1 L 3 2 L 4 2 L 4 0 M 6 0 Z L 7 1 L 5 2 Z M 6 0 L 9 1"
)
non_simplifiable = "M 7 1 L 9 2 L 7 4 Z"
useless_draws_section = "Z Z M 7 4 L 7 4 L 4 5"
curve_section = "C 3 6 5 6 4 7 C 3 8 3 7 2 8 C 0 9 3 10 2 10 C 0 10 1 11 0 12"
bezier_section = "Q -1 13 2 14 Q 5 15 2 17 Q 4 17 4 19 Z"

test = (
    f"{useless_moves_section}"
    f" {non_simplifiable}"
    f" {useless_draws_section}"
    f" {curve_section}"
    f" {bezier_section}"
)


def test_optimize_path_handles_relative_components() -> None:
    """Remove useless relative components."""
    ante = "M 3 2 m 1 0 m 0 1 m 0 1 l 1 1"
    post = "M 4 4 l 1 1"

    ante_svg = SvgPath(ante)
    post_svg = optimize_path(
        ante_svg,
        remove_useless_commands=True,
    )

    # Original must not be mutated
    assert str(ante_svg) == ante
    assert str(post_svg) == post


def test_optimize_path_handles_pathologic_paths() -> None:
    """Handle malformed or degenerate paths."""
    ante = "M 4 19 L 2 1 M 1 1"
    post = "M 4 19 L 2 1"

    ante_svg = SvgPath(ante)
    post_svg = optimize_path(
        ante_svg,
        use_reverse=True,
        remove_useless_commands=True,
        use_horizontal_and_vertical_lines=True,
        use_relative_absolute=True,
        use_shorthands=True,
    )

    # Original must not be mutated
    assert str(ante_svg) == ante
    assert str(post_svg) == post

    # Empty input remains empty.
    empty = ""

    empty_ante_svg = SvgPath(empty)
    empty_post_svg = optimize_path(
        empty_ante_svg,
        use_reverse=True,
        remove_useless_commands=True,
        use_horizontal_and_vertical_lines=True,
        use_relative_absolute=True,
        use_shorthands=True,
    )

    assert str(empty_ante_svg) == empty
    assert str(empty_post_svg) == empty


def test_optimize_path_removes_useless_components() -> None:
    """Remove useless moves/draws."""
    post = (
        "M 2 1 L 3 2 L 4 2 L 4 0 M 6 0 Z L 7 1 L 5 2 Z L 9 1 "
        f"{non_simplifiable} "
        "M 7 4 L 4 5 "
        f"{curve_section} "
        f"{bezier_section}"
    )

    ante_svg = SvgPath(test)
    post_svg = optimize_path(
        ante_svg,
        remove_useless_commands=True,
    )

    # Original must not be mutated
    assert str(ante_svg) == test
    assert str(post_svg) == post


def test_optimize_path_uses_shorthands() -> None:
    """Prefer shorthand ``C``/``S`` and ``Q``/``T`` commands."""
    post = (
        f"{useless_moves_section} "
        f"{non_simplifiable} "
        f"{useless_draws_section} "
        "C 3 6 5 6 4 7 S 3 7 2 8 C 0 9 3 10 2 10 C 0 10 1 11 0 12 "
        "Q -1 13 2 14 T 2 17 Q 4 17 4 19 Z"
    )

    ante_svg = SvgPath(test)
    post_svg = optimize_path(
        ante_svg,
        use_shorthands=True,
    )

    # Original must not be mutated
    assert str(ante_svg) == test
    assert str(post_svg) == post


def test_optimize_path_uses_horizontal_and_vertical_lines() -> None:
    """Replace eligible ``L`` commands by ``H``/``V``."""
    post = (
        "M 1 1 M 2 1 L 3 2 H 4 V 0 M 6 0 Z L 7 1 L 5 2 Z M 6 0 L 9 1 "
        f"{non_simplifiable} "
        "Z Z M 7 4 V 4 L 4 5 "
        f"{curve_section} "
        f"{bezier_section}"
    )

    ante_svg = SvgPath(test)
    post_svg = optimize_path(
        ante_svg,
        use_horizontal_and_vertical_lines=True,
    )

    # Original must not be mutated
    assert str(ante_svg) == test
    assert str(post_svg) == post


def test_optimize_path_uses_relative_and_absolute() -> None:
    """Switch between relative and absolute forms to minimize representation size."""
    post = (
        f"{useless_moves_section} "
        f"{non_simplifiable} "
        f"{useless_draws_section} "
        "C 3 6 5 6 4 7 C 3 8 3 7 2 8 c -2 1 1 2 0 2 c -2 0 -1 1 -2 2 "
        "q -1 1 2 2 q 3 1 0 3 q 2 0 2 2 Z"
    )

    ante_svg = SvgPath(test)
    post_svg = optimize_path(
        ante_svg,
        use_relative_absolute=True,
    )

    # Original must not be mutated
    assert str(ante_svg) == test
    assert str(post_svg) == post


def test_optimize_path_uses_reverse() -> None:
    """Reverse path direction when enabled."""
    post = (
        "M 4 19 Q 4 17 2 17 Q 5 15 2 14 T 0 12 "
        "C 1 11 0 10 2 10 C 3 10 0 9 2 8 C 3 7 3 8 4 7 S 3 6 4 5 L 7 4 Z "
        "M 7 1 Z "
        "M 7 4 L 9 2 L 7 1 Z M 9 1 L 6 0 M 5 2 L 7 1 L 6 0 Z "
        "M 6 0 Z "
        "M 4 0 L 4 2 L 3 2 L 2 1"
    )

    ante_svg = SvgPath(test)
    post_svg = optimize_path(
        ante_svg,
        use_reverse=True,
    )

    # Original must not be mutated
    assert str(ante_svg) == test
    assert str(post_svg) == post


def test_optimize_path_uses_close_path() -> None:
    """Convert explicit lines back to the start point into ``Z`` commands."""
    ante = "M 5 5 L 8 5 L 5 2 V 5 L 5 7 L 3 5 H 5 L 8 7 L 7 8 L 5 5"
    post = "M 5 5 L 8 5 L 5 2 Z L 5 7 L 3 5 Z L 8 7 L 7 8 Z"

    ante_svg = SvgPath(ante)
    post_svg = optimize_path(
        ante_svg,
        use_close_path=True,
    )

    # Original must not be mutated
    assert str(ante_svg) == ante
    assert str(post_svg) == post


def test_optimize_path_removes_orphan_dots() -> None:
    """Remove paths consisting of ``M``/``m`` followed directly by ``Z``/``z``."""
    ante = "M 0 0 Z"
    post = ""

    ante_svg = SvgPath(ante)
    post_svg = optimize_path(
        ante_svg,
        remove_orphan_dots=True,
    )

    # Original must not be mutated
    assert str(ante_svg) == ante
    assert str(post_svg) == post


def test_optimize_path_all_options_together() -> None:
    """Check all optimization flags together."""
    post = (
        "M 2 1 L 3 2 H 4 V 0 M 6 0 Z L 7 1 L 5 2 Z L 9 1 "
        f"{non_simplifiable} "
        "M 7 4 L 4 5 "
        "C 3 6 5 6 4 7 S 3 7 2 8 c -2 1 1 2 0 2 c -2 0 -1 1 -2 2 "
        "q -1 1 2 2 t 0 3 q 2 0 2 2 Z"
    )

    ante_svg = SvgPath(test)
    post_svg = optimize_path(
        ante_svg,
        use_reverse=True,
        remove_useless_commands=True,
        use_horizontal_and_vertical_lines=True,
        use_relative_absolute=True,
        use_shorthands=True,
    )

    # Original must not be mutated
    assert str(ante_svg) == test
    assert str(post_svg) == post
