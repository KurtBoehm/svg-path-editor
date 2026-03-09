# This file is part of https://github.com/KurtBoehm/svg-path-editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from fractions import Fraction
from pathlib import Path
from shutil import which
from subprocess import run

from PIL import Image

from svg_path_editor import SvgPath, bevel_path, offset_path, round_corners, shade_path


def make_svg(svg_parts: list[str], viewbox: tuple[int, int, int, int]) -> str:
    x, y, w, h = viewbox
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="{x} {y} {w} {h}">{"".join(svg_parts)}</svg>'
    )


def make_path(
    d: SvgPath,
    fill: str | None = None,
    translate: tuple[int, int] | None = None,
) -> str:
    attrs: list[str] = []
    if fill:
        attrs.append(f'fill="{fill}"')
    if translate:
        x, y = translate
        attrs.append(f'transform="translate({x} {y})"')
    attrs.append(f'd="{d}"')
    return f"<path {' '.join(attrs)}/>"


def handle_svg(
    dst: Path,
    svg: str,
    size_units: int,
    supersample: int = 16,
) -> None:
    pixels = size_units * 128
    dst.write_text(svg, encoding="utf-8")
    png_path = dst.with_suffix(".png")

    cmd: list[str | Path] = [
        "inkscape",
        dst,
        "--export-type=png",
        f"--export-filename={png_path}",
        f"--export-width={pixels * supersample}",
        f"--export-height={pixels * supersample}",
    ]
    run(cmd, check=True)

    Image.MAX_IMAGE_PIXELS = None
    with Image.open(png_path) as img:
        img = img.resize((pixels, pixels), Image.Resampling.BOX)
    img.save(png_path)

    if which("oxipng"):
        run(["oxipng", "-o6", "--strip", "all", png_path], check=True)


base = Path(__file__).parent

# Base shape
base_svg = SvgPath("M 0 8 H 6 L 8 6 V 2 A 2 2 0 0 1 6 0 H 2 A 2 2 0 0 0 0 2 Z")

# Round corners
handle_svg(
    base / "round_src.svg",
    make_svg([make_path(base_svg)], (0, 0, 8, 8)),
    size_units=8,
)

for radius in (1, 2):
    rounded = round_corners(base_svg, radius=radius)
    handle_svg(
        base / f"round_{radius}.svg",
        make_svg([make_path(rounded)], (0, 0, 8, 8)),
        size_units=8,
    )

# Offset
offset_in = offset_path(base_svg, d=1)
offset_out = offset_path(base_svg, d=-1)

handle_svg(
    base / "offset_merged.svg",
    make_svg(
        [
            make_path(offset_out, fill="#EA4335"),
            make_path(base_svg),
            make_path(offset_in, fill="#4285F4"),
        ],
        (-1, -1, 10, 10),
    ),
    size_units=10,
)
for suffix, path in (("src", base_svg), ("inw", offset_in), ("out", offset_out)):
    handle_svg(
        base / f"offset_{suffix}.svg",
        make_svg([make_path(path)], (-1, -1, 10, 10)),
        size_units=10,
    )


# Bevel
bevel_colors = [
    "#F03E3E",
    "#FD7E14",
    "#FAB005",
    "#40C057",
    "#22B8CF",
    "#4263EB",
    "#AE3EC9",
]

handle_svg(
    base / "bevel_src.svg",
    make_svg([make_path(base_svg)], (-1, -1, 10, 10)),
    size_units=10,
)

for d, suffix in ((1, "inw"), (-1, "out")):
    bevel_faces: list[tuple[SvgPath, str]] = []
    color_index = 0
    prev_ante_ext = False

    for seg in bevel_path(base_svg, d=d):
        bevel_faces.append((seg.path, bevel_colors[color_index]))
        if not prev_ante_ext and not seg.ante_ext:
            color_index += 1
        prev_ante_ext = seg.ante_ext

    handle_svg(
        base / f"bevel_{suffix}.svg",
        make_svg(
            [
                make_path(base_svg),
                *[make_path(p, fill=c) for p, c in bevel_faces],
            ],
            (-1, -1, 10, 10),
        ),
        size_units=10,
    )

# Bevel with Lambert shading
lambert_paths_src = [
    (SvgPath("M 0 4 H 4 V 0 H 2 A 2 2 0 0 0 0 2 Z"), "#4285F4"),
    (SvgPath("M 4 4 H 8 V 2 A 2 2 0 0 1 6 0 H 4 Z"), "#34A853"),
    (SvgPath("M 0 4 V 8 H 4 V 4 Z"), "#FBBC05"),
    (SvgPath("M 4 4 V 8 H 6 L 8 6 V 4 Z"), "#EA4335"),
]

handle_svg(
    base / "lambert_src.svg",
    make_svg([make_path(p, fill=c) for p, c in lambert_paths_src], (0, 0, 8, 8)),
    size_units=8,
)

for z_light in (Fraction(1, 2), Fraction(3, 4), Fraction(2, 1), Fraction(5, 4)):
    defs: list[str] = []
    body_paths: list[str] = []

    for p, color in lambert_paths_src:
        body_paths.append(make_path(p, fill=color))
        shading = shade_path(
            p,
            d=0.5,
            z_light=float(z_light),
            resolution=32,
            shade_offset=len(defs),
            clip_offset=len(defs),
            seed=0,
        )
        defs.extend(shading.defs_body)
        body_paths.extend(shading.body)

    n, d = z_light.numerator, z_light.denominator
    z_str = f"{n}_{d}" if d != 1 else str(n)
    handle_svg(
        base / f"lambert_{z_str}.svg",
        make_svg([f"<defs>{''.join(defs)}</defs>", *body_paths], (0, 0, 8, 8)),
        size_units=8,
    )
