# This file is part of https://github.com/KurtBoehm/svg-path-editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import io
from pathlib import Path
from shutil import which
from subprocess import run

import cairosvg
from PIL import Image

from svg_path_editor import SvgPath, bevel_path, offset_path, round_corners, shade_path


def make_svg(svg_paths: list[str], viewbox: tuple[int, int, int, int]) -> str:
    x, y, w, h = viewbox
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        + f'xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="{x} {y} {w} {h}">'
        + "".join(svg_paths)
        + "</svg>"
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
    n: int,
    supersample: int = 16,
    *,
    png: bool = False,
) -> None:
    n *= 32
    dst.write_text(svg)

    if png:
        # Rasterize
        png_bytes = cairosvg.svg2png(
            bytestring=svg,
            output_width=n * supersample,
            output_height=n * supersample,
        )
        assert isinstance(png_bytes, bytes)
        img = Image.open(io.BytesIO(png_bytes)).resize((n, n), Image.Resampling.BOX)

        png_path = dst.with_suffix(".png")
        img.save(png_path)
        if which("oxipng") is not None:
            run(["oxipng", "-o6", "--strip", "all", png_path], check=True)


base = Path(__file__).parent

# Round corners

svg = SvgPath("M 0 8 H 6 L 8 6 V 2 A 2 2 0 0 1 6 0 H 2 A 2 2 0 0 0 0 2 Z")
handle_svg(base / "round_input.svg", make_svg([make_path(svg)], (0, 0, 8, 8)), 8)
for r in (1, 2):
    svg_rnd = round_corners(svg, radius=r)
    handle_svg(base / f"round_{r}.svg", make_svg([make_path(svg_rnd)], (0, 0, 8, 8)), 8)

# Offset
svg_off_inw = offset_path(svg, d=1)
svg_off_out = offset_path(svg, d=-1)
handle_svg(
    base / "offset.svg",
    make_svg(
        [
            make_path(svg_off_out, fill="#EA4335"),
            make_path(svg),
            make_path(svg_off_inw, fill="#4285F4"),
        ],
        (-1, -1, 10, 10),
    ),
    11,
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
    base / "bevel_input.svg",
    make_svg([make_path(svg)], (-1, -1, 10, 10)),
    11,
    png=True,
)
for d, suffix in ((1, "inw"), (-1, "out")):
    bevel_faces: list[tuple[SvgPath, str]] = []
    i, prev_ante = 0, False
    for j, p in enumerate(bevel_path(svg, d=d)):
        bevel_faces.append((p.path, bevel_colors[i]))
        if not prev_ante and not p.ante_ext:
            i += 1
        prev_ante = p.ante_ext

    handle_svg(
        base / f"bevel_{suffix}.svg",
        make_svg(
            [make_path(svg), *[make_path(p, fill=c) for p, c in bevel_faces]],
            (-1, -1, 10, 10),
        ),
        11,
        png=True,
    )

# Bevel with Lambert shading
paths = [
    (SvgPath("M 0 4 H 4 V 0 H 2 A 2 2 0 0 0 0 2 Z"), "#4285F4"),
    (SvgPath("M 4 4 H 8 V 2 A 2 2 0 0 1 6 0 H 4 Z"), "#34A853"),
    (SvgPath("M 0 4 V 8 H 4 V 4 Z"), "#FBBC05"),
    (SvgPath("M 4 4 V 8 H 6 L 8 6 V 4 Z"), "#EA4335"),
]
handle_svg(
    base / "lambert_base.svg",
    make_svg([make_path(p, fill=c) for p, c in paths], (0, 0, 8, 8)),
    8,
    png=True,
)
for threshold in [0.25, 0.75]:
    lambert_defs: list[str] = []
    lambert_paths: list[str] = []
    for p, c in paths:
        lambert_paths.append(make_path(p, fill=c))
        shading = shade_path(
            p,
            d=0.5,
            threshold=0.75,
            resolution=32,
            shade_offset=len(lambert_defs),
            clip_offset=len(lambert_defs),
            seed=0,
        )
        lambert_defs.extend(shading.defs_body)
        lambert_paths.extend(shading.body)

    f = str(threshold).replace(".", "_")
    handle_svg(
        base / f"lambert_{f}.svg",
        make_svg(
            [f"<defs>{''.join(lambert_defs)}</defs>", *lambert_paths], (0, 0, 8, 8)
        ),
        8,
        png=True,
    )
