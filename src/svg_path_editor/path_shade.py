from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Literal, Protocol

from svg_path_editor.geometry import Point
from svg_path_editor.math import Number, Precision, dec_to_rat, rat_to_dec
from svg_path_editor.path_offset import BevelArced, BevelPolygon, bevel_path
from svg_path_editor.svg import SvgPath
from svg_path_editor.svg import format_decimal as d2s

if TYPE_CHECKING:
    import numpy as np


def lambert_from_angle(normal: Point) -> Decimal:
    r"""
    Lambertian diffuse intensity from a surface normal.

    The light direction is fixed to :math:`(0, -1, 1)` in world space.
    The result is

    .. math::

       I = \max(0, \hat{\mathbf{n}}\cdot\hat{\mathbf{L}}),

    evaluated via the signed angle of ``normal`` in the :math:`xy`-plane.

    :param normal: Surface normal.
    :return: Lambertian intensity in :math:`[0, 1]`.
    """
    import sympy as sp

    # I(theta) = max(0, (1 - sin(theta)) / 2)
    sinv = rat_to_dec(sp.sin(sp.atan2(dec_to_rat(-normal.y), dec_to_rat(normal.x))))
    return max(Decimal(0), (1 - sinv) / 2)


class ImageFormat(Protocol):
    """
    Abstract image encoder.

    :ivar media_type: MIME type of the encoded image.
    :ivar extension: File extension (without dot).
    """

    media_type: ClassVar[str]
    extension: ClassVar[str]

    def encode(self, data: "np.ndarray") -> bytes | bytearray:
        """
        Encode an RGBA image.

        :param data: ``(H, W, 4)`` uint8 array in RGBA order.
        :return: Encoded image bytes.
        """
        ...


class WebpFormat:
    """
    Lossless WebP encoder.

    Uses :func:`imagecodecs.webp_encode` with ``lossless=True``.
    """

    media_type: ClassVar[str] = "image/webp"
    extension: ClassVar[str] = "webp"

    def encode(self, data: "np.ndarray") -> bytes | bytearray:
        from imagecodecs import webp_encode

        return webp_encode(data, lossless=True)


class PngFormat:
    """
    PNG encoder.

    Uses :func:`imagecodecs.png_encode` with ``level=9``.
    """

    media_type: ClassVar[str] = "image/png"
    extension: ClassVar[str] = "png"

    def encode(self, data: "np.ndarray") -> bytes | bytearray:
        from imagecodecs import png_encode

        return png_encode(data, level=9)


WEBP = WebpFormat()
PNG = PngFormat()


def lambert_shading_base64(
    *,
    r: Point,
    phi: Decimal,
    locally_convex: bool,
    resolution: float,
    t: float = 0.25,
    format: ImageFormat = WEBP,
    seed: int | None = None,
) -> tuple[bytes, str]:
    r"""
    Render a Lambert–shaded elliptical cone, return encoded bytes and base64 URI.

    The cone radii are :math:`r = (r_x, r_y)` in image space. For a point
    :math:`(x, y)` on the grid

    .. math::

       (x, y) \in \left[-\frac{1}{r_x}, \frac{1}{r_x}\right]
                 \times \left[-\frac{1}{r_y}, \frac{1}{r_y}\right],

    the unnormalized normal is

    .. math::

       \mathbf{n}(x, y) = \left(\frac{x}{r_x^2}, \frac{y}{r_y^2}, 1\right).

    The Lambert term is

    .. math::

       I(x, y) = \max\left(0, \hat{\mathbf{n}}(x, y)\cdot\hat{\mathbf{L}}\right),

    where :math:`\hat{\mathbf{L}}` is the unit vector from :math:`(0, s, 1)`,
    with :math:`s = -1` if ``locally_convex`` else :math:`+1`, rotated in the
    :math:`xy`-plane by :math:`-\varphi` degrees.

    Grayscale is binary (0 or 255) according to :math:`I > t`. Alpha is a
    symmetric remap of :math:`I` around :math:`t`:

    .. math::

       \alpha(I) =
       \begin{cases}
         \dfrac{I - t}{1 - t}, & I \geq t,\\[4pt]
         \dfrac{t - I}{t},     & I < t.
       \end{cases}

    Before 8-bit quantization, uniform noise in :math:`[0, 1]` is added to
    alpha for dithering.

    The final RGBA image is encoded with ``format`` and returned both as raw
    bytes and as a ``data:...;base64,...`` URI.

    :param r: Ellipse radii in :math:`x` and :math:`y`.
    :param phi: Rotation in degrees of the light direction in image space
        (clockwise in screen coordinates).
    :param locally_convex: If true, the base light direction is :math:`(0, -1, 1)`,
        otherwise :math:`(0, 1, 1)`.
    :param resolution: Pixels per SVG unit. Image size is
        :math:`\lceil 2 r_x \, \mathrm{resolution} \rceil
        \times \lceil 2 r_y \, \mathrm{resolution} \rceil`.
    :param t: Neutral Lambert intensity in :math:`[0, 1]` (threshold).
    :param format: Image format to use.
    :param seed: RNG seed for alpha dithering; ``None`` is non-deterministic.
    :return: ``(img_bytes, img_data_uri)`` with ``img_data_uri`` suitable
        for SVG ``href``.
    """
    import base64
    import math

    import numpy as np
    import numpy.typing as npt

    rx, ry = float(r.x), float(r.y)
    nx, ny = math.ceil(2 * rx * resolution), math.ceil(2 * ry * resolution)

    # Coordinate grid in [-1/rx, 1/rx] × [-1/ry, 1/ry]
    x = np.linspace(-1 / rx, 1 / rx, nx, dtype=np.float64)
    y = np.linspace(-1 / ry, 1 / ry, ny, dtype=np.float64)
    x, y = np.meshgrid(x, y, indexing="xy")

    # Unnormalized normals; z-component is constant 1
    nxy: npt.NDArray[np.float64] = np.hypot(x, y)
    nx, ny, nz = x / nxy, y / nxy, 1.0

    # Normalize the normals
    inv_norm = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
    nxn, nyn, nzn = nx * inv_norm, ny * inv_norm, nz * inv_norm

    # Light direction: base (0, ±1, 1), then rotate by -phi around z
    lx, ly, lz = 0.0, (-1.0 if locally_convex else 1.0), 1.0
    phi_rad = -math.radians(float(phi))
    sin_phi, cos_phi = math.sin(phi_rad), math.cos(phi_rad)
    lx, ly = cos_phi * lx - sin_phi * ly, sin_phi * lx + cos_phi * ly

    lnorm = math.hypot(lx, ly, lz)
    lx, ly, lz = lx / lnorm, ly / lnorm, lz / lnorm

    # Lambert term: clamp to [0, 1]
    intensity = np.clip(nxn * lx + nyn * ly + nzn * lz, 0.0, 1.0)

    # Threshold-based grayscale + symmetric alpha remap
    mask = intensity > t

    alpha = intensity.copy()
    alpha[mask] = (alpha[mask] - t) / (1.0 - t)
    alpha[~mask] = (t - alpha[~mask]) / t

    # Quantize alpha to 8-bit with small dithering noise
    w = np.iinfo(np.uint8).max
    noise = np.random.default_rng(seed).uniform(0.0, 1.0, size=alpha.shape)
    alpha = (alpha * w + noise).clip(0, w).astype(np.uint8)

    gray = mask.astype(np.uint8) * 255
    rgba = np.dstack([gray, gray, gray, alpha])
    img_bytes = format.encode(rgba)
    assert isinstance(img_bytes, bytes)

    b64 = base64.b64encode(img_bytes).decode("ascii")
    return img_bytes, f"data:{format.media_type};base64," + b64


@dataclass
class PathShading:
    """
    SVG fragments for shaded bevels.

    :ivar defs_body: Elements for a document-wide ``<defs>`` (e.g. shared
        ``<image>`` or ``<clipPath>`` definitions).
    :ivar body: Per-path drawing elements (e.g. ``<path>``, ``<g>``, ``<use>``)
        that reference :attr:`defs_body`.
    """

    defs_body: list[str]
    body: list[str]


def shade_path(
    svg: SvgPath,
    *,
    d: Number,
    threshold: Number,
    resolution: float,
    max_opacity: Number = 1,
    format: ImageFormat = WEBP,
    seed: int | None = None,
    prec: Precision | Literal["auto", "auto-intersections"] | None = None,
) -> PathShading:
    """
    Per-bevel Lambert shading for an SVG path.

    The path is decomposed into bevel regions via
    :func:`svg_path_editor.path_offset.bevel_path`. Flat bevel polygons are
    shaded analytically with :func:`lambert_from_angle`. Curved bevel arcs use
    a small Lambert RGBA texture from :func:`lambert_shading_base64`, referenced
    by ``<image>`` / ``<use>`` and clipped to the arc geometry.

    For each bevel polygon:

    * One ``<path>`` is emitted with ``fill="white"`` or ``fill="black"``
      depending on whether the intensity is above or below ``threshold``.
    * Opacity is a symmetric remap of the intensity around ``threshold`` in
      :math:`[0, 1]`, scaled by ``max_opacity``.

    For each bevel arc:

    * A Lambert cone texture is generated (or reused from a cache) for
      ``(r.x, r.y, phi, locally_convex)``.
    * A base ``<image>`` at the origin with size :math:`2 r_x \\times 2 r_y`
      is placed in :attr:`PathShading.defs_body` once per unique key.
    * For each occurrence, a ``<clipPath>`` with the bevel geometry and a
      ``<use>`` of the base image are emitted into :attr:`PathShading.body`,
      translated so the image origin matches the lower-left corner of the
      ellipse bounding box, and rotated by ``phi`` around the ellipse center
      if non-zero.
    * ``<use>`` carries opacity ``max_opacity`` when it is less than 1.

    To integrate into an SVG, place all ``defs_body`` entries inside a single
    document-level ``<defs>`` and insert ``body`` where the path should render.

    :param svg: Input path to bevel and shade.
    :param d: Offset distance for :func:`bevel_path`.
    :param threshold: Neutral Lambert intensity in :math:`[0, 1]`, shared
        between flat bevels and textures.
    :param resolution: Pixels per SVG unit for generated textures; image
        dimensions follow :func:`lambert_shading_base64`.
    :param max_opacity: Global opacity scale in :math:`[0, 1]`.
    :param format: Texture format, e.g. :data:`WEBP` or :data:`PNG`.
    :param seed: RNG seed for alpha dithering in :func:`lambert_shading_base64`;
        ``None`` for non-deterministic.
    :param prec: Precision/geometry mode passed to :func:`bevel_path`.
        ``"auto"`` and ``"auto-intersections"`` select automatic strategies;
        ``None`` uses the default.
    """
    threshold = Decimal(threshold)
    max_opacity = Decimal(max_opacity)

    bevels = bevel_path(svg, d=d, prec=prec)

    # Cache for unique images: key -> (image_id, base64)
    image_cache: dict[tuple[Decimal, Decimal, Decimal, bool], tuple[str, str]] = {}
    image_id_ctr = 0

    defs_body: list[str] = []
    body: list[str] = []

    clip_idx = 0
    for b in bevels:
        match b:
            case BevelPolygon(outward_normal=normal, path=path):
                intensity = lambert_from_angle(normal)
                fill = "white" if intensity >= threshold else "black"
                opacity = (
                    (intensity - threshold) / (1 - threshold)
                    if intensity >= threshold
                    else (threshold - intensity) / threshold
                ) * max_opacity
                body.append(f'<path fill="{fill}" opacity="{opacity:.3g}" d="{path}"/>')

            case BevelArced(
                path=path,
                c=c,
                r=r,
                phi=phi,
                locally_convex=locally_convex,
            ):
                base, dims = c - r, r * 2
                img_key = r.x, r.y, phi, locally_convex

                if (img_entry := image_cache.get(img_key)) is None:
                    # New unique image data; generate and store
                    img, base64 = lambert_shading_base64(
                        r=r,
                        phi=phi,
                        locally_convex=locally_convex,
                        resolution=resolution,
                        format=format,
                        seed=seed,
                    )
                    image_id = f"shade{image_id_ctr}"
                    image_id_ctr += 1

                    image_cache[img_key] = (image_id, base64)

                    # Base <image> in <defs> at (0, 0) with size 2 r.x × 2 r.y.
                    defs_body.append(
                        f'<image id="{image_id}" '
                        + f'width="{d2s(dims.x)}" height="{d2s(dims.y)}" '
                        + f'preserveAspectRatio="none" href="{base64}"/>'
                    )
                else:
                    image_id, base64 = img_entry

                clip_id = f"arc{clip_idx}"
                clip_idx += 1
                body.append(f'<clipPath id="{clip_id}"><path d="{path}"/></clipPath>')

                transform_parts = [f"translate({d2s(base.x)} {d2s(base.y)})"]
                if phi != 0:
                    transform_parts.append(
                        f"rotate({d2s(phi)} {d2s(c.x - base.x)} {d2s(c.y - base.y)})"
                    )
                transform_attr = " ".join(transform_parts)

                opacity_attr = (
                    f' opacity="{max_opacity:.3g}"' if max_opacity != 1 else ""
                )

                body.append(
                    f'<g clip-path="url(#{clip_id})">'
                    + f'<use href="#{image_id}"{opacity_attr} '
                    + f'transform="{transform_attr}"/></g>'
                )

    return PathShading(defs_body=defs_body, body=body)
