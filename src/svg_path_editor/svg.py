# This file is part of https://github.com/KurtBoehm/svg_path_editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from abc import ABC
import re
from collections.abc import Iterable
from decimal import Decimal, getcontext
from typing import TYPE_CHECKING, Final, Self, TypedDict, final, override

from .path_parser import PathParser

if TYPE_CHECKING:
    import sympy as sp

__all__ = [
    "Point",
    "SvgPoint",
    "SvgControlPoint",
    "SvgItem",
    "DummySvgItem",
    "MoveTo",
    "LineTo",
    "CurveTo",
    "SmoothCurveTo",
    "QuadraticBezierCurveTo",
    "SmoothQuadraticBezierCurveTo",
    "ClosePath",
    "HorizontalLineTo",
    "VerticalLineTo",
    "EllipticalArcTo",
    "SvgPath",
]

Number = Decimal | int | float | str

_number_strip_trailing_zeros: Final = re.compile(r"^(-?[0-9]*\.([0-9]*[1-9])?)0*$")
_number_strip_dot: Final = re.compile(r"\.$")
_number_leading_zero: Final = re.compile(r"^(-?)0\.")
_minify_cmd_space: Final = re.compile(r"^([a-zA-Z]) ")
_minify_dot_gap: Final = re.compile(r"(\.[0-9]+) (?=\.)")


def _dec_to_rat(x: Decimal) -> "sp.Expr":
    """
    Convert a ``Decimal`` to a SymPy ``Rational``
    using the exact decimal representation.
    """
    import sympy as sp

    return sp.Rational(str(x))


def _rat_to_dec(x: "sp.Expr") -> Decimal:
    """
    Convert a SymPy expression to ``Decimal`` with current precision.

    The result is evaluated to a decimal string using the current
    ``Decimal`` context precision and then converted to ``Decimal``.
    """
    return Decimal(str(x.evalf(n=getcontext().prec)))


def _dec_to_str(x: Decimal) -> str:
    """
    Convert a ``Decimal`` to a normalized string in fixed-point notation.

    The value is normalized and formatted using fixed-point notation,
    removing any exponent part while preserving the exact decimal value.
    """
    return f"{x.normalize():f}"


def _format_number(v: Decimal, d: int | None, minify: bool = False) -> str:
    """
    Format a ``Decimal`` with optional fixed decimals and SVG number minification.

    :param v: Value to format.
    :param d: Number of decimal places, or ``None`` for default string conversion.
    :param minify: Apply SVG-oriented minification (strip trailing zeros,
        leading zero before decimal, etc.).
    """
    v = v.normalize()
    s = f"{v:.{d}f}" if d is not None else f"{v:f}"
    s = _number_strip_trailing_zeros.sub(r"\1", s)
    s = _number_strip_dot.sub("", s)
    if minify:
        s = _number_leading_zero.sub(r"\1.", s)
    return s


def _parse_format_spec(spec: str) -> tuple[int | None, bool]:
    """
    Parse a format specification for path/string formatting.

    The accepted pattern is a combination of:

    * an optional ``.N`` for decimal places
    * an optional ``m`` flag to enable minification

    Order and whitespace are ignored, e.g. ``"m.3"``, ``".3m"`` and
    ``"  .3   m  "`` all mean the same.

    :param spec: Raw format spec passed to :meth:`__format__`.
    :return: ``(decimals, minify)`` where ``decimals`` is ``None`` if not set.
    """
    decimals: int | None = None
    minify = False

    spec = spec.strip()
    if spec:
        # allow "m", ".3", ".3m", "m.3", "  m  .2  " etc.
        if "m" in spec:
            minify = True
            spec = spec.replace("m", "")
        spec = spec.strip()
        if spec.startswith("."):
            decimals = int(spec[1:])
        elif len(spec) > 0:
            raise ValueError(f"Unsupported format spec: {spec}")

    return decimals, minify


class Point:
    """Simple 2D point."""

    def __init__(self, x: Number, y: Number) -> None:
        """
        :param x: x coordinate.
        :param y: y coordinate.
        """
        self.x: Decimal = Decimal(x)
        self.y: Decimal = Decimal(y)


class SvgPoint(Point):
    """
    Point used as target or vertex in an SVG path.

    Instances hold a back-reference to the :class:`SvgItem` that owns them.
    """

    def __init__(self, x: Number, y: Number) -> None:
        """
        :param x: x coordinate.
        :param y: y coordinate.
        """
        super().__init__(x, y)
        self.item_reference: SvgItem = DummySvgItem()


class SvgControlPoint(SvgPoint):
    """
    Control point for Bézier segments with optional relation hints.

    The :attr:`relations` list can be used to store points that geometrically
    constrain this control point (e.g. endpoints of the segment).
    """

    def __init__(self, point: Point, relations: list[Point]) -> None:
        """
        :param point: Base point for the control point.
        :param relations: Related points, e.g. endpoints of the curve segment.
        """
        super().__init__(point.x, point.y)
        self.sub_index: int = 0
        self.relations: list[Point] = relations


class SvgItem(ABC):
    """Base class for a single SVG path command and its numeric values."""

    def __init__[T: Number](self, values: list[T], relative: bool) -> None:
        """
        :param values: Command parameters as a flat list of numbers.
        :param relative: Whether values are stored in relative coordinates.
        """
        self._relative: bool = relative
        self.values: list[Decimal] = [Decimal(v) for v in values]
        self.previous_point: Point = Point(0, 0)
        self.absolute_points: list[SvgPoint] = []
        self.absolute_control_points: list[SvgControlPoint] = []

    @staticmethod
    def make(raw_item: list[str]) -> SvgItem:
        """
        Construct the appropriate subclass of :class:`SvgItem` from a parsed command
        and its parameter strings.

        :param raw_item: List starting with the command letter followed by numeric
            parameters as strings (e.g. ``["M", "0", "0"]``).
        :raises ValueError: If the item is empty or the command is invalid.
        """
        if not raw_item:
            raise ValueError("Empty SVG item")

        cmd = raw_item[0]
        relative = cmd.islower()
        values = [Decimal(it) for it in raw_item[1:]]

        mapping: dict[str, type[SvgItem]] = {
            MoveTo.key: MoveTo,
            LineTo.key: LineTo,
            HorizontalLineTo.key: HorizontalLineTo,
            VerticalLineTo.key: VerticalLineTo,
            ClosePath.key: ClosePath,
            CurveTo.key: CurveTo,
            SmoothCurveTo.key: SmoothCurveTo,
            QuadraticBezierCurveTo.key: QuadraticBezierCurveTo,
            SmoothQuadraticBezierCurveTo.key: SmoothQuadraticBezierCurveTo,
            EllipticalArcTo.key: EllipticalArcTo,
        }

        cls = mapping.get(cmd.upper())
        if not cls:
            raise ValueError(f"Invalid SVG command type: {cmd!r}")
        return cls(values, relative)

    @staticmethod
    def make_from(origin: SvgItem, previous: SvgItem, new_type: str) -> SvgItem:
        """
        Create a new :class:`SvgItem` of type ``new_type`` from an existing item.

        The new item preserves the current target location and, where possible,
        the original control point geometry.

        :param origin: Existing item whose geometry should be preserved.
        :param previous: Previous item in the path, used for control point defaults.
        :param new_type: New SVG command letter (e.g. ``"L"`` or ``"c"``).
        :raises ValueError: If ``new_type`` is not supported.
        """
        target = origin.target_location()
        x, y = _dec_to_str(target.x), _dec_to_str(target.y)
        absolute_type = new_type.upper()

        match absolute_type:
            case MoveTo.key:
                parts = [MoveTo.key, x, y]
            case LineTo.key:
                parts = [LineTo.key, x, y]
            case HorizontalLineTo.key:
                parts = [HorizontalLineTo.key, x]
            case VerticalLineTo.key:
                parts = [VerticalLineTo.key, y]
            case ClosePath.key:
                parts = [ClosePath.key]
            case CurveTo.key:
                parts = [CurveTo.key, "0", "0", "0", "0", x, y]
            case SmoothCurveTo.key:
                parts = [SmoothCurveTo.key, "0", "0", x, y]
            case QuadraticBezierCurveTo.key:
                parts = [QuadraticBezierCurveTo.key, "0", "0", x, y]
            case SmoothQuadraticBezierCurveTo.key:
                parts = [SmoothQuadraticBezierCurveTo.key, x, y]
            case EllipticalArcTo.key:
                parts = [EllipticalArcTo.key, "1", "1", "0", "0", "0", x, y]
            case _:
                raise ValueError(f"Unsupported SVG item type: {new_type!r}")

        result = SvgItem.make(parts)
        result.previous_point = previous.target_location()
        result.absolute_points = [target]
        result.reset_control_points(previous)

        control_points = origin.absolute_control_points

        if isinstance(origin, (CurveTo, SmoothCurveTo)) and isinstance(
            result, (CurveTo, SmoothCurveTo)
        ):
            if isinstance(result, CurveTo):
                result.values[0] = control_points[0].x
                result.values[1] = control_points[0].y
                result.values[2] = control_points[1].x
                result.values[3] = control_points[1].y
            else:
                result.values[0] = control_points[1].x
                result.values[1] = control_points[1].y

        if isinstance(
            origin, (QuadraticBezierCurveTo, SmoothQuadraticBezierCurveTo)
        ) and isinstance(result, QuadraticBezierCurveTo):
            result.values[0] = control_points[0].x
            result.values[1] = control_points[0].y

        if new_type != absolute_type:
            result.relative = True
        return result

    def refresh_absolute_points(self, origin: Point, previous: SvgItem | None) -> None:
        """
        Recalculate absolute points from stored values and the previous item.

        :param origin: Current subpath origin (last ``M``/``m`` or ``Z``).
        :param previous: Previous item in the path, or ``None`` for the first item.
        """
        self.previous_point = previous.target_location() if previous else Point(0, 0)
        self.absolute_points = []

        current = self.previous_point if self.relative else Point(0, 0)

        for i in range(0, len(self.values) - 1, 2):
            self.absolute_points.append(
                SvgPoint(current.x + self.values[i], current.y + self.values[i + 1])
            )

    @property
    def relative(self) -> bool:
        """Whether this command is stored in relative coordinates."""
        return self._relative

    @relative.setter
    def relative(self, new_relative: bool) -> None:
        """
        Switch between relative and absolute representation.

        The underlying numeric values are rewritten based on the last known
        :attr:`previous_point`.

        :param new_relative: Target representation (``True`` for relative).
        """
        if self._relative == new_relative:
            return

        self._relative = False
        dx = -self.previous_point.x if new_relative else self.previous_point.x
        dy = -self.previous_point.y if new_relative else self.previous_point.y
        self.translate(dx, dy)
        self._relative = new_relative

    def refresh_absolute_control_points(
        self, origin: Point, previous_target: SvgItem | None
    ) -> None:
        """
        Recalculate absolute control points.

        The default implementation assumes there are no control points.

        :param origin: Current subpath origin.
        :param previous_target: Previous item in the path, if any.
        """
        self.absolute_control_points = []

    def reset_control_points(self, previous_target: SvgItem) -> None:
        """
        Reset control points to a default geometry between previous and target.

        Subclasses for curve commands override this to compute reasonable defaults.

        :param previous_target: Previous item in the path.
        """
        pass

    def refresh(self, origin: Point, previous: SvgItem | None) -> None:
        """
        Recompute all absolute points and re-bind back-references.

        :param origin: Current subpath origin.
        :param previous: Previous item in the path, or ``None`` for the first item.
        """
        self.refresh_absolute_points(origin, previous)
        self.refresh_absolute_control_points(origin, previous)

        for point in self.absolute_points:
            point.item_reference = self
        for ctrl in self.absolute_control_points:
            ctrl.item_reference = self

    def clone(self) -> Self:
        """
        Return a shallow clone of this item, retaining its subclass.

        Values, relativity and :attr:`previous_point` are copied. Absolute points
        and control points need to be recomputed via :meth:`refresh`,
        as is done in :meth:`SvgPath.clone`.
        """
        clone = self.__class__(self.values.copy(), self._relative)
        clone.previous_point = Point(self.previous_point.x, self.previous_point.y)
        return clone

    def translate(self, x: Number, y: Number, force: bool = False) -> None:
        """
        Translate in place.

        Relative items are translated only if ``force`` is true; otherwise their
        stored deltas are left unchanged.

        :param x: Translation in x direction.
        :param y: Translation in y direction.
        :param force: Also adjust relative coordinates.
        """
        x, y = Decimal(x), Decimal(y)
        if not self.relative or force:
            for idx in range(len(self.values)):
                self.values[idx] += x if idx % 2 == 0 else y

    def translated(self, x: Number, y: Number, force: bool = False) -> SvgItem:
        """
        Return a translated copy. See :meth:`translate` for details.

        :param x: Translation in x direction.
        :param y: Translation in y direction.
        :param force: Also adjust relative coordinates.
        """
        item = self.clone()
        item.translate(x, y, force=force)
        return item

    def scale(self, kx: Number, ky: Number) -> None:
        """
        Scale in place.

        :param kx: Scale factor for x coordinates.
        :param ky: Scale factor for y coordinates.
        """
        kx, ky = Decimal(kx), Decimal(ky)
        for idx in range(len(self.values)):
            self.values[idx] *= kx if idx % 2 == 0 else ky

    def scaled(self, kx: Number, ky: Number) -> SvgItem:
        """
        Return a scaled copy.

        :param kx: Scale factor for x coordinates.
        :param ky: Scale factor for y coordinates.
        """
        item = self.clone()
        item.scale(kx, ky)
        return item

    def rotate(
        self, ox: Number, oy: Number, degrees: Number, force: bool = False
    ) -> None:
        """
        Rotate the item in place around ``(ox, oy)``.

        For relative items, rotation is performed around ``(0, 0)`` unless
        ``force`` is true.

        :param ox: Rotation origin x coordinate.
        :param oy: Rotation origin y coordinate.
        :param degrees: Rotation angle in degrees.
        :param force: Rotate relative coordinates around ``(ox, oy)``.
        """
        import sympy as sp

        ox, oy, degrees = Decimal(ox), Decimal(oy), Decimal(degrees)
        angle = sp.rad(_dec_to_rat(degrees))
        cosv, sinv = _rat_to_dec(sp.cos(angle)), _rat_to_dec(sp.sin(angle))

        for i in range(0, len(self.values), 2):
            px, py = self.values[i], self.values[i + 1]
            cx, cy = (0, 0) if self._relative and not force else (ox, oy)
            dx, dy = px - cx, py - cy
            qx = cx + dx * cosv - dy * sinv
            qy = cy + dx * sinv + dy * cosv
            self.values[i] = qx
            self.values[i + 1] = qy

    def rotated(
        self, ox: Number, oy: Number, degrees: Number, force: bool = False
    ) -> SvgItem:
        """
        Return a rotated copy around ``(ox, oy)``. See :meth:`rotate` for details.

        :param ox: Rotation origin x coordinate.
        :param oy: Rotation origin y coordinate.
        :param degrees: Rotation angle in degrees.
        :param force: Rotate relative coordinates around ``(ox, oy)``.
        """
        item = self.clone()
        item.rotate(ox, oy, degrees, force=force)
        return item

    def target_location(self) -> SvgPoint:
        """Final absolute point reached by this item."""
        return self.absolute_points[-1]

    def set_target_location(self, pt: Point) -> None:
        """
        Move the geometric target of this command to ``pt``.

        :param pt: New target location in absolute coordinates.
        """
        loc = self.target_location()
        dx, dy = pt.x - loc.x, pt.y - loc.y
        self.values[-2] += dx
        self.values[-1] += dy

    def set_control_location(self, idx: int, pt: Point) -> None:
        """
        Move control point ``idx`` to ``pt``.

        Only meaningful for commands storing Bézier handles.

        :param idx: Index of the control point to move.
        :param pt: New control point location in absolute coordinates.
        """
        loc = self.absolute_points[idx]
        dx, dy = pt.x - loc.x, pt.y - loc.y
        self.values[2 * idx] += dx
        self.values[2 * idx + 1] += dy

    @property
    def control_locations(self) -> list[SvgControlPoint]:
        """Absolute control points associated with this item."""
        return self.absolute_control_points

    def get_type(self, ignore_is_relative: bool = False) -> str:
        """
        Return the SVG command letter for this item (e.g. ``"M"`` or ``"l"``).

        :param ignore_is_relative:
            Always return the uppercase key regardless of :attr:`relative`.
        """
        type_key = getattr(self.__class__, "key")
        assert isinstance(type_key, str)
        if self.relative and not ignore_is_relative:
            return type_key.lower()
        return type_key

    def as_standalone_string(self) -> str:
        """
        Return a standalone path string for this command.

        The result starts with an ``M`` to this command’s :attr:`previous_point`
        followed by the command itself.
        """
        return " ".join(
            [
                "M",
                _dec_to_str(self.previous_point.x),
                _dec_to_str(self.previous_point.y),
                self.get_type(),
                *[_dec_to_str(v) for v in self.values],
            ]
        )

    def as_string(
        self,
        decimals: int | None = None,
        minify: bool = False,
        trailing_items: Iterable["SvgItem"] = (),
    ) -> str:
        """
        Serialize this command into an SVG path fragment.

        Optionally additional same-typed ``trailing_items`` can be appended
        in a compact form.

        :param decimals: Number of decimal places, or ``None`` for default.
        :param minify: Use a more compact numeric representation.
        :param trailing_items: Additional items of the same type to serialize
            in the same command group.
        """
        flattened = self.values + [v for it in trailing_items for v in it.values]
        str_values = [_format_number(it, decimals, minify) for it in flattened]
        return " ".join([self.get_type(), *str_values])

    @override
    def __format__(self, format_spec: str) -> str:
        """
        Format this item using :meth:`as_string`.

        The ``format_spec`` can be used to control decimal places and
        minification:

        * ``""`` (empty): use :meth:`as_string` defaults
        * ``".3"``: ``decimals=3``
        * ``"m"``: ``minify=True``
        * ``".3m"`` or ``"m.3"``: ``decimals=3``, ``minify=True``

        Any other characters are currently ignored.

        :param format_spec: Format specification string (e.g. ``".3m"``).
        """
        decimals, minify = _parse_format_spec(format_spec)
        return self.as_string(decimals=decimals, minify=minify)

    @override
    def __str__(self) -> str:
        """Return :meth:`as_string` with default options."""
        return self.as_string()


@final
class DummySvgItem(SvgItem):
    """Placeholder item used as a default reference owner for points."""

    def __init__(self) -> None:
        """Create a dummy item with no values, always absolute."""
        super().__init__([], False)


@final
class MoveTo(SvgItem):
    """SVG ``M``/``m`` command (move current point)."""

    key = "M"


@final
class LineTo(SvgItem):
    """SVG ``L``/``l`` command (line to point)."""

    key = "L"


@final
class CurveTo(SvgItem):
    """SVG ``C``/``c`` command (cubic Bézier curve)."""

    key = "C"

    @override
    def refresh_absolute_control_points(
        self, origin: Point, previous_target: SvgItem | None
    ) -> None:
        """
        Recompute absolute control points for a cubic Bézier segment.

        :param origin: Current subpath origin.
        :param previous_target: Previous item in the path.
        :raises ValueError: If there is no previous item.
        """
        if not previous_target:
            raise ValueError("Invalid path: CurveTo without previous item")
        self.absolute_control_points = [
            SvgControlPoint(
                self.absolute_points[0], [previous_target.target_location()]
            ),
            SvgControlPoint(self.absolute_points[1], [self.target_location()]),
        ]

    @override
    def reset_control_points(self, previous_target: SvgItem) -> None:
        """
        Reset control points to a smooth cubic curve between previous and target.

        :param previous_target: Previous item in the path.
        """
        a, b = previous_target.target_location(), self.target_location()
        d = a if self.relative else Point(0, 0)
        self.values[0] = 2 * a.x / 3 + b.x / 3 - d.x
        self.values[1] = 2 * a.y / 3 + b.y / 3 - d.y
        self.values[2] = a.x / 3 + 2 * b.x / 3 - d.x
        self.values[3] = a.y / 3 + 2 * b.y / 3 - d.y


@final
class SmoothCurveTo(SvgItem):
    """SVG ``S``/``s`` command (smooth cubic Bézier curve)."""

    key = "S"

    @override
    def refresh_absolute_control_points(
        self, origin: Point, previous_target: SvgItem | None
    ) -> None:
        """
        Recompute absolute control points for a smooth cubic Bézier segment.

        :param origin: Current subpath origin.
        :param previous_target: Previous item in the path, used for reflection.
        """
        self.absolute_control_points = []

        if isinstance(previous_target, (CurveTo, SmoothCurveTo)):
            prev_loc = previous_target.target_location()
            prev_control = previous_target.absolute_control_points[1]
            pt = Point(2 * prev_loc.x - prev_control.x, 2 * prev_loc.y - prev_control.y)
            self.absolute_control_points.append(SvgControlPoint(pt, [prev_loc]))
        else:
            current = (
                previous_target.target_location() if previous_target else Point(0, 0)
            )
            pt = Point(current.x, current.y)
            self.absolute_control_points.append(SvgControlPoint(pt, []))

        self.absolute_control_points.append(
            SvgControlPoint(self.absolute_points[0], [self.target_location()])
        )

    @override
    def as_standalone_string(self) -> str:
        """Standalone SVG path fragment using ``M`` and an explicit ``C``."""
        ctrl0, ctrl1 = self.absolute_control_points
        target = self.absolute_points[1]
        return " ".join(
            [
                "M",
                _dec_to_str(self.previous_point.x),
                _dec_to_str(self.previous_point.y),
                "C",
                _dec_to_str(ctrl0.x),
                _dec_to_str(ctrl0.y),
                _dec_to_str(ctrl1.x),
                _dec_to_str(ctrl1.y),
                _dec_to_str(target.x),
                _dec_to_str(target.y),
            ]
        )

    @override
    def reset_control_points(self, previous_target: SvgItem) -> None:
        """
        Reset the trailing control point for a smooth cubic curve.

        :param previous_target: Previous item in the path.
        """
        a = previous_target.target_location()
        b = self.target_location()
        d = a if self.relative else Point(0, 0)
        self.values[0] = a.x / 3 + 2 * b.x / 3 - d.x
        self.values[1] = a.y / 3 + 2 * b.y / 3 - d.y

    @override
    def set_control_location(self, idx: int, pt: Point) -> None:
        """
        Move the effective control point of this smooth cubic to ``pt``.

        :param idx: Ignored index, the smooth command has a single free control.
        :param pt: New control point location in absolute coordinates.
        """
        loc = self.absolute_control_points[1]
        dx = pt.x - loc.x
        dy = pt.y - loc.y
        self.values[0] += dx
        self.values[1] += dy


@final
class QuadraticBezierCurveTo(SvgItem):
    """SVG ``Q``/``q`` command (quadratic Bézier curve)."""

    key = "Q"

    @override
    def refresh_absolute_control_points(
        self, origin: Point, previous_target: SvgItem | None
    ) -> None:
        """
        Recompute absolute control point for a quadratic Bézier segment.

        :param origin: Current subpath origin.
        :param previous_target: Previous item in the path.
        :raises ValueError: If there is no previous item.
        """
        if not previous_target:
            raise ValueError("Invalid path: QuadraticBezierCurveTo without previous")
        ctrl = SvgControlPoint(
            self.absolute_points[0],
            [previous_target.target_location(), self.target_location()],
        )
        self.absolute_control_points = [ctrl]

    @override
    def reset_control_points(self, previous_target: SvgItem) -> None:
        """
        Reset the control point to the midpoint of previous and target.

        :param previous_target: Previous item in the path.
        """
        a = previous_target.target_location()
        b = self.target_location()
        d = a if self.relative else Point(0, 0)
        self.values[0] = (a.x + b.x) / 2 - d.x
        self.values[1] = (a.y + b.y) / 2 - d.y


@final
class SmoothQuadraticBezierCurveTo(SvgItem):
    """SVG ``T``/``t`` command (smooth quadratic Bézier curve)."""

    key = "T"

    @override
    def refresh_absolute_control_points(
        self, origin: Point, previous_target: SvgItem | None
    ) -> None:
        """
        Recompute absolute control point for a smooth quadratic Bézier segment.

        :param origin: Current subpath origin.
        :param previous_target: Previous item in the path, used for reflection.
        """
        if not isinstance(
            previous_target, (QuadraticBezierCurveTo, SmoothQuadraticBezierCurveTo)
        ):
            previous = (
                previous_target.target_location() if previous_target else Point(0, 0)
            )
            pt = Point(previous.x, previous.y)
            self.absolute_control_points = [SvgControlPoint(pt, [])]
            return

        prev_loc = previous_target.target_location()
        prev_control = previous_target.absolute_control_points[0]
        pt = Point(2 * prev_loc.x - prev_control.x, 2 * prev_loc.y - prev_control.y)
        ctrl = SvgControlPoint(pt, [prev_loc, self.target_location()])
        self.absolute_control_points = [ctrl]

    @override
    def as_standalone_string(self) -> str:
        """Standalone SVG path fragment using ``M`` and an explicit ``Q``."""
        ctrl = self.absolute_control_points[0]
        target = self.absolute_points[0]
        return " ".join(
            [
                "M",
                _dec_to_str(self.previous_point.x),
                _dec_to_str(self.previous_point.y),
                "Q",
                _dec_to_str(ctrl.x),
                _dec_to_str(ctrl.y),
                _dec_to_str(target.x),
                _dec_to_str(target.y),
            ]
        )


@final
class ClosePath(SvgItem):
    """SVG ``Z``/``z`` command (close current subpath)."""

    key = "Z"

    @override
    def refresh_absolute_points(self, origin: Point, previous: SvgItem | None) -> None:
        """
        Set the target to the current subpath origin.

        :param origin: Subpath origin point.
        :param previous: Previous item in the path, if any.
        """
        self.previous_point = previous.target_location() if previous else Point(0, 0)
        self.absolute_points = [SvgPoint(origin.x, origin.y)]


@final
class HorizontalLineTo(SvgItem):
    """SVG ``H``/``h`` command (horizontal line)."""

    key = "H"

    @override
    def rotate(
        self, ox: Number, oy: Number, degrees: Number, force: bool = False
    ) -> None:
        """
        Rotate in place.

        Only a rotation by 180 degrees affects pure horizontal segments. Other
        angles are handled at the path level by type changes.

        :param ox: Rotation origin x coordinate (ignored here).
        :param oy: Rotation origin y coordinate (ignored here).
        :param degrees: Rotation angle in degrees.
        :param force: Unused for this subclass.
        """
        if Decimal(degrees) == Decimal(180):
            self.values[0] = -self.values[0]

    @override
    def refresh_absolute_points(self, origin: Point, previous: SvgItem | None) -> None:
        """
        Recompute absolute point for a horizontal line.

        :param origin: Current subpath origin.
        :param previous: Previous item in the path.
        """
        self.previous_point = previous.target_location() if previous else Point(0, 0)
        x = self.values[0] + self.previous_point.x if self.relative else self.values[0]
        self.absolute_points = [SvgPoint(x, self.previous_point.y)]

    @override
    def set_target_location(self, pt: Point) -> None:
        """
        Move the target x coordinate to ``pt.x`` (y stays unchanged).

        :param pt: New target location.
        """
        loc = self.target_location()
        dx = pt.x - loc.x
        self.values[0] += dx


@final
class VerticalLineTo(SvgItem):
    """SVG ``V``/``v`` command (vertical line)."""

    key = "V"

    @override
    def rotate(
        self, ox: Number, oy: Number, degrees: Number, force: bool = False
    ) -> None:
        """
        Rotate in place.

        Only a rotation by 180 degrees affects pure vertical segments. Other
        angles are handled at the path level by type changes.

        :param ox: Rotation origin x coordinate (ignored here).
        :param oy: Rotation origin y coordinate (ignored here).
        :param degrees: Rotation angle in degrees.
        :param force: Unused for this subclass.
        """
        if Decimal(degrees) == Decimal(180):
            self.values[0] = -self.values[0]

    @override
    def translate(self, x: Number, y: Number, force: bool = False) -> None:
        """
        Translate in place.

        For absolute vertical lines, only the y coordinate is translated.

        :param x: Translation in x direction (ignored).
        :param y: Translation in y direction.
        :param force: Unused for this subclass.
        """
        if not self.relative:
            self.values[0] += Decimal(y)

    @override
    def scale(self, kx: Number, ky: Number) -> None:
        """
        Scale in place.

        For vertical lines only y scaling applies.

        :param kx: Scale factor for x coordinates (ignored).
        :param ky: Scale factor for y coordinates.
        """
        self.values[0] *= Decimal(ky)

    @override
    def refresh_absolute_points(self, origin: Point, previous: SvgItem | None) -> None:
        """
        Recompute absolute point for a vertical line.

        :param origin: Current subpath origin.
        :param previous: Previous item in the path.
        """
        self.previous_point = previous.target_location() if previous else Point(0, 0)
        y = self.values[0] + self.previous_point.y if self.relative else self.values[0]
        self.absolute_points = [SvgPoint(self.previous_point.x, y)]

    @override
    def set_target_location(self, pt: Point) -> None:
        """
        Move the target y coordinate to ``pt.y`` (x stays unchanged).

        :param pt: New target location.
        """
        loc = self.target_location()
        dy = pt.y - loc.y
        self.values[0] += dy


@final
class EllipticalArcTo(SvgItem):
    """SVG ``A``/``a`` command (elliptical arc)."""

    key = "A"

    @override
    def translate(self, x: Number, y: Number, force: bool = False) -> None:
        """
        Translate in place.

        For absolute arcs, only the arc target coordinates are translated.

        :param x: Translation in x direction.
        :param y: Translation in y direction.
        :param force: Unused for this subclass.
        """
        if not self.relative:
            self.values[5] += Decimal(x)
            self.values[6] += Decimal(y)

    @override
    def rotate(
        self, ox: Number, oy: Number, degrees: Number, force: bool = False
    ) -> None:
        """
        Rotate in place.

        The arc’s rotation angle and target coordinates are updated accordingly.

        :param ox: Rotation origin x coordinate.
        :param oy: Rotation origin y coordinate.
        :param degrees: Rotation angle in degrees.
        :param force: Rotate relative coordinates around ``(ox, oy)``.
        """
        import sympy as sp

        ox, oy, degrees = Decimal(ox), Decimal(oy), Decimal(degrees)

        self.values[2] = (self.values[2] + degrees) % 360
        angle = sp.rad(_dec_to_rat(degrees))
        cosv, sinv = _rat_to_dec(sp.cos(angle)), _rat_to_dec(sp.sin(angle))
        px, py = self.values[5], self.values[6]
        x, y = (0, 0) if self.relative and not force else (ox, oy)
        dx, dy = px - x, py - y
        qx = dx * cosv - dy * sinv + x
        qy = dx * sinv + dy * cosv + y
        self.values[5] = qx
        self.values[6] = qy

    @override
    def scale(self, kx: Number, ky: Number) -> None:
        """
        Scale in place.

        Radii, rotation angle, target and sweep flag are updated to reflect the
        scaling factors.

        :param kx: Scale factor for x coordinates.
        :param ky: Scale factor for y coordinates.
        """
        import sympy as sp

        kx, ky = Decimal(kx), Decimal(ky)

        a, b = _dec_to_rat(self.values[0]), _dec_to_rat(self.values[1])
        degrees = _dec_to_rat(self.values[2])
        rkx, rky = _dec_to_rat(kx), _dec_to_rat(ky)
        angle = sp.rad(degrees)
        cosv, sinv = sp.cos(angle), sp.sin(angle)

        ca = b * b * rky * rky * cosv * cosv + a * a * rky * rky * sinv * sinv
        cb = 2 * rkx * rky * cosv * sinv * (b * b - a * a)
        cc = a * a * rkx * rkx * cosv * cosv + b * b * rkx * rkx * sinv * sinv
        cf = -(a * a * b * b * rkx * rkx * rky * rky)
        det = cb * cb - 4 * ca * cc
        val1 = sp.sqrt((ca - cc) * (ca - cc) + cb * cb)

        # New rotation
        if not cb.equals(0):
            # atan2-style expression in degrees, using SymPy
            self.values[2] = _rat_to_dec(sp.deg(sp.atan2(cc - ca - val1, cb)))
        else:
            # Fall back to axis-aligned orientation
            self.values[2] = Decimal(0) if ca < cc else Decimal(90)

        # New radii
        if not det.equals(0):
            # Use SymPy throughout and convert back at the end
            f = 2 * det * cf
            self.values[0] = _rat_to_dec(-sp.sqrt(f * ((ca + cc) + val1)) / det)
            self.values[1] = _rat_to_dec(-sp.sqrt(f * ((ca + cc) - val1)) / det)

        # New target
        self.values[5] *= kx
        self.values[6] *= ky

        # New sweep flag
        self.values[4] = self.values[4] if kx * ky >= 0 else 1 - self.values[4]

    @override
    def refresh_absolute_points(self, origin: Point, previous: SvgItem | None) -> None:
        """
        Recompute the absolute target point for the arc.

        :param origin: Current subpath origin.
        :param previous: Previous item in the path.
        """
        self.previous_point = previous.target_location() if previous else Point(0, 0)
        if self.relative:
            x = self.values[5] + self.previous_point.x
            y = self.values[6] + self.previous_point.y
            self.absolute_points = [SvgPoint(x, y)]
        else:
            self.absolute_points = [SvgPoint(self.values[5], self.values[6])]

    @override
    def as_string(
        self,
        decimals: int | None = None,
        minify: bool = False,
        trailing_items: Iterable[SvgItem] = (),
    ) -> str:
        """
        Serialize this arc (and optionally trailing arcs) to an SVG path fragment.

        :param decimals: Number of decimal places, or ``None`` for default.
        :param minify: Use a compact group representation.
        :param trailing_items: Additional arc items to serialize together.
        """
        if not minify:
            return super().as_string(decimals, minify, trailing_items)

        vals_groups = [self.values, *[it.values for it in trailing_items]]
        formatted_groups = [
            [_format_number(v, decimals, minify) for v in vals] for vals in vals_groups
        ]
        compact = [
            f"{v[0]} {v[1]} {v[2]} {v[3]}{v[4]}{v[5]} {v[6]}" for v in formatted_groups
        ]
        return " ".join([self.get_type(), *compact])


class _Grouped(TypedDict):
    """Internal helper structure for grouping path items by command type."""

    type: str
    item: SvgItem
    trailing: list[SvgItem]


class SvgPath:
    """An SVG path as a sequence of :class:`SvgItem`."""

    def __init__(self, path: str) -> None:
        """
        :param path: SVG path data string (e.g. ``"M0 0L10 0Z"``).
        """
        raw_path = PathParser.parse(path)
        self.path: list[SvgItem] = [SvgItem.make(it) for it in raw_path]
        self.refresh_absolute_positions()

    def clone(self) -> SvgPath:
        """
        Return a deep clone of this path.

        All contained items are cloned as well, and absolute positions are recomputed.
        """
        clone = object.__new__(SvgPath)
        clone.path = [it.clone() for it in self.path]
        clone.refresh_absolute_positions()
        return clone

    def translate(self, dx: Number, dy: Number) -> None:
        """
        Translate in place.

        :param dx: Translation in x direction.
        :param dy: Translation in y direction.
        """
        for idx, it in enumerate(self.path):
            it.translate(dx, dy, idx == 0)
        self.refresh_absolute_positions()

    def translated(self, dx: Number, dy: Number) -> SvgPath:
        """
        Return a translated copy of this path.

        :param dx: Translation in x direction.
        :param dy: Translation in y direction.
        """
        new_path = self.clone()
        new_path.translate(dx, dy)
        return new_path

    def scale(self, kx: Number, ky: Number) -> None:
        """
        Scale in place.

        :param kx: Scale factor for x coordinates.
        :param ky: Scale factor for y coordinates.
        """
        for it in self.path:
            it.scale(kx, ky)
        self.refresh_absolute_positions()

    def scaled(self, kx: Number, ky: Number) -> SvgPath:
        """
        Return a scaled copy of this path.

        :param kx: Scale factor for x coordinates.
        :param ky: Scale factor for y coordinates.
        """
        new_path = self.clone()
        new_path.scale(kx, ky)
        return new_path

    def rotate(self, ox: Number, oy: Number, degrees: Number) -> None:
        """
        Rotate in place around ``(ox, oy)``.

        May also normalize horizontal/vertical segments after rotation.

        :param ox: Rotation origin x coordinate.
        :param oy: Rotation origin y coordinate.
        :param degrees: Rotation angle in degrees.
        """
        degrees = Decimal(degrees) % 360
        if degrees == Decimal(0):
            return

        for idx, it in enumerate(self.path):
            last_instance_of = type(it)
            if degrees != Decimal(180) and isinstance(
                it, (HorizontalLineTo, VerticalLineTo)
            ):
                new_type = LineTo.key.lower() if it.relative else LineTo.key
                changed = self.change_type(idx, new_type)
                if changed is not None:
                    it = changed

            it.rotate(ox, oy, degrees, idx == 0)

            if degrees in (Decimal(90), Decimal(270)):
                if last_instance_of is HorizontalLineTo:
                    self.refresh_absolute_positions()
                    new_type = (
                        VerticalLineTo.key.lower()
                        if it.relative
                        else VerticalLineTo.key
                    )
                    self.change_type(idx, new_type)
                elif last_instance_of is VerticalLineTo:
                    self.refresh_absolute_positions()
                    new_type = (
                        HorizontalLineTo.key.lower()
                        if it.relative
                        else HorizontalLineTo.key
                    )
                    self.change_type(idx, new_type)

        self.refresh_absolute_positions()

    def rotated(self, ox: Number, oy: Number, degrees: Number) -> SvgPath:
        """
        Return a rotated copy of this path. See :meth:`rotate` for details.

        :param ox: Rotation origin x coordinate.
        :param oy: Rotation origin y coordinate.
        :param degrees: Rotation angle in degrees.
        """
        new_path = self.clone()
        new_path.rotate(ox, oy, degrees)
        return new_path

    @property
    def relative(self) -> bool:
        """
        Indicate whether all items are stored as relative commands.

        Mixed paths (some absolute, some relative) return ``False``.
        """
        return all(it.relative for it in self.path)

    @relative.setter
    def relative(self, new_relative: bool) -> None:
        """
        Convert all items to relative or absolute coordinates in place.

        :param new_relative: Target representation (``True`` for relative).
        """
        for it in self.path:
            it.relative = new_relative
        self.refresh_absolute_positions()

    def with_relative(self, new_relative: bool) -> SvgPath:
        """
        Return a new path with all items converted to the requested representation.

        :param new_relative: Target representation (``True`` for relative).
        """
        new_path = self.clone()
        new_path.relative = new_relative
        return new_path

    def remove(self, item: SvgItem) -> None:
        """
        Remove the given item.

        :param item: Item to remove.
        :raises ValueError: If the item is not present.
        """
        self.path.remove(item)
        self.refresh_absolute_positions()

    def insert(self, index: int, item: SvgItem) -> None:
        """
        Insert ``item`` before ``index``.

        :param index: Index before which to insert.
        :param item: Item to insert.
        """
        self.path.insert(index, item)
        self.refresh_absolute_positions()

    def change_type(self, index: int, new_type: str) -> SvgItem | None:
        """
        Change the command type of the item at ``index`` in place.

        :param index: The index of the item whose type should be changed.
        :param new_type: New SVG command letter (e.g. ``"L"`` or ``"c"``).
        :return: Newly created :class:`SvgItem` replacing the item at ``index``,
            or ``None`` if ``index`` is not in the path or is the first item.
        """
        if index not in range(1, len(self.path)):
            return None
        previous = self.path[index - 1]
        self.path[index] = SvgItem.make_from(self.path[index], previous, new_type)
        self.refresh_absolute_positions()
        return self.path[index]

    def as_string(self, decimals: int | None = None, minify: bool = False) -> str:
        """
        Serialize the entire path to an SVG path data string.

        :param decimals: Number of decimal places, or ``None`` for default.
        :param minify: Use a compact representation.
        """
        grouped: list[_Grouped] = []
        for it in self.path:
            t = it.get_type()
            if minify and grouped and (last := grouped[-1])["type"] == t:
                last["trailing"].append(it)
                continue
            gtype = "l" if t == "m" else ("L" if t == "M" else t)
            grouped.append({"type": gtype, "item": it, "trailing": []})

        out_parts: list[str] = []
        for g in grouped:
            s = g["item"].as_string(decimals, minify, g["trailing"])
            if minify:
                s = _minify_cmd_space.sub(r"\1", s)
                s = s.replace(" -", "-")
                s = _minify_dot_gap.sub(r"\1", s)
            out_parts.append(s)

        return "".join(out_parts) if minify else " ".join(out_parts)

    @property
    def target_locations(self) -> list[SvgPoint]:
        """Final absolute points for each item in the path."""
        return [it.target_location() for it in self.path]

    @property
    def control_locations(self) -> list[SvgControlPoint]:
        """Flattened list of all absolute control points for the path."""
        result: list[SvgControlPoint] = []
        for item in self.path[1:]:
            controls = item.control_locations
            for idx, ctrl in enumerate(controls):
                ctrl.sub_index = idx
            result.extend(controls)
        return result

    def set_location(self, pt_reference: SvgPoint, to: Point) -> None:
        """
        Move the given point to ``to``.

        The reference must come from a previously queried point list
        (e.g. :attr:`target_locations` or :attr:`control_locations`).

        :param pt_reference: Point (target or control) to be moved.
        :param to: New absolute location for the point.
        """
        if isinstance(pt_reference, SvgControlPoint):
            pt_reference.item_reference.set_control_location(pt_reference.sub_index, to)
        else:
            pt_reference.item_reference.set_target_location(to)
        self.refresh_absolute_positions()

    def refresh_absolute_positions(self) -> None:
        """
        Recompute absolute positions for all items in the path.

        This should be called after structural or coordinate changes.
        """
        previous: SvgItem | None = None
        origin = Point(0, 0)
        for item in self.path:
            item.refresh(origin, previous)
            if isinstance(item, (MoveTo, ClosePath)):
                origin = item.target_location()
            previous = item

    @override
    def __format__(self, format_spec: str) -> str:
        """
        Format this path using :meth:`as_string`.

        The ``format_spec`` can be used to control decimal places and
        minification, following the same rules as :meth:`SvgItem.__format__`:

        * ``""`` (empty): use :meth:`as_string` defaults
        * ``".3"``: ``decimals=3``
        * ``"m"``: ``minify=True``
        * ``".3m"`` or ``"m.3"``: ``decimals=3``, ``minify=True``

        Any other characters are currently ignored.

        :param format_spec: Format specification string (e.g. ``".3m"``).
        """
        decimals, minify = _parse_format_spec(format_spec)
        return self.as_string(decimals=decimals, minify=minify)

    @override
    def __str__(self) -> str:
        """Return :meth:`as_string` with default options."""
        return self.as_string()
