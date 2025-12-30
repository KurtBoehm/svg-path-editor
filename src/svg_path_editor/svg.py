# This file is part of https://github.com/KurtBoehm/svg_path_editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Final, TypedDict, final, override

from .path_parser import PathParser

_number_strip_trailing_zeros: Final = re.compile(r"^(-?[0-9]*\.([0-9]*[1-9])?)0*$")
_number_strip_dot: Final = re.compile(r"\.$")
_number_leading_zero: Final = re.compile(r"^(-?)0\.")
_minify_cmd_space: Final = re.compile(r"^([a-zA-Z]) ")
_minify_negative: Final = re.compile(r" -")
_minify_dot_gap: Final = re.compile(r"(\.[0-9]+) (?=\.)")


def format_number(v: float, d: int | None, minify: bool = False) -> str:
    """Format a float with optional fixed decimals and SVG number minification."""
    s = f"{v:.{d}f}" if d is not None else str(v)
    s = _number_strip_trailing_zeros.sub(r"\1", s)
    s = _number_strip_dot.sub("", s)
    if minify:
        s = _number_leading_zero.sub(r"\1.", s)
    return s


@dataclass
class Point:
    """Simple 2D point."""

    x: float
    y: float


class SvgPoint(Point):
    """Point used as target or vertex in an SVG path."""

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y)
        self.item_reference: SvgItem = DummySvgItem()


class SvgControlPoint(SvgPoint):
    """Control point for Bézier segments with optional relation hints."""

    def __init__(self, point: Point, relations: list[Point]) -> None:
        super().__init__(point.x, point.y)
        self.sub_index: int = 0
        self.relations: list[Point] = relations


class SvgItem:
    """Base class for a single SVG path command and its numeric values."""

    def __init__(self, values: list[float], relative: bool) -> None:
        self._relative: bool = relative
        self.values: list[float] = values
        self.previous_point: Point = Point(0, 0)
        self.absolute_points: list[SvgPoint] = []
        self.absolute_control_points: list[SvgControlPoint] = []

    @staticmethod
    def make(raw_item: list[str]) -> SvgItem:
        """Construct an SvgItem from a parsed command and its parameter strings."""
        if not raw_item:
            raise ValueError("Empty SVG item")

        cmd = raw_item[0]
        relative = cmd.islower()
        values = [float(it) for it in raw_item[1:]]

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
            raise ValueError(f"Invalid SVG item type: {cmd!r}")
        return cls(values, relative)

    @staticmethod
    def make_from(origin: SvgItem, previous: SvgItem, new_type: str) -> SvgItem:
        """
        Create a new SvgItem of type `new_type` based on an existing item,
        preserving the current target location and, where possible, control
        point geometry.
        """
        target = origin.target_location()
        x, y = str(target.x), str(target.y)
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
        result.absolute_points = [SvgPoint(target.x, target.y)]
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
        """Recalculate absolute points from stored values and previous item."""
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
        Switch between relative and absolute representation, rewriting values
        based on the last known previous_point.
        """
        if self._relative == new_relative:
            return

        dx = -self.previous_point.x if new_relative else self.previous_point.x
        dy = -self.previous_point.y if new_relative else self.previous_point.y

        if self.values:
            for i in range(0, len(self.values), 2):
                self.values[i] += dx
                if i + 1 < len(self.values):
                    self.values[i + 1] += dy

        self._relative = new_relative

    def refresh_absolute_control_points(
        self, origin: Point, previous_target: SvgItem | None
    ) -> None:
        """Recalculate absolute control points. Default: no control points."""
        self.absolute_control_points = []

    def reset_control_points(self, previous_target: SvgItem) -> None:
        """Reset control points to a default geometry between previous and target."""
        # Overridden in curve subclasses.
        pass

    def refresh(self, origin: Point, previous: SvgItem | None) -> None:
        """Recompute all absolute points and bind back-references."""
        self.refresh_absolute_points(origin, previous)
        self.refresh_absolute_control_points(origin, previous)

        for point in self.absolute_points:
            point.item_reference = self
        for ctrl in self.absolute_control_points:
            ctrl.item_reference = self

    def clone(self) -> SvgItem:
        """Return a shallow geometric clone of this item (values and relativity)."""
        clone: SvgItem = self.__class__(self.values.copy(), self._relative)
        clone.previous_point = Point(self.previous_point.x, self.previous_point.y)
        # absolute_points / absolute_control_points are recomputed via refresh()
        return clone

    def translate(self, x: float, y: float, force: bool = False) -> SvgItem:
        """
        Return a translated copy. Relative items are translated only if force=True,
        otherwise their stored deltas are left as-is.
        """
        item = self.clone()

        if not item.relative or force:
            for idx in range(len(item.values)):
                item.values[idx] += x if idx % 2 == 0 else y

        return item

    def scale(self, kx: float, ky: float) -> SvgItem:
        """Return a scaled copy, scaling x/y coordinates by kx/ky."""
        item = self.clone()
        for idx in range(len(item.values)):
            item.values[idx] *= kx if idx % 2 == 0 else ky
        return item

    def rotate(
        self, ox: float, oy: float, degrees: float, force: bool = False
    ) -> SvgItem:
        """
        Return a rotated copy around (ox, oy). For relative items, rotation is
        performed around (0, 0) unless force=True.
        """
        item = self.clone()

        rad = math.radians(degrees)
        cosv, sinv = math.cos(rad), math.sin(rad)

        for i in range(0, len(item.values), 2):
            px, py = item.values[i], item.values[i + 1]
            cx, cy = (0, 0) if (item.relative and not force) else (ox, oy)
            dx, dy = px - cx, py - cy
            qx = cx + dx * cosv - dy * sinv
            qy = cy + dx * sinv + dy * cosv
            item.values[i] = qx
            item.values[i + 1] = qy

        return item

    def target_location(self) -> SvgPoint:
        """Final absolute point reached by this item."""
        return self.absolute_points[-1]

    def set_target_location(self, pts: Point) -> None:
        """Move the geometric target of this command to `pts`."""
        loc = self.target_location()
        dx, dy = pts.x - loc.x, pts.y - loc.y
        self.values[-2] += dx
        self.values[-1] += dy

    def set_control_location(self, idx: int, pts: Point) -> None:
        """Move control point `idx` to `pts` (for commands storing Bezier handles)."""
        loc = self.absolute_points[idx]
        dx, dy = pts.x - loc.x, pts.y - loc.y
        self.values[2 * idx] += dx
        self.values[2 * idx + 1] += dy

    @property
    def control_locations(self) -> list[SvgControlPoint]:
        """Absolute control points associated with this item."""
        return self.absolute_control_points

    def get_type(self, ignore_is_relative: bool = False) -> str:
        """Return the SVG command letter for this item, respecting relativity."""
        type_key = getattr(self.__class__, "key")
        assert isinstance(type_key, str)
        if self.relative and not ignore_is_relative:
            return type_key.lower()
        return type_key

    def as_standalone_string(self) -> str:
        """
        Return a path string that starts with a MoveTo to this command’s
        previous_point followed by this command.
        """
        return " ".join(
            [
                "M",
                str(self.previous_point.x),
                str(self.previous_point.y),
                self.get_type(),
                *[str(v) for v in self.values],
            ]
        )

    def as_string(
        self,
        decimals: int | None = None,
        minify: bool = False,
        trailing_items: list[SvgItem] | None = None,
    ) -> str:
        """
        Serialize this command (optionally together with same-typed trailing items)
        into an SVG path fragment.
        """
        trailing_items = trailing_items or []
        flattened = self.values + [v for it in trailing_items for v in it.values]
        str_values = [format_number(it, decimals, minify) for it in flattened]
        return " ".join([self.get_type(), *str_values])


@final
class DummySvgItem(SvgItem):
    """Placeholder item used as a default reference owner for points."""

    def __init__(self) -> None:
        super().__init__([], False)


@final
class MoveTo(SvgItem):
    key = "M"


@final
class LineTo(SvgItem):
    key = "L"


@final
class CurveTo(SvgItem):
    key = "C"

    @override
    def refresh_absolute_control_points(
        self, origin: Point, previous_target: SvgItem | None
    ) -> None:
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
        a, b = previous_target.target_location(), self.target_location()
        d = a if self.relative else Point(0, 0)
        self.values[0] = 2 * a.x / 3 + b.x / 3 - d.x
        self.values[1] = 2 * a.y / 3 + b.y / 3 - d.y
        self.values[2] = a.x / 3 + 2 * b.x / 3 - d.x
        self.values[3] = a.y / 3 + 2 * b.y / 3 - d.y


@final
class SmoothCurveTo(SvgItem):
    key = "S"

    @override
    def refresh_absolute_control_points(
        self, origin: Point, previous_target: SvgItem | None
    ) -> None:
        self.absolute_control_points = []

        if isinstance(previous_target, (CurveTo, SmoothCurveTo)):
            prev_loc = previous_target.target_location()
            prev_control = previous_target.absolute_control_points[1]
            x, y = 2 * prev_loc.x - prev_control.x, 2 * prev_loc.y - prev_control.y
            pts = Point(x, y)
            self.absolute_control_points.append(SvgControlPoint(pts, [prev_loc]))
        else:
            current = (
                previous_target.target_location() if previous_target else Point(0, 0)
            )
            pts = Point(current.x, current.y)
            self.absolute_control_points.append(SvgControlPoint(pts, []))

        self.absolute_control_points.append(
            SvgControlPoint(self.absolute_points[0], [self.target_location()])
        )

    @override
    def as_standalone_string(self) -> str:
        ctrl0, ctrl1 = self.absolute_control_points
        target = self.absolute_points[1]
        return " ".join(
            [
                "M",
                str(self.previous_point.x),
                str(self.previous_point.y),
                "C",
                str(ctrl0.x),
                str(ctrl0.y),
                str(ctrl1.x),
                str(ctrl1.y),
                str(target.x),
                str(target.y),
            ]
        )

    @override
    def reset_control_points(self, previous_target: SvgItem) -> None:
        a = previous_target.target_location()
        b = self.target_location()
        d = a if self.relative else Point(0, 0)
        self.values[0] = a.x / 3 + 2 * b.x / 3 - d.x
        self.values[1] = a.y / 3 + 2 * b.y / 3 - d.y

    @override
    def set_control_location(self, idx: int, pts: Point) -> None:
        loc = self.absolute_control_points[1]
        dx = pts.x - loc.x
        dy = pts.y - loc.y
        self.values[0] += dx
        self.values[1] += dy


@final
class QuadraticBezierCurveTo(SvgItem):
    key = "Q"

    @override
    def refresh_absolute_control_points(
        self, origin: Point, previous_target: SvgItem | None
    ) -> None:
        if not previous_target:
            raise ValueError("Invalid path: QuadraticBezierCurveTo without previous")
        ctrl = SvgControlPoint(
            self.absolute_points[0],
            [previous_target.target_location(), self.target_location()],
        )
        self.absolute_control_points = [ctrl]

    @override
    def reset_control_points(self, previous_target: SvgItem) -> None:
        a = previous_target.target_location()
        b = self.target_location()
        d = a if self.relative else Point(0, 0)
        self.values[0] = 0.5 * (a.x + b.x) - d.x
        self.values[1] = 0.5 * (a.y + b.y) - d.y


@final
class SmoothQuadraticBezierCurveTo(SvgItem):
    key = "T"

    @override
    def refresh_absolute_control_points(
        self, origin: Point, previous_target: SvgItem | None
    ) -> None:
        if not isinstance(
            previous_target, (QuadraticBezierCurveTo, SmoothQuadraticBezierCurveTo)
        ):
            previous = (
                previous_target.target_location() if previous_target else Point(0, 0)
            )
            pts = Point(previous.x, previous.y)
            self.absolute_control_points = [SvgControlPoint(pts, [])]
            return

        prev_loc = previous_target.target_location()
        prev_control = previous_target.absolute_control_points[0]
        x, y = 2 * prev_loc.x - prev_control.x, 2 * prev_loc.y - prev_control.y
        pts = Point(x, y)
        ctrl = SvgControlPoint(pts, [prev_loc, self.target_location()])
        self.absolute_control_points = [ctrl]

    @override
    def as_standalone_string(self) -> str:
        ctrl = self.absolute_control_points[0]
        target = self.absolute_points[0]
        return " ".join(
            [
                "M",
                str(self.previous_point.x),
                str(self.previous_point.y),
                "Q",
                str(ctrl.x),
                str(ctrl.y),
                str(target.x),
                str(target.y),
            ]
        )


@final
class ClosePath(SvgItem):
    key = "Z"

    @override
    def refresh_absolute_points(self, origin: Point, previous: SvgItem | None) -> None:
        self.previous_point = previous.target_location() if previous else Point(0, 0)
        self.absolute_points = [SvgPoint(origin.x, origin.y)]


@final
class HorizontalLineTo(SvgItem):
    key = "H"

    @override
    def rotate(
        self, ox: float, oy: float, degrees: float, force: bool = False
    ) -> SvgItem:
        item = self.clone()
        if degrees == 180:
            item.values[0] = -item.values[0]
        return item

    @override
    def refresh_absolute_points(self, origin: Point, previous: SvgItem | None) -> None:
        self.previous_point = previous.target_location() if previous else Point(0, 0)
        x = self.values[0] + self.previous_point.x if self.relative else self.values[0]
        self.absolute_points = [SvgPoint(x, self.previous_point.y)]

    @override
    def set_target_location(self, pts: Point) -> None:
        loc = self.target_location()
        dx = pts.x - loc.x
        self.values[0] += dx


@final
class VerticalLineTo(SvgItem):
    key = "V"

    @override
    def rotate(
        self, ox: float, oy: float, degrees: float, force: bool = False
    ) -> SvgItem:
        item = self.clone()
        if degrees == 180:
            item.values[0] = -item.values[0]
        return item

    @override
    def translate(self, x: float, y: float, force: bool = False) -> SvgItem:
        item = self.clone()
        if not item.relative:
            item.values[0] += y
        return item

    @override
    def scale(self, kx: float, ky: float) -> SvgItem:
        item = self.clone()
        item.values[0] *= ky
        return item

    @override
    def refresh_absolute_points(self, origin: Point, previous: SvgItem | None) -> None:
        self.previous_point = previous.target_location() if previous else Point(0, 0)
        y = self.values[0] + self.previous_point.y if self.relative else self.values[0]
        self.absolute_points = [SvgPoint(self.previous_point.x, y)]

    @override
    def set_target_location(self, pts: Point) -> None:
        loc = self.target_location()
        dy = pts.y - loc.y
        self.values[0] += dy


@final
class EllipticalArcTo(SvgItem):
    key = "A"

    @override
    def translate(self, x: float, y: float, force: bool = False) -> SvgItem:
        item = self.clone()
        if not item.relative:
            item.values[5] += x
            item.values[6] += y
        return item

    @override
    def rotate(
        self, ox: float, oy: float, degrees: float, force: bool = False
    ) -> SvgItem:
        item = self.clone()

        item.values[2] = (item.values[2] + degrees) % 360
        rad = math.radians(degrees)
        cosv, sinv = math.cos(rad), math.sin(rad)
        px, py = item.values[5], item.values[6]
        x, y = (0, 0) if (item.relative and not force) else (ox, oy)
        qx = (px - x) * cosv - (py - y) * sinv + x
        qy = (px - x) * sinv + (py - y) * cosv + y
        item.values[5] = qx
        item.values[6] = qy

        return item

    @override
    def scale(self, kx: float, ky: float) -> SvgItem:
        item = self.clone()
        a, b = item.values[0], item.values[1]
        angle = math.radians(item.values[2])
        cosv, sinv = math.cos(angle), math.sin(angle)
        a = b * b * ky * ky * cosv * cosv + a * a * ky * ky * sinv * sinv
        b2 = 2 * kx * ky * cosv * sinv * (b * b - a * a)
        c = a * a * kx * kx * cosv * cosv + b * b * kx * kx * sinv * sinv
        f = -(a * a * b * b * kx * kx * ky * ky)
        det = b2 * b2 - 4 * a * c
        val1 = math.sqrt((a - c) * (a - c) + b2 * b2)

        # New rotation:
        if b2 != 0:
            item.values[2] = math.degrees(math.atan((c - a - val1) / b2))
        else:
            item.values[2] = 0 if a < c else 90

        # New radii
        if det != 0:
            item.values[0] = -math.sqrt(2 * det * f * ((a + c) + val1)) / det
            item.values[1] = -math.sqrt(2 * det * f * ((a + c) - val1)) / det

        # New target
        item.values[5] *= kx
        item.values[6] *= ky

        # New sweep flag
        item.values[4] = item.values[4] if kx * ky >= 0 else 1 - item.values[4]
        return item

    @override
    def refresh_absolute_points(self, origin: Point, previous: SvgItem | None) -> None:
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
        trailing_items: list[SvgItem] | None = None,
    ) -> str:
        trailing_items = trailing_items or []
        if not minify:
            return super().as_string(decimals, minify, trailing_items)

        vals_groups = [self.values, *[it.values for it in trailing_items]]
        formatted_groups = [
            [format_number(v, decimals, minify) for v in vals] for vals in vals_groups
        ]
        compact = [
            f"{v[0]} {v[1]} {v[2]} {v[3]}{v[4]}{v[5]} {v[6]}" for v in formatted_groups
        ]
        return " ".join([self.get_type(), *compact])


class _Grouped(TypedDict):
    type: str
    item: SvgItem
    trailing: list[SvgItem]


class SvgPath:
    """Immutable-style representation of an SVG path as a sequence of SvgItem."""

    def __init__(self, path: str) -> None:
        raw_path = PathParser.parse(path)
        self.path: list[SvgItem] = [SvgItem.make(it) for it in raw_path]
        self.refresh_absolute_positions()

    def clone(self) -> SvgPath:
        """Return a deep clone of this path (items are cloned as well)."""
        clone = object.__new__(SvgPath)
        clone.path = [it.clone() for it in self.path]
        clone.refresh_absolute_positions()
        return clone

    def translate(self, dx: float, dy: float) -> SvgPath:
        """Return a translated copy of this path."""
        new_path = self.clone()
        new_path.path = [
            it.translate(dx, dy, idx == 0) for idx, it in enumerate(self.path)
        ]
        new_path.refresh_absolute_positions()
        return new_path

    def scale(self, kx: float, ky: float) -> SvgPath:
        """Return a scaled copy of this path."""
        new_path = self.clone()
        new_path.path = [it.scale(kx, ky) for it in self.path]
        new_path.refresh_absolute_positions()
        return new_path

    def rotate(self, ox: float, oy: float, degrees: float) -> SvgPath:
        """
        Return a rotated copy of this path around (ox, oy).
        May also normalize horizontal/vertical segments after rotation.
        """
        degrees %= 360
        if degrees == 0:
            return self.clone()

        new_path = self.clone()
        items = new_path.path

        for idx, it in enumerate(items):
            last_instance_of = it.__class__

            if degrees != 180 and isinstance(it, (HorizontalLineTo, VerticalLineTo)):
                new_type = LineTo.key.lower() if it.relative else LineTo.key
                changed = new_path.change_type(it, new_type)
                if changed is not None:
                    it = changed
                    items[idx] = it

            items[idx] = it.rotate(ox, oy, degrees, idx == 0)

            if degrees in (90, 270):
                if last_instance_of is HorizontalLineTo:
                    new_path.refresh_absolute_positions()
                    new_type = (
                        VerticalLineTo.key.lower()
                        if it.relative
                        else VerticalLineTo.key
                    )
                    it2 = new_path.change_type(items[idx], new_type)
                    if it2 is not None:
                        items[idx] = it2
                elif last_instance_of is VerticalLineTo:
                    new_path.refresh_absolute_positions()
                    new_type = (
                        HorizontalLineTo.key.lower()
                        if it.relative
                        else HorizontalLineTo.key
                    )
                    it2 = new_path.change_type(items[idx], new_type)
                    if it2 is not None:
                        items[idx] = it2

        new_path.refresh_absolute_positions()
        return new_path

    @property
    def relative(self) -> bool:
        """
        True if all items are stored as relative commands. Mixed paths return False.
        """
        return all(it.relative for it in self.path)

    @relative.setter
    def relative(self, new_relative: bool) -> None:
        """
        In-place conversion of all items to relative or absolute coordinates.
        Note: this mutates the current SvgPath instance for efficiency.
        """
        for it in self.path:
            it.relative = new_relative
        self.refresh_absolute_positions()

    def with_relative(self, new_relative: bool) -> SvgPath:
        """
        Return a new path with all items converted to the requested
        relative/absolute representation.
        """
        new_path = self.clone()
        new_path.relative = new_relative
        return new_path

    def delete(self, item: SvgItem) -> SvgPath:
        """Return a new path with the given item removed, if present."""
        if item not in self.path:
            return self.clone()
        new_path = self.clone()
        new_path.path.remove(new_path.path[self.path.index(item)])
        new_path.refresh_absolute_positions()
        return new_path

    def insert(self, item: SvgItem, after: SvgItem | None = None) -> SvgPath:
        """
        Return a new path with `item` inserted after `after`, or appended at
        the end if `after` is None or not found.
        """
        new_path = self.clone()
        if after is not None and after in self.path:
            idx = self.path.index(after)
            new_path.path.insert(idx + 1, item)
        else:
            new_path.path.append(item)
        new_path.refresh_absolute_positions()
        return new_path

    def change_type(self, item: SvgItem, new_type: str) -> SvgItem | None:
        """
        Change the command type of `item` in-place within this path, returning
        the newly created SvgItem, or None if `item` is not in the path or
        is the first item.
        """
        if item not in self.path:
            return None
        idx = self.path.index(item)
        if idx == 0:
            return None

        previous = self.path[idx - 1]
        new_item = SvgItem.make_from(item, previous, new_type)
        self.path[idx] = new_item
        self.refresh_absolute_positions()
        return new_item

    def as_string(self, decimals: int | None = None, minify: bool = False) -> str:
        """Serialize the entire path to an SVG path string."""
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
        """List of final absolute points for each item in the path."""
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

    def set_location(self, pt_reference: SvgPoint, to: Point) -> SvgPath:
        """
        Return a new path with the given point (target or control) moved to
        `to`. The reference must come from a previously queried point list.
        """
        new_path = self.clone()
        # Rebind to cloned items
        if isinstance(pt_reference, SvgControlPoint):
            ref_item = pt_reference.item_reference
            if ref_item in self.path:
                idx = self.path.index(ref_item)
                new_item = new_path.path[idx]
                new_item.set_control_location(pt_reference.sub_index, to)
        else:
            ref_item = pt_reference.item_reference
            if ref_item in self.path:
                idx = self.path.index(ref_item)
                new_item = new_path.path[idx]
                new_item.set_target_location(to)

        new_path.refresh_absolute_positions()
        return new_path

    def refresh_absolute_positions(self) -> None:
        """Recompute absolute positions for all items in the path."""
        previous: SvgItem | None = None
        origin = Point(0, 0)
        for item in self.path:
            item.refresh(origin, previous)
            if isinstance(item, (MoveTo, ClosePath)):
                origin = item.target_location()
            previous = item

    @override
    def __str__(self) -> str:
        return self.as_string()
