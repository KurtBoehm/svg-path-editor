# This file is part of https://github.com/KurtBoehm/svg-path-editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from typing import Callable, Final, NotRequired, TypedDict

import pytest

from svg_path_editor import SvgPath, Point, round_corners


class RoundTestCase(TypedDict):
    name: str
    path: str
    expected: str
    selector: NotRequired[Callable[[Point, Point, Point], bool]]


test_cases: Final[list[RoundTestCase]] = [
    {
        "name": "triangle_s0.15",
        "path": "M 0 0 L 0.15 0.15 H 0 Z",
        "expected": "M 0 0 L 0.15 0.15 H 0.1 A 0.1 0.1 0 0 1 0 0.05 Z",
    },
    {
        "name": "triangle_s1",
        "path": "M 0 0 L 1 1 H 0 Z",
        "expected": (
            "M 0 0.2414213562373095048801688724 "
            "A 0.1 0.1 0 0 1 0.1707106781186547524400844362 0.1707106781186547524400844362 "
            "L 0.8292893218813452475599155638 0.8292893218813452475599155638 "
            "A 0.1 0.1 0 0 1 0.7585786437626904951198311276 1 H 0.1 "
            "A 0.1 0.1 0 0 1 0 0.9 Z"
        ),
    },
    {
        "name": "triangle_s1_select",
        "path": "M 0 0 L 1 1 H 0 Z",
        "expected": (
            "M 0 0 L 0.8292893218813452475599155638 0.8292893218813452475599155638 "
            "A 0.1 0.1 0 0 1 0.7585786437626904951198311276 1 H 0.1 "
            "A 0.1 0.1 0 0 1 0 0.9 Z"
        ),
        "selector": lambda a, b, c: b != Point(0, 0),
    },
    {
        "name": "triangle_s2",
        "path": "M 0 0 l 2 2 L 0 2 Z",
        "expected": (
            "M 0 0.2414213562373095048801688724 "
            "A 0.1 0.1 0 0 1 0.1707106781186547524400844362 0.1707106781186547524400844362 "
            "L 1.829289321881345247559915564 1.829289321881345247559915564 "
            "A 0.1 0.1 0 0 1 1.758578643762690495119831128 2 L 0.1 2 "
            "A 0.1 0.1 0 0 1 0 1.9 Z"
        ),
    },
    {
        "name": "triangle_with_dummy_h",
        "path": "M 0 0 H 0 H 1 V 1 Z",
        "expected": (
            "M 0 0 H 0 H 0.9 A 0.1 0.1 0 0 1 1 0.1 V 0.7585786437626904951198311276 "
            "A 0.1 0.1 0 0 1 0.8292893218813452475599155638 0.8292893218813452475599155638 Z"
        ),
    },
    {
        "name": "quarter_circle_r2",
        "path": "M 0 0 a 2 2 45 0 1 2 2 L 0 2 Z",
        "expected": "M 0 0 A 2 2 45 0 1 2 2 L 0.1 2 A 0.1 0.1 0 0 1 0 1.9 Z",
    },
    {
        "name": "rect_2x1_with_right_bulge",
        "path": "M 0 0 h 1 a 2 3 32 0 1 0 2 L 0 2 Z",
        "expected": (
            "M 0 0.1 A 0.1 0.1 0 0 1 0.1 0 H 1 A 2 3 32 0 1 1 2 L 0.1 2 "
            "A 0.1 0.1 0 0 1 0 1.9 Z"
        ),
    },
    {
        "name": "square_3x3_rounded_ur",
        "path": "M 0 0 h 1 a 2 2 0 0 1 2 2 v 1 L 0 3 Z",
        "expected": (
            "M 0 0.1 A 0.1 0.1 0 0 1 0.1 0 H 1 A 2 2 0 0 1 3 2 V 2.9 "
            "A 0.1 0.1 0 0 1 2.9 3 L 0.1 3 A 0.1 0.1 0 0 1 0 2.9 Z"
        ),
    },
    {
        "name": "square_3x3_rounded_ur_split_edge",
        "path": "M 0 0 h 1 a 2 2 0 0 1 2 2 v 1 L 2 3 L 0 3 Z",
        "expected": (
            "M 0 0.1 A 0.1 0.1 0 0 1 0.1 0 H 1 A 2 2 0 0 1 3 2 V 2.9 "
            "A 0.1 0.1 0 0 1 2.9 3 L 2 3 A 0.1 0.1 0 0 0 2 3 L 0.1 3 "
            "A 0.1 0.1 0 0 1 0 2.9 Z"
        ),
    },
    {
        "name": "L_with_outer_bulge",
        "path": "M 0 0 h 1 v1 a 1 1 0 0 1 1 1 h 1 v 1 L 0 3 Z",
        "expected": (
            "M 0 0.1 A 0.1 0.1 0 0 1 0.1 0 H 0.9 A 0.1 0.1 0 0 1 1 0.1 V 1 "
            "A 1 1 0 0 1 2 2 H 2.9 A 0.1 0.1 0 0 1 3 2.1 V 2.9 A 0.1 0.1 0 0 1 2.9 3 "
            "L 0.1 3 A 0.1 0.1 0 0 1 0 2.9 Z"
        ),
    },
    {
        "name": "half_circle_r2_split_arcs",
        "path": "M 0 0 a 1 1 0 0 1 1 1 a 1 1 45 0 1 -1 1 Z",
        "expected": "M 0 0 A 1 1 0 0 1 1 1 A 1 1 45 0 1 0 2 Z",
    },
    {
        "name": "half_circle_plus_half_ellipse",
        "path": "M 0 0 a 1 1 0 0 1 1 1 a 1 2 0 0 1 -1 2 Z",
        "expected": "M 0 0 A 1 1 0 0 1 1 1 A 1 2 0 0 1 0 3 Z",
    },
    {
        "name": "L_with_two_bulges_different_radii",
        "path": "M 0 0 h 1 v 1 a 1 0.5 45 0 1 1 1 a 1 1 0 0 1 1 1 h 1 v 1 L 0 4 Z",
        "expected": (
            "M 0 0.1 A 0.1 0.1 0 0 1 0.1 0 H 0.9 A 0.1 0.1 0 0 1 1 0.1 V 1 "
            "A 1 0.5 45 0 1 2 2 A 1 1 0 0 1 3 3 H 3.9 A 0.1 0.1 0 0 1 4 3.1 V 3.9 "
            "A 0.1 0.1 0 0 1 3.9 4 L 0.1 4 A 0.1 0.1 0 0 1 0 3.9 Z"
        ),
    },
    {
        "name": "L_with_two_bulges_same_radius",
        "path": "M 0 0 h 1 v 1 a 1 1 45 0 1 1 1 a 1 1 0 0 1 1 1 h 1 v 1 L 0 4 Z",
        "expected": (
            "M 0 0.1 A 0.1 0.1 0 0 1 0.1 0 H 0.9 A 0.1 0.1 0 0 1 1 0.1 V 1 "
            "A 1 1 45 0 1 2 2 A 1 1 0 0 1 3 3 H 3.9 A 0.1 0.1 0 0 1 4 3.1 V 3.9 "
            "A 0.1 0.1 0 0 1 3.9 4 L 0.1 4 A 0.1 0.1 0 0 1 0 3.9 Z"
        ),
    },
    {
        "name": "double_loop_B_shape",
        "path": "M 0 0 a 1 1 0 0 1 0 2 a 1 1 0 0 1 0 2 h -1 V 0 Z",
        "expected": (
            "M 0 0 A 1 1 0 0 1 0 2 A 1 1 0 0 1 0 4 H -0.9 A 0.1 0.1 0 0 1 -1 3.9 V 0.1 "
            "A 0.1 0.1 0 0 1 -0.9 0 Z"
        ),
    },
    {
        "name": "square_2x2_with_horizontal_slot",
        "path": "M 0 0 h 2 v 1 h -1 h 1 v 1 h -2 Z",
        "expected": (
            "M 0 0.1 A 0.1 0.1 0 0 1 0.1 0 H 1.9 A 0.1 0.1 0 0 1 2 0.1 V 0.9 "
            "A 0.1 0.1 0 0 1 1.9 1 H 1 H 1.9 A 0.1 0.1 0 0 1 2 1.1 V 1.9 "
            "A 0.1 0.1 0 0 1 1.9 2 H 0.1 A 0.1 0.1 0 0 1 0 1.9 Z"
        ),
    },
    {
        "name": "square_2x2_with_vertical_slot",
        "path": "M 0 0 h 1 v 1 v -1 h 1 v 2 h -2 Z",
        "expected": (
            "M 0 0.1 A 0.1 0.1 0 0 1 0.1 0 H 0.9 A 0.1 0.1 0 0 1 1 0.1 V 1 V 0.1 "
            "A 0.1 0.1 0 0 1 1.1 0 H 1.9 A 0.1 0.1 0 0 1 2 0.1 V 1.9 "
            "A 0.1 0.1 0 0 1 1.9 2 H 0.1 A 0.1 0.1 0 0 1 0 1.9 Z"
        ),
    },
    {
        "name": "square_2x2_top_cut_with_rounded_top",
        "path": "M 0 0 h 2 a 1 1 0 0 1 -1 1 h 1 v 1 h -2 Z",
        "expected": (
            "M 0 0.1 A 0.1 0.1 0 0 1 0.1 0 H 2 A 1 1 0 0 1 1 1 H 1.9 "
            "A 0.1 0.1 0 0 1 2 1.1 V 1.9 A 0.1 0.1 0 0 1 1.9 2 H 0.1 "
            "A 0.1 0.1 0 0 1 0 1.9 Z"
        ),
    },
    {
        "name": "square_2x2_middle_cut_with_rounded_bottom",
        "path": "M 0 0 h 2 v 1 h -1 a 1 1 0 0 1 1 1 h -2 Z",
        "expected": (
            "M 0 0.1 A 0.1 0.1 0 0 1 0.1 0 H 1.9 A 0.1 0.1 0 0 1 2 0.1 V 0.9 "
            "A 0.1 0.1 0 0 1 1.9 1 H 1 A 1 1 0 0 1 2 2 H 0.1 A 0.1 0.1 0 0 1 0 1.9 Z"
        ),
    },
    {
        "name": "square_2x2_single_concave_cut",
        "path": "M 0 0 h 1 a 1 1 0 0 0 1 1 v 1 h -2 Z",
        "expected": (
            "M 0 0.1 A 0.1 0.1 0 0 1 0.1 0 H 1 A 1 1 0 0 0 2 1 V 1.9 "
            "A 0.1 0.1 0 0 1 1.9 2 H 0.1 A 0.1 0.1 0 0 1 0 1.9 Z"
        ),
    },
    {
        "name": "square_2x2_single_convex_cut",
        "path": "M 0 0 h 1 a 1 1 0 0 1 1 1 v 1 h -2 Z",
        "expected": (
            "M 0 0.1 A 0.1 0.1 0 0 1 0.1 0 H 1 A 1 1 0 0 1 2 1 V 1.9 "
            "A 0.1 0.1 0 0 1 1.9 2 H 0.1 A 0.1 0.1 0 0 1 0 1.9 Z"
        ),
    },
    {
        "name": "square_2x2_two_concave_cuts",
        "path": "M 0 0 h 1 a 1 1 0 0 0 1 1 a 1 1 0 0 0 -1 1 H 0 Z",
        "expected": (
            "M 0 0.1 A 0.1 0.1 0 0 1 0.1 0 H 1 A 1 1 0 0 0 2 1 A 1 1 0 0 0 1 2 H 0.1 "
            "A 0.1 0.1 0 0 1 0 1.9 Z"
        ),
    },
    {
        "name": "square_2x2_concave_cut_upwards",
        "path": "M 0 0 h 1 a 1 1 0 0 1 1 -1 v -1 h -2 Z",
        "expected": (
            "M 0 -0.1 A 0.1 0.1 0 0 0 0.1 0 H 1 A 1 1 0 0 1 2 -1 V -1.9 "
            "A 0.1 0.1 0 0 0 1.9 -2 H 0.1 A 0.1 0.1 0 0 0 0 -1.9 Z"
        ),
    },
    {
        "name": "square_2x2_bulbous_outgrowth",
        "path": "M 0 0 h 1 a 1 1 0 1 1 1 1 v 1 h -2 Z",
        "expected": (
            "M 0 0.1 A 0.1 0.1 0 0 1 0.1 0 H 1 A 1 1 0 1 1 2 1 V 1.9 "
            "A 0.1 0.1 0 0 1 1.9 2 H 0.1 A 0.1 0.1 0 0 1 0 1.9 Z"
        ),
    },
    {
        "name": "square_2x2_bulbous_outgrowth_ccw",
        "path": "M 0 2 H 2 V 1 A 1 1 0 1 0 1 0 H 0 Z",
        "expected": (
            "M 0 1.9 A 0.1 0.1 0 0 0 0.1 2 H 1.9 A 0.1 0.1 0 0 0 2 1.9 "
            "V 1 A 1 1 0 1 0 1 0 H 0.1 A 0.1 0.1 0 0 0 0 0.1 Z"
        ),
    },
    {
        "name": "square_2x3_with_large_concave_cut",
        "path": "M 0 3 h 3 v -2 a 1 1 0 1 1 -1 -1 h -2 Z",
        "expected": (
            "M 0 2.9 A 0.1 0.1 0 0 0 0.1 3 H 2.9 A 0.1 0.1 0 0 0 3 2.9 V 1 "
            "A 1 1 0 1 1 2 0 H 0.1 A 0.1 0.1 0 0 0 0 0.1 Z"
        ),
    },
    {
        "name": "claw",
        "path": "m 5 0 a 5 10 0 0 0 5 10 a 5 5 0 0 1 5 -5 z",
        "expected": "M 5 0 A 5 10 0 0 0 10 10 A 5 5 0 0 1 15 5 Z",
    },
    {
        "name": "complex",
        "path": (
            "M 5 0 A 5 5 0 0 0 0 5 "
            "A 5 10 0 0 0 5 15 a 5 5 0 0 1 5 -5 "
            "V 5 H 5 a 5 5 0 0 0 5 -5 Z"
        ),
        "expected": (
            "M 5 0 A 5 5 0 0 0 0 5 A 5 10 0 0 0 5 15 A 5 5 0 0 1 10 10 V 5.1 "
            "A 0.1 0.1 0 0 0 9.9 5 H 5 A 5 5 0 0 0 10 0 Z"
        ),
    },
]


@pytest.mark.parametrize("test_case", test_cases, ids=[c["name"] for c in test_cases])
def test_round_corners(test_case: RoundTestCase) -> None:
    path = SvgPath(test_case["path"])
    expected = test_case["expected"]
    selector = test_case.get("selector", lambda a, b, c: True)

    rounded = round_corners(path, radius="0.1", selector=selector)
    assert str(rounded) == expected


def test_round_corners_negative() -> None:
    path = SvgPath("M 0 0 Z")
    with pytest.raises(ValueError):
        round_corners(path, radius=-1)
    assert str(round_corners(path, radius=1)) == str(path)
