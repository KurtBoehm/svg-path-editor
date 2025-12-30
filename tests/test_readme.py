from typing import Final

from svg_path_editor import SvgPath, change_path_origin, optimize_path, reverse_path

# Shared path used in multiple tests. The original string is kept to ensure
# that out-of-place operations do not mutate it.
path: Final = SvgPath("M-15 14s5 7.5 15 7.5 15-7.5 15-7.5 z")
original_str: Final = str(path)


def test_convert_to_str() -> None:
    """String conversions with and without minification."""

    # Plain string conversion
    assert str(path) == original_str

    # Custom decimals and minified output (decimals=None, minify=False by default)
    s = path.as_string(decimals=1, minify=True)
    assert s == "M-15 14s5 7.5 15 7.5 15-7.5 15-7.5z"


def test_transformations() -> None:
    """Geometric transformations are out-of-place."""

    p = path.scale(kx=2, ky=2)
    assert str(p) == "M -30 28 s 10 15 30 15 s 30 -15 30 -15 z"
    assert str(path) == original_str

    p = path.translate(dx=1, dy=0.5)
    assert str(p) == "M -14 14.5 s 5 7.5 15 7.5 s 15 -7.5 15 -7.5 z"
    assert str(path) == original_str

    p = path.rotate(ox=0, oy=0, degrees=90)
    assert p.as_string(decimals=2) == "M -14 -15 s -7.5 5 -7.5 15 s 7.5 15 7.5 15 z"
    assert str(path) == original_str


def test_absolute_relative() -> None:
    """Convert between absolute and relative command representations."""

    # Setting relative=False mutates the clone in place
    absolute = path.clone()
    absolute.relative = False
    assert str(absolute) == "M -15 14 S -10 21.5 0 21.5 S 15 14 15 14 Z"
    assert str(path) == original_str

    # `with_relative` is out-of-place; internally it sets `relative` on a clone
    p = path.with_relative(True)
    assert str(p) == "m -15 14 s 5 7.5 15 7.5 s 15 -7.5 15 -7.5 z"
    assert str(path) == original_str


def test_reverse() -> None:
    """Reverse path out-of-place."""

    p = reverse_path(path)
    assert str(p) == "M 15 14 S 10 21.5 0 21.5 S -15 14 -15 14 Z"
    assert str(path) == original_str


def test_change_path_origin() -> None:
    """Change the origin of the path out-of-place."""

    p = change_path_origin(path, new_origin_index=2)
    assert str(p) == "M 0 21.5 c 10 0 15 -7.5 15 -7.5 L -15 14 s 5 7.5 15 7.5"
    assert str(path) == original_str


def test_optimize_path() -> None:
    """Optimize a path out-of-place."""

    # All options default to False; here we enable all of them.
    optimized = optimize_path(
        path,
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

    assert str(optimized) == "M -15 14 s 5 7.5 15 7.5 S 15 14 15 14 z"
    assert optimized.as_string(minify=True) == "M-15 14s5 7.5 15 7.5S15 14 15 14z"
    assert str(path) == original_str
