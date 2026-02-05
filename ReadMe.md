# 🎨 SVG Path Editor

A high-precision Python library for editing, transforming, and optimizing SVG paths programmatically.

It is a port of [`svg-path-editor-lib`](https://www.npmjs.com/package/svg-path-editor-lib) 1.0.3 to Python with significant improvements:

- **Decimal-based geometry**: all coordinates are stored as `decimal.Decimal`, with high-precision SymPy-based computations where appropriate. This preserves the decimal values stored in an SVG path and avoids the binary round-off errors introduced by `float`.
- **In-place and out-of-place operations**: most geometric operations are available in both mutating (`scale`, `rotate`, …) and non-mutating (`scaled`, `rotated`, …) variants.
- **`list`-like path modification API**: path-level manipulations (insert, remove, change type, …) are exposed as methods on `SvgPath`.
- **Typed and documented**: extensive type hints and docstrings for good IDE support and static analysis.
- **Geometric offsetting**: robust offsets for simple closed paths, with exact line/ellipse geometry and symbolic intersection handling.

The **full documentation** is on [Read the Docs](https://svg-path-editor.readthedocs.io), and a `pytest`-based **test suite with 100% coverage** is available in the [`tests` directory](https://github.com/KurtBoehm/svg-path-editor/blob/main/tests).

[![Tests](https://github.com/KurtBoehm/svg-path-editor/actions/workflows/test.yml/badge.svg)](https://github.com/KurtBoehm/svg-path-editor/actions/workflows/test.yml)

## 📦 Installation

This package is available on PyPI and can be installed with `pip`:

```sh
pip install svg-path-editor
```

## 🚀 Basic Usage

```python
from svg_path_editor import SvgPath

path = SvgPath("M-15 14s5 7.5 15 7.5 15-7.5 15-7.5 z")

# `SvgPath` implements `__str__` with fairly readable (non-minified) output
# M -15 14 s 5 7.5 15 7.5 s 15 -7.5 15 -7.5 z
print(path)

# Custom decimals and minified output (`decimals=None`, `minify=False` by default)
# M-15 14s5 7.5 15 7.5 15-7.5 15-7.5z
print(path.as_string(decimals=1, minify=True))

# `SvgPath` also implements `__format__`, with `m` denoting `minify=True`
print(f"{path:.1m} or {path:m.1}")
```

## 📐 Geometric Operations

Geometric operations are available in both in-place and out-of-place variants.

### Out-of-place

```python
path = SvgPath("M-15 14s5 7.5 15 7.5 15-7.5 15-7.5 z")

# Out-of-place scale
# M -30 28 s 10 15 30 15 s 30 -15 30 -15 z
print(path.scaled(kx=2, ky=2))

# Out-of-place translate
# M -14 14.5 s 5 7.5 15 7.5 s 15 -7.5 15 -7.5 z
print(path.translated(dx=1, dy=0.5))

# Out-of-place rotate around (0, 0)
# M -14 -15 s -7.5 5 -7.5 15 s 7.5 15 7.5 15 z
print(path.rotated(ox=0, oy=0, degrees=90))
```

### In-place

```python
path = SvgPath("M-15 14s5 7.5 15 7.5 15-7.5 15-7.5 z")

# In-place scale
# M -30 28 s 10 15 30 15 s 30 -15 30 -15 z
path.scale(kx=2, ky=2)
print(path)

# In-place translate
# M -29 28.5 s 10 15 30 15 s 30 -15 30 -15 z
path.translate(dx=1, dy=0.5)
print(path)

# In-place rotate
# M -28.5 -29 s -15 10 -15 30 s 15 30 15 30 z
path.rotate(ox=0, oy=0, degrees=90)
print(path)
```

## 🔁 Absolute vs. Relative Commands

Commands can be stored as either absolute (`M`, `L`, `C`, …) or relative (`m`, `l`, `c`, …).
Conversion is available in-place via a property and out-of-place via a method.

```python
path = SvgPath("M-15 14s5 7.5 15 7.5 15-7.5 15-7.5 z")

# In-place: `SvgPath.relative` mutates the instance
path.relative = False
# M -15 14 S -10 21.5 0 21.5 S 15 14 15 14 Z
print(path)

# Out-of-place: `SvgPath.with_relative()` returns a new path
relative = path.with_relative(True)
# m -15 14 s 5 7.5 15 7.5 s 15 -7.5 15 -7.5 z
print(relative)
```

## 🧩 Path Modification

`SvgPath` exposes several methods that modify the structure of a path in place, including parts of the `list` API:

```python
from svg_path_editor import Point, SvgPath
from svg_path_editor.svg import QuadraticBezierCurveTo

path = SvgPath("M0 0L10 0V10Z")

# Deep copy
clone = path.clone()
# M 0 0 L 10 0 V 10 Z
print(clone)

# In-place removal of the `L` command
path.remove(path.path[1])
# M 0 0 V 10 Z
print(path)

# In-place insertion of a quadratic Bézier curve where the `L` command was
path.insert(1, QuadraticBezierCurveTo([5, -5, 10, 0], relative=False))
# M 0 0 Q 5 -5 10 0 V 10 Z
print(path)

# In-place command type change from `V` to `L` (equivalent, but longer)
path.change_type(2, "L")
# M 0 0 Q 5 -5 10 0 L 10 10 Z
print(path)

# In-place move of a particular point
path.set_location(path.target_locations[-2], to=Point(5, 10))
# M 0 0 Q 5 -5 10 0 L 5 10 Z
print(path)

# The clone is unaffected by these changes
print(clone)
```

## 🛠️ Higher-Level Path Operations

These functions operate on paths out-of-place:

```python
from svg_path_editor import SvgPath, change_path_origin, reverse_path

path = SvgPath("M-15 14s5 7.5 15 7.5 15-7.5 15-7.5 z")

# Reverse path direction
# M 15 14 S 10 21.5 0 21.5 S -15 14 -15 14 Z
print(reverse_path(path))

# Change the origin (starting command) within a subpath
# M 0 21.5 c 10 0 15 -7.5 15 -7.5 L -15 14 s 5 7.5 15 7.5
print(change_path_origin(path, new_origin_index=2))
```

## 🔘 Offsetting Paths

This library supports high-precision offsetting of a closed path consisting of straight lines and elliptical arcs inward or outward by a given distance:

```python
from svg_path_editor import SvgPath, offset_path

# A complex path with various arcs
path = SvgPath("M 5 0 A 5 5 0 0 0 0 5 A 5 10 0 0 0 5 15 a 5 5 0 0 1 5 -5 V 5 H 5 a 5 5 0 0 0 5 -5 Z")

# Offset the path
inset = offset_path(
    path,
    # Offset by 1 inwards (negative values offset outwards)
    d=1,
    # Use numeric computations with automatic precision
    prec="auto",
)

# M 5 1 A 4 4 0 0 0 1 5 A 4 9 0 0 0 4.1249 13.782 A 6 6 0 0 1 9 9.0839 L 9 6 L 4 6 L 4 4 L 5 4 A 4 4 0 0 0 8.873 1 Z
print(f"{inset:.4}")
```

The `prec` parameter controls how `offset_path` operates:

- `prec=None`: fully symbolic intermediate computations using SymPy. Can be very slow, especially for arcs based on rotated ellipses.
- `prec="auto"`: mostly numeric computations with the current `Decimal` precision plus a safety margin (8 digits by default). Fastest option, with results at full precision in all tests.
- `prec="auto-intersections"`: offset segments are computed symbolically, but intersections are still computed mostly numerically.
- `prec=Precision(baseline=…, additional=…)`: explicitly set the desired _baseline_ precision and the _additional_ safety margin.

Similarly, the library exposes `bevel_path`, which has the same parameters as `offset_path` (and uses very similar logic internally) and generates a sequence of small closed paths that fill the gap between the original path and its offset (the “bevel” region), which can be used for shading:

```python
from svg_path_editor import SvgPath, bevel_path

# A path looking somewhat like an anvil
path = SvgPath("M 0 0 h 2 a 1 1 0 0 1 -1 1 h 1 v 1 h -2 Z")

# M 0 0 L 2 0 L 1.894427190999915878563669467 0.1 L 0.1 0.1 Z
# M 2 0 a 1 1 0 0 1 -1 1 L 1 0.9 A 0.9 0.9 0 0 0 1.894427190999915878563669467 0.1 Z
# M 1 1 L 0.9 0.9 L 1 0.9 Z
# M 1 1 L 0.9 1.1 L 0.9 0.9 Z
# M 1 1 L 2 1 L 1.9 1.1 L 0.9 1.1 Z
# M 2 1 L 2 2 L 1.9 1.9 L 1.9 1.1 Z
# M 2 2 L 0 2 L 0.1 1.9 L 1.9 1.9 Z
# M 0 2 L 0 0 L 0.1 0.1 L 0.1 1.9 Z
for p in bevel_path(path, d="0.1"):
    print(p)
```

## 🧮 Decimal-Based Geometry

Internally, all coordinates and numeric parameters are stored as `decimal.Decimal`:

- Constructors and geometric methods accept `int`, `float`, `str`, or `Decimal`, and convert to `Decimal` immediately.
- Arithmetic (translation, scaling, rotation, etc.) is performed in terms of `Decimal` to retain the decimal representation in an SVG path and avoid binary round-off errors.
- The decimal precision is controlled via Python’s `decimal` context.

```python
from decimal import localcontext
from svg_path_editor import SvgPath

path = SvgPath("M0 0h10v10z")

# Default precision: 28 digits
# Rotation uses SymPy for high-precision trigonometric functions
rotated = path.rotated(0, 0, -45)
# M 0 0 l 7.071067811865475244008443621 -7.071067811865475244008443621 l 7.071067811865475244008443621 7.071067811865475244008443621 z
print(rotated)
# Precision can be reduced when printing
# M 0 0 l 7.07107 -7.07107 l 7.07107 7.07107 z
print(f"{rotated:.5}")

# The precision can be controlled using `getcontext`/`localcontext`
# Since `Decimal` is a floating-point format, the precision specifies the total
# number of significant digits, not just the number of decimal places
with localcontext() as ctx:
    ctx.prec = 6
    rotated = path.rotated(0, 0, -45)
    # Same output as before, even without explicit precision reduction
    # M 0 0 l 7.07107 -7.07107 l 7.07107 7.07107 z
    print(rotated)
```

## 🧹 Path Optimization

`optimize_path` rewrites a path into an equivalent but more compact form and operates out-of-place:

```python
from svg_path_editor import SvgPath, optimize_path

path = SvgPath("M-15 14s5 7.5 15 7.5 15-7.5 15-7.5 z")

optimized = optimize_path(
    path,
    # Remove redundant M/Z or degenerate L/H/V.
    remove_useless_commands=True,
    # Remove empty closed subpaths (M immediately followed by Z).
    remove_orphan_dots=True,
    # Convert eligible C/Q to S/T.
    use_shorthands=True,
    # Replace L with H/V where possible.
    use_horizontal_and_vertical_lines=True,
    # Choose relative/absolute per command to minimize size.
    use_relative_absolute=True,
    # Try reversing path direction if it reduces output length.
    # This may change the appearance of stroked paths!
    use_reverse=True,
    # Convert final line segments that return to start into Z.
    # This may change the appearance of stroked paths!
    use_close_path=True,
)

# More readable form
# M -15 14 s 5 7.5 15 7.5 S 15 14 15 14 z
print(optimized)
# Minified form
# M-15 14s5 7.5 15 7.5S15 14 15 14z
print(f"{optimized:m}")
```

## 🧪 Testing

This project includes `pytest`-based tests that cover the entire code base with 100% code coverage.

The development dependencies can be installed via the `dev` optional group:

```sh
pip install .[dev]
```

All tests (including coverage reporting using `pytest-cov`) can then be run from the project root:

```sh
pytest --cov
```

## 📜 License

This library is licensed under the terms of the Mozilla Public License 2.0, provided in [`License`](https://github.com/KurtBoehm/svg-path-editor/blob/main/License).
The original TypeScript library is licensed under the Apache License, Version 2.0, provided in [`LicenseYqnn`](https://github.com/KurtBoehm/svg-path-editor/blob/main/LicenseYqnn).
