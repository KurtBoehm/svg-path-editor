import pytest

from svg_path_editor import Point, SvgItem, SvgPath
from svg_path_editor.svg import CurveTo, QuadraticBezierCurveTo


def test_item_invalid_make() -> None:
    """Various invalid arguments when creating a path item raise :class:`ValueError`."""
    with pytest.raises(ValueError):
        SvgItem.make([])
    with pytest.raises(ValueError):
        SvgItem.make(["x"])


def test_path_parse_invalid_command_type() -> None:
    """Parsing a path with an unknown command type raises :class:`ValueError`."""
    with pytest.raises(ValueError):
        SvgPath("x 0 0 z")


def test_path_parse_invalid_format_specifier() -> None:
    """Formatting with an unsupported format specifier raises :class:`ValueError`."""
    with pytest.raises(ValueError):
        f"{SvgPath('m 0 0 z'):z}"
    with pytest.raises(ValueError):
        f"{SvgPath('m 0 0 z'):.3x}"


def test_path_invalid_change_type() -> None:
    """Changing the type of an item to an invalid type raises :class:`ValueError`."""
    path = SvgPath("m 0 0 l 1 1 h -1 z")

    with pytest.raises(ValueError):
        path.change_type(1, "x")


def test_path_item_out_of_place() -> None:
    """Transform a standalone path item out of place."""

    ante = SvgItem.make(["M", "2", "1"])

    post = ante.translated("0.1", "0.2")
    assert f"{post:m}" == "M 2.1 1.2"

    post = ante.scaled("0.2", "0.1")
    assert f"{post:m}" == "M .4 .1"

    post = ante.rotated(0, 0, 90)
    assert f"{post:m}" == "M -1 2"


def test_modify_move_close() -> None:
    """Changing move and close-path commands updates the path as expected."""
    ante = "M 0 0 L 1 1 V 0 Z M 1 1 L 0 2 H 1 L 1 1"
    path = SvgPath(ante)

    # Changing the type of the first item is a no-op
    path.change_type(0, "M")
    path.change_type(4, "M")
    assert str(path) == ante

    path.change_type(7, "Z")
    assert str(path) == "M 0 0 L 1 1 V 0 Z M 1 1 L 0 2 H 1 Z"


def test_refresh_cubic_bezier() -> None:
    """
    Refreshing a cubic Bézier command without previous item raises :class:`ValueError`.
    """
    item = CurveTo([10, 0, 15, 5, 10, 10], relative=False)
    with pytest.raises(ValueError):
        item.refresh_absolute_control_points(Point(0, 0), previous_target=None)


def test_modify_smooth_cubic_bezier() -> None:
    """Modify a path segment using the smooth cubic Bézier command ``S``."""
    path = SvgPath("M 0 0 Q 5 -5 10 0 V 10 Z")

    # Change type from `V` to `S`
    path.change_type(2, "S")
    assert f"{path:.2}" == "M 0 0 Q 5 -5 10 0 S 10 6.67 10 10 Z"

    # Set position of the control point of the `S`
    path.set_location(path.control_locations[-1], to=Point(15, 5))
    assert str(path) == "M 0 0 Q 5 -5 10 0 S 15 5 10 10 Z"

    assert path.path[2].as_standalone_string() == "M 10 0 C 10 0 15 5 10 10"

    # Conversion to `C` and back
    path.change_type(2, "C")
    assert f"{path:.2}" == "M 0 0 Q 5 -5 10 0 C 10 0 15 5 10 10 Z"
    path.change_type(2, "S")
    assert str(path) == "M 0 0 Q 5 -5 10 0 S 15 5 10 10 Z"


def test_modify_vertical_line() -> None:
    """Modify a path segment using the vertical line command ``V``."""
    path = SvgPath("M 0 0 Q 5 -5 10 0 V 10 Z")
    path.set_location(path.target_locations[-2], to=Point(0, 5))
    assert str(path) == "M 0 0 Q 5 -5 10 0 V 5 Z"

    assert str(path.path[-2]) == "V 5"
    assert path.path[-2].as_standalone_string() == "M 10 0 V 5"


def test_modify_horizontal_line() -> None:
    """Modify a path segment using the horizontal line command ``H``."""
    path = SvgPath("M 0 0 H 10 Q 15 5 10 10 Z")
    path.set_location(path.target_locations[-3], to=Point(5, 0))
    assert str(path) == "M 0 0 H 5 Q 15 5 10 10 Z"


def test_modify_quadratic_bezier_curve() -> None:
    """Modify a path segment using the quadratic Bézier command ``Q``."""
    path = SvgPath("M 0 0 Q 5 -5 10 0 V 10 Z")

    # Set position of the control point of the `Q`
    path.set_location(path.control_locations[-1], to=Point(5, -4))
    assert str(path) == "M 0 0 Q 5 -4 10 0 V 10 Z"

    # Refreshing a `Q` command without previous item raises :class:`ValueError`.
    item = QuadraticBezierCurveTo([5, -4, 10, 0], relative=False)
    with pytest.raises(ValueError):
        item.refresh_absolute_control_points(Point(0, 0), previous_target=None)


def test_modify_smooth_quadratic_bezier_curve() -> None:
    """Modify a path segment using the smooth quadratic Bézier command ``T``."""
    path = SvgPath("M 0 0 L 5 -5 L 10 0 V 10 Z")

    # Convert line segments to `T`
    path.change_type(1, "T")
    path.change_type(2, "T")
    assert str(path) == "M 0 0 T 5 -5 T 10 0 V 10 Z"

    assert path.path[2].as_standalone_string() == "M 5 -5 Q 10 -10 10 0"


def test_modify_elliptical_arc() -> None:
    """Modify a path segment by converting a line into an elliptical arc ``A``."""
    path = SvgPath("M 0 0 H 10 V -10 Z")
    path.change_type(1, "A")
    assert str(path) == "M 0 0 A 1 1 0 0 0 10 0 V -10 Z"
