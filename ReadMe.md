# 🎨 SVG Path Editor

A small, high-precision library for editing, transforming, and optimizing SVG paths programmatically in Python.

It is a port of [`svg-path-editor-lib`](https://www.npmjs.com/package/svg-path-editor-lib) 1.0.3 to Python with significant improvements:

- **Decimal-based geometry**: all coordinates are stored as `decimal.Decimal`, with high-precision SymPy-based computations where appropriate. This preserves the decimal values stored in an SVG path and avoids the binary round-off errors that occur with `float`.
- **In-place and out-of-place operations**: most geometric operations are available in a mutating (`scale`, `rotate`, …) and a non-mutating (`scaled`, `rotated`, …) variant.
- **`list`-like path modification API**: path-level manipulations (insert, remove, change type, …) are exposed as methods on `SvgPath`.
- **Typed and documented**: extensive type hints and docstrings for good IDE support and static analysis.

The **full documentation** is available on [Read the Docs](https://svg-path-editor.readthedocs.io), and the `pytest`-based **test suite** is defined in the [`tests` directory](https://github.com/KurtBoehm/polyqr/blob/main/tests).

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

## 🧱 Path Modification

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

## 🧱 Higher-Level Path Operations

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

## 🧮 Decimal-Based Geometry

Internally, all coordinates and numeric parameters are stored as `decimal.Decimal`:

- Constructors and geometric methods accept `int`, `float`, `str`, or `Decimal`; values are converted to `Decimal` immediately.
- Arithmetic (translation, scaling, rotation, etc.) is performed in terms of `Decimal` to retain the decimal representation in an SVG path and avoid introducing binary round-off errors.
- The decimal precision can be controlled via Python’s `decimal` context.

```python
from decimal import localcontext
from svg_path_editor import SvgPath

path = SvgPath("M0 0h10v10z")

# Default precision: 28 places
# Rotation computed with SymPy for high-precision trigonometric functions
rotated = path.rotated(0, 0, -45)
# M 0 0 l 7.071067811865475244008443621 -7.071067811865475244008443621 l 7.071067811865475244008443621 7.071067811865475244008443621 z
print(rotated)
# Precision can be reduced when printing
# M 0 0 l 7.07107 -7.07107 l 7.07107 7.07107 z
print(f"{rotated:.5}")

# The precision can be controlled using `getcontext`/`localcontext`
# Since `Decimal` is a floating-point format, the precision specifies the overall
# number of digits, not just the number of decimal places!
with localcontext() as ctx:
    ctx.prec = 6
    rotated = path.rotated(0, 0, -45)
    # The same output as before, even without precision reduction
    # M 0 0 l 7.07107 -7.07107 l 7.07107 7.07107 z
    print(rotated)
```

## 🧹 Path Optimization

`optimize_path` rewrites a path into an equivalent but more compact form and is also out-of-place:

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

The project includes `pytest`-based tests that cover the main operations and a range of edge cases.

The development dependencies can be installed via the `dev` optional group:

```sh
pip install .[dev]
```

All tests can then be run from the project root:

```sh
pytest
```

## 📜 License

This library is licensed under the terms of the Mozilla Public License 2.0, provided in [`License`](https://github.com/KurtBoehm/polyqr/blob/main/License).
The original TypeScript library is licensed under the Apache License, Version 2.0, provided in [`LicenseYqnn`](https://github.com/KurtBoehm/polyqr/blob/main/LicenseYqnn).
