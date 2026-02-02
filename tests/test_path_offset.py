from __future__ import annotations

from typing import Final, Literal, NotRequired, TypedDict

import pytest

import svg_path_editor
from svg_path_editor import SvgPath
from svg_path_editor.path_offset import offset_path


class InsetTestCase(TypedDict):
    name: str
    path: str
    expected: str
    prec: NotRequired[Literal["auto-intersections"]]
    min_additional_digits: NotRequired[int]


test_cases: Final[list[InsetTestCase]] = [
    {
        "name": "triangle_offset_s1",
        "path": "M 0 0 L 1 1 H 0 Z",
        "expected": (
            "M 0.1 0.2414213562373095048801688724 L 0.7585786437626904951198311276 0.9 "
            "L 0.1 0.9 Z"
        ),
    },
    {
        "name": "triangle_offset_s2",
        "path": "M 0 0 l 2 2 L 0 2 Z",
        "expected": (
            "M 0.1 0.2414213562373095048801688724 L 1.758578643762690495119831128 1.9 "
            "L 0.1 1.9 Z"
        ),
    },
    {
        "name": "quarter_circle_r2",
        "path": "M 0 0 a 2 2 45 0 1 2 2 L 0 2 Z",
        "expected": (
            "M 0.1 0.1026334038989724008006638733 "
            "A 1.9 1.9 45 0 1 1.897366596101027599199336127 1.9 L 0.1 1.9 Z"
        ),
    },
    {
        "name": "rect_2x1_with_right_bulge",
        "path": "M 0 0 h 1 a 2 3 32 0 1 0 2 L 0 2 Z",
        "expected": (
            "M 0.1 0.1 L 0.9357124499406418214735029256 0.1 "
            "A 1.9 2.9 32 0 1 0.9275812294334963384228272808 1.9 L 0.1 1.9 Z"
        ),
        "prec": "auto-intersections",
    },
    {
        "name": "square_3x3_rounded_ur",
        "path": "M 0 0 h 1 a 2 2 0 0 1 2 2 v 1 L 0 3 Z",
        "expected": "M 0.1 0.1 L 1 0.1 A 1.9 1.9 0 0 1 2.9 2 L 2.9 2.9 L 0.1 2.9 Z",
    },
    {
        "name": "square_3x3_rounded_ur_split_edge",
        "path": "M 0 0 h 1 a 2 2 0 0 1 2 2 v 1 L 2 3 L 0 3 Z",
        "expected": (
            "M 0.1 0.1 L 1 0.1 A 1.9 1.9 0 0 1 2.9 2 L 2.9 2.9 L 2 2.9 L 0.1 2.9 Z"
        ),
    },
    {
        "name": "L_with_outer_bulge",
        "path": "M 0 0 h 1 v1 a 1 1 0 0 1 1 1 h 1 v 1 L 0 3 Z",
        "expected": (
            "M 0.1 0.1 L 0.9 0.1 L 0.9 1.1 L 1 1.1 A 0.9 0.9 0 0 1 1.9 2 L 1.9 2.1 "
            "L 2.9 2.1 L 2.9 2.9 L 0.1 2.9 Z"
        ),
    },
    {
        "name": "half_circle_r2_split_arcs",
        "path": "M 0 0 a 1 1 0 0 1 1 1 a 1 1 45 0 1 -1 1 Z",
        "expected": (
            "M 0.1 0.1055728090000841214363305325 A 0.9 0.9 0 0 1 0.9 1 "
            "A 0.9 0.9 45 0 1 0.1 1.894427190999915878563669467 Z"
        ),
    },
    {
        "name": "half_circle_plus_half_ellipse",
        "path": "M 0 0 a 1 1 0 0 1 1 1 a 1 2 0 0 1 -1 2 Z",
        "expected": (
            "M 0.1 0.1055728090000841214363305325 A 0.9 0.9 0 0 1 0.9 1 "
            "A 0.9 1.9 0 0 1 0.1 2.888235180999822410301079987 Z"
        ),
    },
    {
        "name": "L_with_two_bulges_different_radii",
        "path": "M 0 0 h 1 v 1 a 1 0.5 45 0 1 1 1 a 1 1 0 0 1 1 1 h 1 v 1 L 0 4 Z",
        "expected": (
            "M 0.1 0.1 L 0.9 0.1 L 0.9 1.061538461538461538461538462 L 1 1.1 "
            "A 0.9 0.4 45 0 1 1.9 2 L 1.938461538461538461538461538 2.1 L 2 2.1 "
            "A 0.9 0.9 0 0 1 2.9 3 L 2.9 3.1 L 3.9 3.1 L 3.9 3.9 L 0.1 3.9 Z"
        ),
        "prec": "auto-intersections",
    },
    {
        "name": "L_with_two_bulges_same_radius",
        "path": "M 0 0 h 1 v 1 a 1 1 45 0 1 1 1 a 1 1 0 0 1 1 1 h 1 v 1 L 0 4 Z",
        "expected": (
            "M 0.1 0.1 L 0.9 0.1 L 0.9 1.1 L 1 1.1 A 0.9 0.9 45 0 1 1.9 2 L 1.9 2.1 "
            "L 2 2.1 A 0.9 0.9 0 0 1 2.9 3 L 2.9 3.1 L 3.9 3.1 L 3.9 3.9 L 0.1 3.9 Z"
        ),
    },
    {
        "name": "double_loop_B_shape",
        "path": "M 0 0 a 1 1 0 0 1 0 2 a 1 1 0 0 1 0 2 h -1 V 0 Z",
        "expected": (
            "M 0 0.1 A 0.9 0.9 0 0 1 0 1.9 L -0.1 1.9 L -0.1 2.1 L 0 2.1 "
            "A 0.9 0.9 0 0 1 0 3.9 L -0.9 3.9 L -0.9 0.1 Z"
        ),
    },
    {
        "name": "square_2x2_with_horizontal_slot",
        "path": "M 0 0 h 2 v 1 h -1 h 1 v 1 h -2 Z",
        "expected": (
            "M 0.1 0.1 L 1.9 0.1 L 1.9 0.9 L 0.9 0.9 L 0.9 1.1 L 1.9 1.1 L 1.9 1.9 "
            "L 0.1 1.9 Z"
        ),
    },
    {
        "name": "square_2x2_with_vertical_slot",
        "path": "M 0 0 h 1 v 1 v -1 h 1 v 2 h -2 Z",
        "expected": (
            "M 0.1 0.1 L 0.9 0.1 L 0.9 1.1 L 1.1 1.1 L 1.1 0.1 L 1.9 0.1 L 1.9 1.9 "
            "L 0.1 1.9 Z"
        ),
    },
    {
        "name": "square_2x2_top_cut_with_rounded_top",
        "path": "M 0 0 h 2 a 1 1 0 0 1 -1 1 h 1 v 1 h -2 Z",
        "expected": (
            "M 0.1 0.1 L 1.894427190999915878563669467 0.1 A 0.9 0.9 0 0 1 1 0.9 "
            "L 0.9 0.9 L 0.9 1.1 L 1.9 1.1 L 1.9 1.9 L 0.1 1.9 Z"
        ),
    },
    {
        "name": "square_2x2_middle_cut_with_rounded_bottom",
        "path": "M 0 0 h 2 v 1 h -1 a 1 1 0 0 1 1 1 h -2 Z",
        "expected": (
            "M 0.1 0.1 L 1.9 0.1 L 1.9 0.9 L 0.9 0.9 L 0.9 1.1 L 1 1.1 "
            "A 0.9 0.9 0 0 1 1.894427190999915878563669467 1.9 L 0.1 1.9 Z"
        ),
    },
    {
        "name": "square_2x2_single_concave_cut",
        "path": "M 0 0 h 1 a 1 1 0 0 0 1 1 v 1 h -2 Z",
        "expected": (
            "M 0.1 0.1 L 0.9045548849896677730860604344 0.1 "
            "A 1.1 1.1 0 0 0 1.9 1.095445115010332226913939566 L 1.9 1.9 L 0.1 1.9 Z"
        ),
    },
    {
        "name": "square_2x2_single_convex_cut",
        "path": "M 0 0 h 1 a 1 1 0 0 1 1 1 v 1 h -2 Z",
        "expected": ("M 0.1 0.1 L 1 0.1 A 0.9 0.9 0 0 1 1.9 1 L 1.9 1.9 L 0.1 1.9 Z"),
    },
    {
        "name": "square_2x2_two_concave_cuts",
        "path": "M 0 0 h 1 a 1 1 0 0 0 1 1 a 1 1 0 0 0 -1 1 H 0 Z",
        "expected": (
            "M 0.1 0.1 L 0.9045548849896677730860604344 0.1 "
            "A 1.1 1.1 0 0 0 1.541742430504415999341195281 1 "
            "A 1.1 1.1 0 0 0 0.9045548849896677730860604344 1.9 L 0.1 1.9 Z"
        ),
    },
    {
        "name": "square_2x2_concave_cut_upwards",
        "path": "M 0 0 h 1 a 1 1 0 0 1 1 -1 v -1 h -2 Z",
        "expected": (
            "M 0.1 -0.1 L 0.9045548849896677730860604344 -0.1 "
            "A 1.1 1.1 0 0 1 1.9 -1.095445115010332226913939566 L 1.9 -1.9 L 0.1 -1.9 Z"
        ),
    },
    {
        "name": "square_2x2_bulbous_outgrowth",
        "path": "M 0 0 h 1 a 1 1 0 1 1 1 1 v 1 h -2 Z",
        "expected": (
            "M 0.1 0.1 L 1.1 0.1 L 1.1 0 A 0.9 0.9 0 1 1 2 0.9 L 1.9 0.9 L 1.9 1.9 "
            "L 0.1 1.9 Z"
        ),
    },
    {
        "name": "square_2x2_bulbous_outgrowth_ccw",
        "path": "M 0 2 H 2 V 1 A 1 1 0 1 0 1 0 H 0 Z",
        "expected": (
            "M 0.1 1.9 L 1.9 1.9 L 1.9 0.9 L 2 0.9 A 0.9 0.9 0 1 0 1.1 0 L 1.1 0.1 "
            "L 0.1 0.1 Z"
        ),
    },
    {
        "name": "square_2x3_with_large_concave_cut",
        "path": "M 0 3 h 3 v -2 a 1 1 0 1 1 -1 -1 h -2 Z",
        "expected": (
            "M 0.1 2.9 L 2.9 2.9 L 2.9 1.632455532033675866399778709 "
            "A 1.1 1.1 0 1 1 1.367544467966324133600221291 0.1 L 0.1 0.1 Z"
        ),
    },
    {
        "name": "claw",
        "path": "m 5 0 a 5 10 0 0 0 5 10 a 5 5 0 0 1 5 -5 z",
        "expected": (
            "M 5.10065714642350860777466057 0.1621319720867437887077889683 "
            "A 4.9 9.9 0 0 0 9.901020501811487572306428683 9.897980016402540094757467376 "
            "A 5.1 5.1 0 0 1 14.60675958521542240111475456 4.915183191482700685377835966 Z"
        ),
        "prec": "auto-intersections",
    },
    {
        "name": "complex",
        "path": (
            "M 5 0 A 5 5 0 0 0 0 5 "
            "A 5 10 0 0 0 5 15 a 5 5 0 0 1 5 -5 "
            "V 5 H 5 a 5 5 0 0 0 5 -5 Z"
        ),
        "expected": (
            "M 5 0.1 A 4.9 4.9 0 0 0 0.1 5 "
            "A 4.9 9.9 0 0 0 4.901020501811487572306428683 14.89798001640254009475746738 "
            "A 5.1 5.1 0 0 1 9.9 9.900980486407215169971775891 "
            "L 9.9 5.1 L 4.9 5.1 L 4.9 4.9 L 5 4.9 "
            "A 4.9 4.9 0 0 0 9.89897948556635619639456815 0.1 Z"
        ),
        "prec": "auto-intersections",
        "min_additional_digits": 6,
    },
]


@pytest.mark.parametrize("test_case", test_cases, ids=[c["name"] for c in test_cases])
def test_inset_path(test_case: InsetTestCase) -> None:
    path = SvgPath(test_case["path"])
    prec = test_case.get("prec", None)
    expected = test_case["expected"]
    min_additional_digits = test_case.get("additional_digits", 8)

    additional_digits = svg_path_editor.path_offset.additional_digits

    for d in [4, 6, 8]:
        if d < min_additional_digits:
            continue

        if prec is None:
            inset = offset_path(path, d="0.1")
            assert str(inset) == expected

        if prec is None or prec == "auto-intersections":
            inset = offset_path(path, d="0.1", prec="auto-intersections")
            assert str(inset) == expected

        inset = offset_path(path, d="0.1", prec="auto")
        assert str(inset) == expected

    svg_path_editor.path_offset.additional_digits = additional_digits
