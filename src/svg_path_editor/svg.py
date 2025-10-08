import math
import re
from typing import TypedDict, final, override

from .path_parser import PathParser


def format_number(v: float, d: int, minify: bool = False) -> str:
    s = f"{v:.{d}f}"
    s = re.sub(r"^(-?[0-9]*\.([0-9]*[1-9])?)0*$", r"\1", s)
    s = re.sub(r"\.$", "", s)
    if minify:
        s = re.sub(r"^(-?)0\.", r"\1.", s)
    return s


class Point:
    def __init__(self, x: float, y: float):
        self.x: float = x
        self.y: float = y


class SvgPoint(Point):
    def __init__(self, x: float, y: float, movable: bool = True):
        super().__init__(x, y)
        self.item_reference: "SvgItem" = DummySvgItem()
        self.movable: bool = movable


class SvgControlPoint(SvgPoint):
    def __init__(self, point: Point, relations: list[Point], movable: bool = True):
        super().__init__(point.x, point.y, movable)
        self.sub_index: int = 0
        self.relations: list[Point] = relations


class SvgItem:
    def __init__(self, values: list[float], relative: bool):
        self.relative: bool = relative
        self.values: list[float] = values
        self.previous_point: Point = Point(0, 0)
        self.absolute_points: list[SvgPoint] = []
        self.absolute_control_points: list[SvgControlPoint] = []

    @staticmethod
    def make(raw_item: list[str]) -> "SvgItem":
        result: SvgItem | None = None
        relative = raw_item[0].upper() != raw_item[0]
        values = [float(it) for it in raw_item[1:]]

        mapping: dict[str, type["SvgItem"]] = {
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

        cls = mapping.get(raw_item[0].upper())
        if cls:
            result = cls(values, relative)

        if not result:
            raise ValueError("Invalid SVG item")
        return result

    @staticmethod
    def make_from(origin: "SvgItem", previous: "SvgItem", new_type: str) -> "SvgItem":
        target = origin.target_location()
        x = str(target.x)
        y = str(target.y)
        values: list[str] = []
        absolute_type = new_type.upper()
        match absolute_type:
            case MoveTo.key:
                values = [MoveTo.key, x, y]
            case LineTo.key:
                values = [LineTo.key, x, y]
            case HorizontalLineTo.key:
                values = [HorizontalLineTo.key, x]
            case VerticalLineTo.key:
                values = [VerticalLineTo.key, y]
            case ClosePath.key:
                values = [ClosePath.key]
            case CurveTo.key:
                values = [CurveTo.key, "0", "0", "0", "0", x, y]
            case SmoothCurveTo.key:
                values = [SmoothCurveTo.key, "0", "0", x, y]
            case QuadraticBezierCurveTo.key:
                values = [QuadraticBezierCurveTo.key, "0", "0", x, y]
            case SmoothQuadraticBezierCurveTo.key:
                values = [SmoothQuadraticBezierCurveTo.key, x, y]
            case EllipticalArcTo.key:
                values = [EllipticalArcTo.key, "1", "1", "0", "0", "0", x, y]
            case _:
                pass

        result = SvgItem.make(values)

        control_points = origin.absolute_control_points

        result.previous_point = previous.target_location()
        result.absolute_points = [target]
        result.reset_control_points(previous)

        if isinstance(origin, (CurveTo, SmoothCurveTo)) and isinstance(
            result, (CurveTo, SmoothCurveTo)
        ):
            if isinstance(result, CurveTo):
                result.values[0] = control_points[0].x
                result.values[1] = control_points[0].y
                result.values[2] = control_points[1].x
                result.values[3] = control_points[1].y
            if isinstance(result, SmoothCurveTo):
                result.values[0] = control_points[1].x
                result.values[1] = control_points[1].y

        if isinstance(
            origin, (QuadraticBezierCurveTo, SmoothQuadraticBezierCurveTo)
        ) and isinstance(result, QuadraticBezierCurveTo):
            result.values[0] = control_points[0].x
            result.values[1] = control_points[0].y

        if new_type != absolute_type:
            result.set_relative(True)
        return result

    def refresh_absolute_points(self, origin: Point, previous: "SvgItem | None"):
        self.previous_point = previous.target_location() if previous else Point(0, 0)
        self.absolute_points = []
        current = previous.target_location() if previous else Point(0, 0)
        if not self.relative:
            current = Point(0, 0)
        for i in range(0, len(self.values) - 1, 2):
            self.absolute_points.append(
                SvgPoint(current.x + self.values[i], current.y + self.values[i + 1])
            )

    def set_relative(self, new_relative: bool):
        if self.relative != new_relative:
            self.relative = False
            if new_relative:
                self.translate(-self.previous_point.x, -self.previous_point.y)
                self.relative = True
            else:
                self.translate(self.previous_point.x, self.previous_point.y)

    def refresh_absolute_control_points(
        self, origin: Point, previous_target: "SvgItem | None"
    ):
        self.absolute_control_points = []

    def reset_control_points(self, previous_target: "SvgItem"):
        # Does nothing by default
        pass

    def refresh(self, origin: Point, previous: "SvgItem | None"):
        self.refresh_absolute_points(origin, previous)
        self.refresh_absolute_control_points(origin, previous)
        for it in self.absolute_points:
            it.item_reference = self
        for it in self.absolute_control_points:
            it.item_reference = self

    def translate(self, x: float, y: float, force: bool = False):
        if not self.relative or force:
            for idx, val in enumerate(self.values):
                self.values[idx] = val + (x if idx % 2 == 0 else y)

    def scale(self, kx: float, ky: float):
        for idx, val in enumerate(self.values):
            self.values[idx] = val * (kx if idx % 2 == 0 else ky)

    def rotate(self, ox: float, oy: float, degrees: float, force: bool = False):
        rad = math.radians(degrees)
        cosv, sinv = math.cos(rad), math.sin(rad)
        for i in range(0, len(self.values), 2):
            px, py = self.values[i], self.values[i + 1]
            x, y = (0, 0) if self.relative and not force else (ox, oy)
            qx = x + (px - x) * cosv - (py - y) * sinv
            qy = y + (px - x) * sinv + (py - y) * cosv
            self.values[i] = qx
            self.values[i + 1] = qy

    def target_location(self) -> SvgPoint:
        return self.absolute_points[-1]

    def set_target_location(self, pts: Point):
        loc = self.target_location()
        dx, dy = pts.x - loc.x, pts.y - loc.y
        self.values[-2] += dx
        self.values[-1] += dy

    def set_control_location(self, idx: int, pts: Point):
        loc = self.absolute_points[idx]
        dx, dy = pts.x - loc.x, pts.y - loc.y
        self.values[2 * idx] += dx
        self.values[2 * idx + 1] += dy

    def control_locations(self) -> list[SvgControlPoint]:
        return self.absolute_control_points

    def get_type(self, ignore_is_relative: bool = False) -> str:
        type_key = getattr(self.__class__, "key")
        if self.relative and not ignore_is_relative:
            type_key = type_key.lower()
        return type_key

    def as_standalone_string(self) -> str:
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
        decimals: int = 4,
        minify: bool = False,
        trailing_items: list["SvgItem"] | None = None,
    ) -> str:
        trailing_items = trailing_items or []
        flattened = list(self.values)
        for it in trailing_items:
            flattened.extend(it.values)
        str_values = [format_number(it, decimals, minify) for it in flattened]
        return " ".join([self.get_type(), *str_values])


@final
class DummySvgItem(SvgItem):
    def __init__(self):
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
    ):
        if not previous_target:
            raise ValueError("Invalid path")
        self.absolute_control_points = [
            SvgControlPoint(
                self.absolute_points[0], [previous_target.target_location()]
            ),
            SvgControlPoint(self.absolute_points[1], [self.target_location()]),
        ]

    @override
    def reset_control_points(self, previous_target: SvgItem):
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
    ):
        self.absolute_control_points = []
        if isinstance(previous_target, (CurveTo, SmoothCurveTo)):
            prev_loc = previous_target.target_location()
            prev_control = previous_target.absolute_control_points[1]
            x, y = 2 * prev_loc.x - prev_control.x, 2 * prev_loc.y - prev_control.y
            pts = Point(x, y)
            self.absolute_control_points.append(SvgControlPoint(pts, [prev_loc], False))
        else:
            current = (
                previous_target.target_location() if previous_target else Point(0, 0)
            )
            pts = Point(current.x, current.y)
            self.absolute_control_points.append(SvgControlPoint(pts, [], False))
        self.absolute_control_points.append(
            SvgControlPoint(self.absolute_points[0], [self.target_location()])
        )

    @override
    def as_standalone_string(self) -> str:
        return " ".join(
            [
                "M",
                str(self.previous_point.x),
                str(self.previous_point.y),
                "C",
                str(self.absolute_control_points[0].x),
                str(self.absolute_control_points[0].y),
                str(self.absolute_control_points[1].x),
                str(self.absolute_control_points[1].y),
                str(self.absolute_points[1].x),
                str(self.absolute_points[1].y),
            ]
        )

    @override
    def reset_control_points(self, previous_target: SvgItem):
        a = previous_target.target_location()
        b = self.target_location()
        d = a if self.relative else Point(0, 0)
        self.values[0] = a.x / 3 + 2 * b.x / 3 - d.x
        self.values[1] = a.y / 3 + 2 * b.y / 3 - d.y

    @override
    def set_control_location(self, idx: int, pts: Point):
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
            raise ValueError("Invalid path")
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
        self.values[0] = a.x / 2 + b.x / 2 - d.x
        self.values[1] = a.y / 2 + b.y / 2 - d.y


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
            self.absolute_control_points = [SvgControlPoint(pts, [], False)]
        else:
            prev_loc = previous_target.target_location()
            prev_control = previous_target.absolute_control_points[0]
            x, y = 2 * prev_loc.x - prev_control.x, 2 * prev_loc.y - prev_control.y
            pts = Point(x, y)
            ctrl = SvgControlPoint(pts, [prev_loc, self.target_location()], False)
            self.absolute_control_points = [ctrl]

    @override
    def as_standalone_string(self) -> str:
        return " ".join(
            [
                "M",
                str(self.previous_point.x),
                str(self.previous_point.y),
                "Q",
                str(self.absolute_control_points[0].x),
                str(self.absolute_control_points[0].y),
                str(self.absolute_points[0].x),
                str(self.absolute_points[0].y),
            ]
        )


@final
class ClosePath(SvgItem):
    key = "Z"

    @override
    def refresh_absolute_points(self, origin: Point, previous: SvgItem | None) -> None:
        self.previous_point = previous.target_location() if previous else Point(0, 0)
        self.absolute_points = [SvgPoint(origin.x, origin.y, False)]


@final
class HorizontalLineTo(SvgItem):
    key = "H"

    @override
    def rotate(self, ox: float, oy: float, degrees: float, force: bool = False) -> None:
        if degrees == 180:
            self.values[0] = -self.values[0]

    @override
    def refresh_absolute_points(self, origin: Point, previous: SvgItem | None) -> None:
        self.previous_point = previous.target_location() if previous else Point(0, 0)
        if self.relative:
            self.absolute_points = [
                SvgPoint(self.values[0] + self.previous_point.x, self.previous_point.y)
            ]
        else:
            self.absolute_points = [SvgPoint(self.values[0], self.previous_point.y)]

    @override
    def set_target_location(self, pts: Point) -> None:
        loc = self.target_location()
        dx = pts.x - loc.x
        self.values[0] += dx


@final
class VerticalLineTo(SvgItem):
    key = "V"

    @override
    def rotate(self, ox: float, oy: float, degrees: float, force: bool = False) -> None:
        if degrees == 180:
            self.values[0] = -self.values[0]

    @override
    def translate(self, x: float, y: float, force: bool = False) -> None:
        if not self.relative:
            self.values[0] += y

    @override
    def scale(self, kx: float, ky: float) -> None:
        self.values[0] *= ky

    @override
    def refresh_absolute_points(self, origin: Point, previous: SvgItem | None) -> None:
        self.previous_point = previous.target_location() if previous else Point(0, 0)
        if self.relative:
            self.absolute_points = [
                SvgPoint(self.previous_point.x, self.values[0] + self.previous_point.y)
            ]
        else:
            self.absolute_points = [SvgPoint(self.previous_point.x, self.values[0])]

    @override
    def set_target_location(self, pts: Point) -> None:
        loc = self.target_location()
        dy = pts.y - loc.y
        self.values[0] += dy


@final
class EllipticalArcTo(SvgItem):
    key = "A"

    @override
    def translate(self, x: float, y: float, force: bool = False) -> None:
        if not self.relative:
            self.values[5] += x
            self.values[6] += y

    @override
    def rotate(self, ox: float, oy: float, degrees: float, force: bool = False) -> None:
        self.values[2] = (self.values[2] + degrees) % 360
        rad = math.radians(degrees)
        cosv, sinv = math.cos(rad), math.sin(rad)
        px, py = self.values[5], self.values[6]
        x, y = (0, 0) if (self.relative and not force) else (ox, oy)
        qx = (px - x) * cosv - (py - y) * sinv + x
        qy = (px - x) * sinv + (py - y) * cosv + y
        self.values[5] = qx
        self.values[6] = qy

    @override
    def scale(self, kx: float, ky: float) -> None:
        a, b = self.values[0], self.values[1]
        angle = math.radians(self.values[2])
        cosv, sinv = math.cos(angle), math.sin(angle)
        a = b * b * ky * ky * cosv * cosv + a * a * ky * ky * sinv * sinv
        b = 2 * kx * ky * cosv * sinv * (b * b - a * a)
        c = a * a * kx * kx * cosv * cosv + b * b * kx * kx * sinv * sinv
        f = -(a * a * b * b * kx * kx * ky * ky)
        det = b * b - 4 * a * c
        val1 = math.sqrt((a - c) * (a - c) + b * b)

        # New rotation:
        if b != 0:
            self.values[2] = math.degrees(math.atan((c - a - val1) / b))
        else:
            self.values[2] = 0 if a < c else 90

        # New radius-x, radius-y
        if det != 0:
            self.values[0] = -math.sqrt(2 * det * f * ((a + c) + val1)) / det
            self.values[1] = -math.sqrt(2 * det * f * ((a + c) - val1)) / det

        # New target
        self.values[5] *= kx
        self.values[6] *= ky

        # New sweep flag
        self.values[4] = self.values[4] if kx * ky >= 0 else 1 - self.values[4]

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
        decimals: int = 4,
        minify: bool = False,
        trailing_items: list[SvgItem] | None = None,
    ) -> str:
        trailing_items = trailing_items or []
        if not minify:
            return super().as_string(decimals, minify, trailing_items)
        else:
            str_values = [self.values, *[it.values for it in trailing_items]]
            str_values = [
                [format_number(v, decimals, minify) for v in vals]
                for vals in str_values
            ]
            str_values = [
                f"{v[0]} {v[1]} {v[2]} {v[3]}{v[4]}{v[5]} {v[6]}" for v in str_values
            ]
            return " ".join([self.get_type(), *str_values])


class _Grouped(TypedDict):
    type: str
    item: SvgItem
    trailing: list[SvgItem]


class SvgPath:
    def __init__(self, path: str) -> None:
        raw_path = PathParser.parse(path)
        self.path: list[SvgItem] = [SvgItem.make(it) for it in raw_path]
        self.refresh_absolute_positions()

    def translate(self, dx: float, dy: float) -> "SvgPath":
        for idx, it in enumerate(self.path):
            it.translate(dx, dy, idx == 0)
        self.refresh_absolute_positions()
        return self

    def scale(self, kx: float, ky: float) -> "SvgPath":
        for it in self.path:
            it.scale(kx, ky)
        self.refresh_absolute_positions()
        return self

    def rotate(self, ox: float, oy: float, degrees: float) -> "SvgPath":
        degrees %= 360
        if degrees == 0:
            return self

        for idx in range(len(self.path)):
            it = self.path[idx]
            last_instance_of = it.__class__
            if degrees != 180:
                if isinstance(it, (HorizontalLineTo, VerticalLineTo)):
                    new_type = LineTo.key.lower() if it.relative else LineTo.key
                    it = self.change_type(it, new_type) or it
                    # update local reference after change_type
                    self.path[idx] = it

            it.rotate(ox, oy, degrees, idx == 0)

            if degrees in (90, 270):
                if last_instance_of is HorizontalLineTo:
                    self.refresh_absolute_positions()
                    new_type = (
                        VerticalLineTo.key.lower()
                        if it.relative
                        else VerticalLineTo.key
                    )
                    it2 = self.change_type(it, new_type)
                    if it2 is not None:
                        self.path[idx] = it2
                        it = it2
                elif last_instance_of is VerticalLineTo:
                    self.refresh_absolute_positions()
                    new_type = (
                        HorizontalLineTo.key.lower()
                        if it.relative
                        else HorizontalLineTo.key
                    )
                    it2 = self.change_type(it, new_type)
                    if it2 is not None:
                        self.path[idx] = it2
                        it = it2

        self.refresh_absolute_positions()
        return self

    def set_relative(self, new_relative: bool) -> "SvgPath":
        for it in self.path:
            it.set_relative(new_relative)
        self.refresh_absolute_positions()
        return self

    def delete(self, item: SvgItem) -> "SvgPath":
        idx = self.path.index(item) if item in self.path else -1
        if idx != -1:
            self.path.pop(idx)
            self.refresh_absolute_positions()
        return self

    def insert(self, item: SvgItem, after: SvgItem | None = None) -> None:
        idx = self.path.index(after) if after in self.path else -1
        if idx != -1:
            self.path.insert(idx + 1, item)
        else:
            self.path.append(item)
        self.refresh_absolute_positions()

    def change_type(self, item: SvgItem, new_type: str) -> SvgItem | None:
        idx = self.path.index(item) if item in self.path else -1
        if idx > 0:
            previous = self.path[idx - 1]
            self.path[idx] = SvgItem.make_from(item, previous, new_type)
            self.refresh_absolute_positions()
            return self.path[idx]
        return None

    def as_string(self, decimals: int = 4, minify: bool = False) -> str:
        grouped: list[_Grouped] = []
        for it in self.path:
            t = it.get_type()
            if minify and len(grouped) > 0:
                last = grouped[-1]
                if last["type"] == t:
                    last["trailing"].append(it)
                    continue
            gtype = "l" if t == "m" else ("L" if t == "M" else t)
            grouped.append({"type": gtype, "item": it, "trailing": []})

        out_parts: list[str] = []
        for g in grouped:
            s = g["item"].as_string(decimals, minify, g["trailing"])
            if minify:
                s = re.sub(r"^([a-zA-Z]) ", r"\1", s)
                s = s.replace(" -", "-")
                s = re.sub(r"(\.[0-9]+) (?=\.)", r"\1", s)
            out_parts.append(s)

        return "".join(out_parts) if minify else " ".join(out_parts)

    def target_locations(self) -> list[SvgPoint]:
        return [it.target_location() for it in self.path]

    def control_locations(self) -> list[SvgControlPoint]:
        result: list[SvgControlPoint] = []
        for i in range(1, len(self.path)):
            controls = self.path[i].control_locations()
            for idx, it in enumerate(controls):
                it.sub_index = idx
            result = [*result, *controls]
        return result

    def set_location(self, pt_reference: SvgPoint, to: Point) -> None:
        if isinstance(pt_reference, SvgControlPoint):
            pt_reference.item_reference.set_control_location(pt_reference.sub_index, to)
        else:
            pt_reference.item_reference.set_target_location(to)
        self.refresh_absolute_positions()

    def refresh_absolute_positions(self) -> None:
        previous: SvgItem | None = None
        origin = Point(0, 0)
        for item in self.path:
            item.refresh(origin, previous)
            if isinstance(item, (MoveTo, ClosePath)):
                origin = item.target_location()
            previous = item
