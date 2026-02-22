from typing import Final, Literal, NotRequired, TypedDict

import pytest

import svg_path_editor
from svg_path_editor import PNG, WEBP, ImageFormat, PathShading, SvgPath, shade_path


class ShadeTestCase(TypedDict):
    name: str
    path: str
    expected: str
    prec: NotRequired[Literal["auto-intersections"]]
    min_additional_digits: NotRequired[int]
    format: NotRequired[ImageFormat]


test_cases: Final[list[ShadeTestCase]] = [
    {
        "name": "triangle_offset_s1",
        "path": "M 0 0 L 1 1 H 0 Z",
        "expected": (
            '<path fill="white" opacity="0.805" d="M 0 0 L 1 1 L 0.7585786437626904951198311276 0.9 L 0.1 0.2414213562373095048801688724 Z"/>\n'
            '<path fill="black" opacity="1" d="M 1 1 L 0 1 L 0.1 0.9 L 0.7585786437626904951198311276 0.9 Z"/>\n'
            '<path fill="white" opacity="0.333" d="M 0 1 L 0 0 L 0.1 0.2414213562373095048801688724 L 0.1 0.9 Z"/>'
        ),
    },
    {
        "name": "triangle_offset_s2",
        "path": "M 0 0 l 2 2 L 0 2 Z",
        "expected": (
            '<path fill="white" opacity="0.805" d="M 0 0 L 2 2 L 1.758578643762690495119831128 1.9 L 0.1 0.2414213562373095048801688724 Z"/>\n'
            '<path fill="black" opacity="1" d="M 2 2 L 0 2 L 0.1 1.9 L 1.758578643762690495119831128 1.9 Z"/>\n'
            '<path fill="white" opacity="0.333" d="M 0 2 L 0 0 L 0.1 0.2414213562373095048801688724 L 0.1 1.9 Z"/>'
        ),
    },
    {
        "name": "quarter_circle_r2",
        "path": "M 0 0 a 2 2 45 0 1 2 2 L 0 2 Z",
        "expected": (
            "<defs>\n"
            '<image id="shade0" width="4" height="4" preserveAspectRatio="none" href="data:image/webp;base64,UklGRkACAABXRUJQVlA4TDQCAAAvH8AHEE2oaduAScdZ/pRLIaL/2T2DhDaSBEly8wd9d1/zHCIjJEmSpNhVVM2ImZm11c3+qXQgrbX/zPxmGqpyAn4AgZKb0NUUVZkps0WZzClN3fBNKEarluSCUIRLh0AxVASSaIwgYxFaqxotjJBkBNmYZBRGK3zSMAIhmWCSCUagofrP3SHJRJIFGmhNhuiwaiRLgCCriDUQorO1kkxQK1CsbUHE2oljNJEUkIsQqzYdrcaJb4iS+gQVG2prooihODY+Si8pGGpbfKSN1tA2vqYLtUDsE20aoVptM/KkSZkEB2dtvdF6KiJEKGaYZSP547cGnjHDc1s2rRvlFBQFAgVDNix55zNZtsLejgO71jSxySkECrLRJmD06Ll36cmpPZPZpCcmj2SV3HRN8ddbz0+OvXj11S8LRUsXcpsJrdEmppr89gWOvbGjmxVdFUkhRzPTXUcb3qUXu25sW4IkATnamAWiSm5CClj25FWzY9uqZcapQCBppsKorcAtO/dZMVqzammMowgjswQVqAIzzK4/CizNsqHYMAoWLAokUYz3di2mETNaMnAD41jLTJIPhMsNDsyKJnnMaGC8gdPMoHBpHNyuouoU4wZe4MNmRgRCcYw/s6bpYmAchvEtcDLTQGtomy1VT1AMHHwNHFMYNVyO2RS6FFQMfIEPm1JFDBuNW5diciCwOPiwpRIYDbXtjUad5Aqx2hbH1D7ZatYlCVljYXGCAV+sassaieQCIVZ8NAw="/>\n'
            "</defs>\n"
            '<clipPath id="arc0"><path d="M 0 0 a 2 2 45 0 1 2 2 L 1.897366596101027599199336127 1.9 A 1.9 1.9 45 0 0 0.1 0.1026334038989724008006638733 Z"/></clipPath>\n'
            '<g clip-path="url(#arc0)"><use href="#shade0" transform="translate(-2 0) rotate(45 2 2)"/></g>\n'
            '<path fill="black" opacity="1" d="M 2 2 L 0 2 L 0.1 1.9 L 1.897366596101027599199336127 1.9 Z"/>\n'
            '<path fill="white" opacity="0.333" d="M 0 2 L 0 0 L 0.1 0.1026334038989724008006638733 L 0.1 1.9 Z"/>'
        ),
    },
    {
        "name": "rect_2x1_with_right_bulge",
        "path": "M 0 0 h 1 a 2 3 32 0 1 0 2 L 0 2 Z",
        "expected": (
            "<defs>\n"
            '<image id="shade0" width="4" height="6" preserveAspectRatio="none" href="data:image/webp;base64,UklGRuACAABXRUJQVlA4TNMCAAAvH8ALEE0oatsGerW7Mv6IyyGi/2lBkU9aKDaS5EiScvSXaiR70vM6eB1pRB/LPOqo+cUggm0AACh0dzcPGB3hQhf4wBFOMNUB3W0C/hoL6i64C2yhvqn7quN9bbW+1fL29vNn7e/rfD7ruqYfiqI6UD8hkgimPTRqt5IQQ5BopvvsPg+tYghjeJxp+wjS3YYhjBANpvts+8SHnTAEiEQY2+7zBO1uYAgEefioG9H2rDckxAAeItpAA4YcDUdxA0pjFMJMSDQCOAjQICKTTCQY0dkGjwcZd5JgFMABQRAVNjsQRIxsCCAoDaknkzQCdFwBUMBGZu9gDu3IJgEiaMuenVFooDkYYgTPzr4mRkUEdwwQ0ujp+rGi/QBhB0iEYJ9ez0GVVsBLAg5JYyGv9z/Hs21EkU0gITBYaGEf3jjPbhtB2QMEkmR4FVPth/PredoqRi5JTJhMdkqschdd+PlqFRV2YsKEmXV9Piv/XsSrvYHn2ac05yUJITOznjVUdkvuzR24I3f0jn0sdM8OwywCQ5LZq47qqrinhfysv6BXwa/Zk+MVkx4ms6+r1ptdUQUDffZMZphsBpJksue5Ki66rBdiwTuTDFwAQ5iZNVRY3PevRM2QgVkhhAyZieUV/+mrhh42SViQcUxmyA0u6dP/hRkJyZik7mDIkVh2DcUWVWg7cWKSuEgMYQ7l1lybf/4UfBoIgbkMiQNES/38rO/P66USCHERYAgxlvy5rgL61WcjAciKIRBI39h8XnOe3a1ACCsEiEFK+bF+QL9axPSYFQMhki5h/ah3+ihiDJchGECe19rBblsM4CKSSPSGv9beSbdNg2B2IDzMc9aeoG2nAeMlMRDp/2fWBFpbxMACghEods+eoIqNkewQHYEbVMTsyWDaNtKRZQxH38/OTKARpYnsEeKDzM6BFhvSccl/UNSwh4M0GiWbhA7I+9nJEDrSUaMA"/>\n'
            "</defs>\n"
            '<path fill="white" opacity="1" d="M 0 0 L 1 0 L 0.9357124499406418214735029256 0.1 L 0.1 0.1 Z"/>\n'
            '<clipPath id="arc0"><path d="M 1 0 a 2 3 32 0 1 0 2 L 0.9275812294334963384228272808 1.9 A 1.9 2.9 32 0 0 0.9357124499406418214735029256 0.1 Z"/></clipPath>\n'
            '<g clip-path="url(#arc0)"><use href="#shade0" transform="translate(-3.143093565969665228925113935 -1.108912829834606313636519963) rotate(32 2 3)"/></g>\n'
            '<path fill="black" opacity="1" d="M 1 2 L 0 2 L 0.1 1.9 L 0.9275812294334963384228272808 1.9 Z"/>\n'
            '<path fill="white" opacity="0.333" d="M 0 2 L 0 0 L 0.1 0.1 L 0.1 1.9 Z"/>'
        ),
        "prec": "auto-intersections",
    },
    {
        "name": "square_3x3_rounded_ur",
        "path": "M 0 0 h 1 a 2 2 0 0 1 2 2 v 1 L 0 3 Z",
        "expected": (
            "<defs>\n"
            '<image id="shade0" width="4" height="4" preserveAspectRatio="none" href="data:image/webp;base64,UklGRngCAABXRUJQVlA4TGwCAAAvH8AHEE0oaNuG6f7nz3gYIvqfFCL73BoctI0kSW7+oPc+HYZUhNxItlXbmb3OOQ8+M8iVJXnoKQNlokgUkNIgi2xmfvfRPXtNwPNc3TT1JymCBk7qm/GnrbHUaao2VXzThlEKVUOrbLUfo0S1bZVCrYY1W21TNZOJUWvYSKFq2Lhgq2oz2SLRlBGolIqGGiMbTTXRVpRQRm1KapQiBk4ONqq2mZiaQNCUhlEpbQOD5bJWNdUkUxNBU6iauk0hgeR4gxUSjFoEWojBeuDw24rBIiwCLdDkxi2a4KFZIka8QKBUAanLMZpoTGOD0EVIEoNSImzGcUi0mGApBVeQFamaCt1al7H4HVmAK0heYNXMHAZrPVYEgbAtC0aS13Sj3EydCd+shaJSihiFZpFkbNOl0cbKwn/X7LM9u6apilAFgQaDZIw3fbbWBj+9upl4lm47saeaKBO0MLJgSG6bbrSxuvTYHb6XnjwyTVUSNNBgEVey6dJ4tzzyzQAPXd7T5xkpiTbC9guSdycemBt8soUbLu3cyrPnkwIxwjYDCwnGbuqmU2njv786O3BkV6P75e2zEsO2rOQE+HAR2GhtZSGFqbkdE1Xgvnr3BAQPBjHJd+BKgHWjjfUkNNM2Ct3H56cYsoK8mTNNcOm2s4lBqommqATRbX15VpKsrzg2F+Bg1Gc7yYgmsGioG/x6xps5YAEG603qxjGEFIxoWCTF/XUKwU1im25kiWJ8K2LjBSeoZDrLrS2BGPGgoK0cFYMlvjYUgwusQBBaDiFj8Na3DlF90cJaDniyAreVQGMwKsJGDHuM+E8pAiMOSxmKAA=="/>\n'
            "</defs>\n"
            '<path fill="white" opacity="1" d="M 0 0 L 1 0 L 1 0.1 L 0.1 0.1 Z"/>\n'
            '<clipPath id="arc0"><path d="M 1 0 a 2 2 0 0 1 2 2 L 2.9 2 A 1.9 1.9 0 0 0 1 0.1 Z"/></clipPath>\n'
            '<g clip-path="url(#arc0)"><use href="#shade0" transform="translate(-1 0)"/></g>\n'
            '<path fill="white" opacity="0.333" d="M 3 2 L 3 3 L 2.9 2.9 L 2.9 2 Z"/>\n'
            '<path fill="black" opacity="1" d="M 3 3 L 0 3 L 0.1 2.9 L 2.9 2.9 Z"/>\n'
            '<path fill="white" opacity="0.333" d="M 0 3 L 0 0 L 0.1 0.1 L 0.1 2.9 Z"/>'
        ),
    },
    {
        "name": "double_loop_B_shape",
        "path": "M 0 0 a 1 1 0 0 1 0 2 a 1 1 0 0 1 0 2 h -1 V 0 Z",
        "expected": (
            "<defs>\n"
            '<image id="shade0" width="2" height="2" preserveAspectRatio="none" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABkElEQVQ4y12TTUoDQRCFp83MmEQjISL+YvwBRXDhSpdeQA/hOTyLx3AreAD3uoogiBDRGJM4ycS0r+LXMtjwUZ2eqtfVrzvOe38XRVFZVP7FRJSi3/EtcpHBV4gxExszFMQFwvCIjMVIDBGZCvTEhESHSMqaZ31C8V+hGASBT9SDSEz7KTEIhOI+NRYzS/6grRFCEV2UwXN+27ErOnTdDx28iVnMyxCKKJ5DwJLfRZvYD0bGLKbQKexgftQReBYt8UoXGUfKg0Awr8S5KxQEE28oHnCcMb5MTOCFxOB0Tntt51xreofeXyssIZxgtF27Cx3ktGStdVVoO12IS6vXb9O5kpB5soA/5lscBMIV9ZS8r3gqzvHAxhlCtxK513xeVE0o3EKmj6Z8Io7EsWgW3kGTb0pzJvogIfOkEmvBrm1TbIs9cUBBnXNGzJs8IBtV1T0qPpnrh2IHdsWWWBcNTHOYOy48b4eRaVwo2BArYpEHlBT+HwlrDXJy1qcCa2JVLJNQw+USSb7wtGtsMEQk+gHbL4r7VF3cTQAAAABJRU5ErkJggg=="/>\n'
            "</defs>\n"
            '<clipPath id="arc0"><path d="M 0 0 a 1 1 0 0 1 0 2 L 0 1.9 A 0.9 0.9 0 0 0 0 0.1 Z"/></clipPath>\n'
            '<g clip-path="url(#arc0)"><use href="#shade0" transform="translate(-1 0)"/></g>\n'
            '<path fill="black" opacity="1" d="M 0 2 L -0.1 1.9 L 0 1.9 Z"/>\n'
            '<path fill="white" opacity="0.333" d="M 0 2 L -0.1 2.1 L -0.1 1.9 Z"/>\n'
            '<path fill="white" opacity="1" d="M 0 2 L 0 2.1 L -0.1 2.1 Z"/>\n'
            '<clipPath id="arc1"><path d="M 0 2 a 1 1 0 0 1 0 2 L 0 3.9 A 0.9 0.9 0 0 0 0 2.1 Z"/></clipPath>\n'
            '<g clip-path="url(#arc1)"><use href="#shade0" transform="translate(-1 2)"/></g>\n'
            '<path fill="black" opacity="1" d="M 0 4 L -1 4 L -0.9 3.9 L 0 3.9 Z"/>\n'
            '<path fill="white" opacity="0.333" d="M -1 4 L -1 0 L -0.9 0.1 L -0.9 3.9 Z"/>\n'
            '<path fill="white" opacity="1" d="M -1 0 L 0 0 L 0 0.1 L -0.9 0.1 Z"/>'
        ),
        "format": PNG,
    },
]


@pytest.mark.parametrize("test_case", test_cases, ids=[c["name"] for c in test_cases])
def test_inset_path(test_case: ShadeTestCase) -> None:
    path = SvgPath(test_case["path"])
    prec = test_case.get("prec", None)
    expected = test_case["expected"]
    min_additional_digits = test_case.get("additional_digits", 8)
    fmt = test_case.get("format", WEBP)

    additional_digits = svg_path_editor.path_offset.additional_digits

    def to_str(shaded: PathShading) -> str:
        out = ""
        if shaded.defs_body:
            out += f"<defs>\n{'\n'.join(shaded.defs_body)}\n</defs>\n"
        return f"{out}{'\n'.join(shaded.body)}"

    for d in [4, 6, 8]:
        if d < min_additional_digits:
            continue

        if prec is None:
            shaded = shade_path(
                path,
                d="0.1",
                threshold="0.25",
                resolution=8,
                format=fmt,
                seed=0,
            )
            assert to_str(shaded) == expected

        if prec is None or prec == "auto-intersections":
            shaded = shade_path(
                path,
                d="0.1",
                threshold="0.25",
                resolution=8,
                prec="auto-intersections",
                format=fmt,
                seed=0,
            )
            assert to_str(shaded) == expected

        shaded = shade_path(
            path,
            d="0.1",
            threshold="0.25",
            resolution=8,
            prec="auto",
            format=fmt,
            seed=0,
        )
        assert to_str(shaded) == expected

    svg_path_editor.path_offset.additional_digits = additional_digits
