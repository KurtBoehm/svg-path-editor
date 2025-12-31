import pytest

from svg_path_editor import SvgPath, change_path_origin


def test_change_path_origin_basic_closed_paths() -> None:
    """Change origin of a simple closed path."""
    ante = "M 2 2 L 6 2 L 2 5 L 2 2 L 5 0 L 5 -1 L 1 -2 L -1 0 L 2 2"
    post = "M 1 -2 L -1 0 L 2 2 L 6 2 L 2 5 L 2 2 L 5 0 L 5 -1 Z"

    ante_svg = SvgPath(ante)
    post_svg = change_path_origin(ante_svg, new_origin_index=7)

    # Original must not be mutated
    assert str(ante_svg) == ante
    assert str(post_svg) == post


def test_change_path_origin_subpath() -> None:
    """Change origin within a specific subpath only."""
    ante = (
        "M 3 4 L 4 4 L 4 5 L 3 5 Z "
        "M 5 5 L 6 4 L 7 4 L 8 5 L 8 6 L 7 7 L 6 7 L 5 6 Z "
        "M 9 6 L 10 6 L 10 7 L 9 7 Z"
    )
    post = (
        "M 3 4 L 4 4 L 4 5 L 3 5 Z "
        "M 7 4 L 8 5 L 8 6 L 7 7 L 6 7 L 5 6 L 5 5 L 6 4 Z "
        "M 9 6 L 10 6 L 10 7 L 9 7 Z"
    )

    ante_svg = SvgPath(ante)
    post_svg = change_path_origin(ante_svg, new_origin_index=8, subpath=True)

    # Original must not be mutated
    assert str(ante_svg) == ante
    assert str(post_svg) == post


def test_change_path_origin_preserve_relative_move_to() -> None:
    """Changing origin in a subpath preserves ``m`` in unrelated subpaths."""
    ante = (
        "M 3 4 L 4 4 L 4 5 L 3 5 Z "
        "M 5 5 L 6 4 L 7 4 L 8 5 L 8 6 L 7 7 L 6 7 L 5 6 Z "
        "m 9 6 L 10 6 L 10 7 L 9 7 Z"
    )
    post = (
        "M 3 4 L 4 4 L 4 5 L 3 5 Z "
        "M 7 4 L 8 5 L 8 6 L 7 7 L 6 7 L 5 6 L 5 5 L 6 4 Z "
        "m 7 7 L 10 6 L 10 7 L 9 7 Z"
    )

    ante_svg = SvgPath(ante)
    post_svg = change_path_origin(ante_svg, new_origin_index=8, subpath=True)

    # Original must not be mutated
    assert str(ante_svg) == ante
    assert str(post_svg) == post


@pytest.mark.parametrize(("new_origin_index",), [(0,), (99,)])
def test_change_path_origin_out_of_bounds_or_zero(new_origin_index: int) -> None:
    """Out-of-bounds or zero origin index leaves the path unchanged."""
    path = "M 2 2 L 6 2 L 2 6"

    ante_svg = SvgPath(path)
    post_svg = change_path_origin(ante_svg, new_origin_index=new_origin_index)

    assert str(ante_svg) == path
    assert str(post_svg) == path


def test_change_path_origin_remove_initial_move() -> None:
    """
    Initial ``M`` may be removed when moving origin if there is no closing ``Z``
    that would be affected.
    """
    ante = (
        "M 2 -3 L 3 -3 L 2 -2 L 2 -3 M 3 -2 L 4 -2 L 3 -1 Z M 2 -3 L 2 -5 L 4 -4 L 2 -3"
    )
    post = (
        "M 2 -5 L 4 -4 L 2 -3 L 3 -3 L 2 -2 L 2 -3 M 3 -2 L 4 -2 L 3 -1 Z M 2 -3 L 2 -5"
    )

    ante_svg = SvgPath(ante)
    post_svg = change_path_origin(ante_svg, new_origin_index=10)

    # Original must not be mutated
    assert str(ante_svg) == ante
    assert str(post_svg) == post


def test_change_path_origin_keep_initial_move_if_z_follows() -> None:
    """Initial ``M`` must be preserved when a ``Z`` later closes the subpath."""
    ante = "M 2 2 L 6 2 L 2 5 Z L 5 0 L 5 -1 L 1 -2 L -1 0 L 2 2"
    post = "M 1 -2 L -1 0 L 2 2 M 2 2 L 6 2 L 2 5 Z L 5 0 L 5 -1 L 1 -2"

    ante_svg = SvgPath(ante)
    post_svg = change_path_origin(ante_svg, new_origin_index=7)

    # Original must not be mutated
    assert str(ante_svg) == ante
    assert str(post_svg) == post


def test_change_path_origin_convert_s_to_c() -> None:
    """
    Shorthand ``S``/``s`` commands become explicit ``C``/``c`` when moved to origin.
    """
    # Absolute S → C
    ante = "M 5 5 L 10 5 C 12 5 12 6 12 7 S 13 11 12 10 Z"
    post = "M 12 7 C 12 8 13 11 12 10 L 5 5 L 10 5 C 12 5 12 6 12 7"

    ante_svg = SvgPath(ante)
    post_svg = change_path_origin(ante_svg, new_origin_index=3)

    # Original must not be mutated
    assert str(ante_svg) == ante
    assert str(post_svg) == post

    # Relative s → c
    ante = "M 5 5 L 10 5 C 12 5 12 6 12 7 s 1 4 0 3 Z"
    post = "M 12 7 c 0 1 1 4 0 3 L 5 5 L 10 5 C 12 5 12 6 12 7"

    ante_svg = SvgPath(ante)
    post_svg = change_path_origin(ante_svg, new_origin_index=3)

    # Original must not be mutated
    assert str(ante_svg) == ante
    assert str(post_svg) == post


def test_change_path_origin_convert_t_to_q() -> None:
    """
    Shorthand ``T``/``t`` commands become explicit ``Q``/``q`` when moved to origin.
    """
    # Absolute T → Q
    ante = "M 5 5 L 10 5 Q 10 7 12 7 T 12 10 Z"
    post = "M 12 7 Q 14 7 12 10 L 5 5 L 10 5 Q 10 7 12 7"

    ante_svg = SvgPath(ante)
    post_svg = change_path_origin(ante_svg, new_origin_index=3)

    # Original must not be mutated
    assert str(ante_svg) == ante
    assert str(post_svg) == post

    # Relative t → q
    ante = "M 5 5 L 10 5 Q 10 7 12 7 t 12 10 Z"
    post = "M 12 7 q 2 0 12 10 L 5 5 L 10 5 Q 10 7 12 7"

    ante_svg = SvgPath(ante)
    post_svg = change_path_origin(ante_svg, new_origin_index=3)

    # Original must not be mutated
    assert str(ante_svg) == ante
    assert str(post_svg) == post


def test_change_path_origin_convert_z_to_l_after_new_origin() -> None:
    """
    ``Z`` commands that appear after the new origin within a subpath are
    converted to ``L``, up to the next ``M``.
    """
    # Single subpath case
    ante = "M 2 2 L 4 2 L 4 3 Z L 2 4 L 1 4 Z L 0 2 L 0 1 Z"
    post = "M 2 4 L 1 4 L 2 2 L 0 2 L 0 1 L 2 2 M 2 2 L 4 2 L 4 3 Z L 2 4"

    ante_svg = SvgPath(ante)
    post_svg = change_path_origin(ante_svg, new_origin_index=5)

    # Original must not be mutated
    assert str(ante_svg) == ante
    assert str(post_svg) == post

    # More complex with additional subpaths
    ante = (
        "M 2 2 L 4 2 L 4 3 Z "
        "L 2 4 L 1 4 Z "
        "L 0 2 L 0 1 Z "
        "L 2 0 L 3 0 Z "
        "M 2 -2 L 3 -2 L 2 -3 Z L 1 -2 L 2 -1 Z"
    )
    post = (
        "M 2 4 L 1 4 L 2 2 L 0 2 L 0 1 L 2 2 L 2 0 L 3 0 L 2 2 "
        "M 2 -2 L 3 -2 L 2 -3 Z L 1 -2 L 2 -1 Z "
        "M 2 2 L 4 2 L 4 3 Z L 2 4"
    )

    ante_svg = SvgPath(ante)
    post_svg = change_path_origin(ante_svg, new_origin_index=5)

    # Original must not be mutated
    assert str(ante_svg) == ante
    assert str(post_svg) == post
