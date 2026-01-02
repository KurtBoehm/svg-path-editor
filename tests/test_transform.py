# This file is part of https://github.com/KurtBoehm/svg_path_editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from svg_path_editor import SvgPath

ante = (
    "M 10 10 L 110 10 A 20 20 0 0 1 130 30 L 130 130 C 130 150 110 170 90 170 "
    "L 30 170 Q 10 170 10 150 Z M 40 40 C 60 20 90 20 110 40 C 130 60 130 90 110 110 "
    "C 90 130 60 130 40 110 C 20 90 20 60 40 40 Z M 60 70 a 10 15 30 1 1 20 0 "
    "a 10 15 30 1 1 -20 0 z M 80 120 h 20 v 20 h -20 v -20 z"
)
print(ante)


def test_translation():
    post = (
        "M 10.1 10.2 L 110.1 10.2 A 20 20 0 0 1 130.1 30.2 L 130.1 130.2 "
        "C 130.1 150.2 110.1 170.2 90.1 170.2 L 30.1 170.2 Q 10.1 170.2 10.1 150.2 Z "
        "M 40.1 40.2 C 60.1 20.2 90.1 20.2 110.1 40.2 "
        "C 130.1 60.2 130.1 90.2 110.1 110.2 C 90.1 130.2 60.1 130.2 40.1 110.2 "
        "C 20.1 90.2 20.1 60.2 40.1 40.2 Z M 60.1 70.2 a 10 15 30 1 1 20 0 "
        "a 10 15 30 1 1 -20 0 z M 80.1 120.2 h 20 v 20 h -20 v -20 z"
    )

    ante_svg = SvgPath(ante)
    post_svg = ante_svg.translated("0.1", "0.2")

    assert str(ante_svg) == ante
    assert str(post_svg) == post


def test_rotation():
    post90 = (
        "M -10 10 L -10 110 A 20 20 90 0 1 -30 130 L -130 130 "
        "C -150 130 -170 110 -170 90 L -170 30 Q -170 10 -150 10 Z M -40 40 "
        "C -20 60 -20 90 -40 110 C -60 130 -90 130 -110 110 C -130 90 -130 60 -110 40 "
        "C -90 20 -60 20 -40 40 Z M -70 60 a 10 15 120 1 1 0 20 "
        "a 10 15 120 1 1 0 -20 z M -120 80 v 20 h -20 v -20 h 20 z"
    )
    post180 = (
        "M -10 -10 L -110 -10 A 20 20 180 0 1 -130 -30 L -130 -130 "
        "C -130 -150 -110 -170 -90 -170 L -30 -170 Q -10 -170 -10 -150 Z "
        "M -40 -40 C -60 -20 -90 -20 -110 -40 C -130 -60 -130 -90 -110 -110 "
        "C -90 -130 -60 -130 -40 -110 C -20 -90 -20 -60 -40 -40 Z M -60 -70 "
        "a 10 15 210 1 1 -20 0 a 10 15 210 1 1 20 0 z M -80 -120 h -20 v -20 h 20 v 20 "
        "z"
    )
    post270 = (
        "M 10 -10 L 10 -110 A 20 20 270 0 1 30 -130 L 130 -130 "
        "C 150 -130 170 -110 170 -90 L 170 -30 Q 170 -10 150 -10 Z M 40 -40 "
        "C 20 -60 20 -90 40 -110 C 60 -130 90 -130 110 -110 C 130 -90 130 -60 110 -40 "
        "C 90 -20 60 -20 40 -40 Z M 70 -60 a 10 15 300 1 1 0 -20 a 10 15 300 1 1 0 20 "
        "z M 120 -80 v -20 h 20 v 20 h -20 z"
    )

    ante_svg = SvgPath(ante)
    post90_svg = ante_svg.rotated(0, 0, 90)
    post180_svg = ante_svg.rotated(0, 0, 180)
    post270_svg = ante_svg.rotated(0, 0, 270)

    assert str(ante_svg) == ante
    assert str(post90_svg) == post90
    assert str(post180_svg) == post180
    assert str(post270_svg) == post270


def test_scale():
    post = (
        "M 1 2 L 11 2 A 4 2 90 0 1 13 6 L 13 26 C 13 30 11 34 9 34 L 3 34 "
        "Q 1 34 1 30 Z M 4 8 C 6 4 9 4 11 8 C 13 12 13 18 11 22 C 9 26 6 26 4 22 "
        "C 2 18 2 12 4 8 Z M 6 14 a 2.8155 1.0655 -80.7056 1 1 2 0 "
        "a 2.8155 1.0655 -80.7056 1 1 -2 0 z M 8 24 h 2 v 4 h -2 v -4 z"
    )

    ante_svg = SvgPath(ante)
    post_svg = ante_svg.scaled("0.1", "0.2")

    assert str(ante_svg) == ante
    assert f"{post_svg:.4}" == post
