# 🎨 SVG Path Editor

A small library for editing, transforming, and optimizing SVG paths programmatically in Python.

It is a port of [`svg-path-editor-lib`](https://www.npmjs.com/package/svg-path-editor-lib) 1.0.3 to Python with a more Pythonic interface:

- **Out-of-place by default**: most operations return new objects instead of mutating in place, similar to `datetime` or `pathlib`.
- **Typed and documented**: extensive type hints and docstrings for good IDE support and static analysis.
- **Tested**: [`tests`](https://github.com/KurtBoehm/polyqr/blob/main/tests) contains `pytest`-based tests.

## 📦 Installation

This package is on PyPI and can be installed with `pip`:

```sh
pip install svg-path-editor
```

## 🚀 Basic usage

```python
from svg_path_editor import SvgPath, change_path_origin, optimize_path, reverse_path

path = SvgPath("M-15 14s5 7.5 15 7.5 15-7.5 15-7.5 z")

# `SvgPath` implements `__str__` with fairly readable (non-minified) output
# M -15 14 s 5 7.5 15 7.5 s 15 -7.5 15 -7.5 z
print(path)

# Custom decimals and minified output (decimals=None, minify=False by default)
# M-15 14s5 7.5 15 7.5 15-7.5 15-7.5z
print(path.as_string(decimals=1, minify=True))
```

## 📐 Geometric Operations

All geometric operations are out-of-place:

```python
# Scale
# M -30 28 s 10 15 30 15 s 30 -15 30 -15 z
print(path.scale(kx=2, ky=2))

# Translate
# M -14 14.5 s 5 7.5 15 7.5 s 15 -7.5 15 -7.5 z
print(path.translate(dx=1, dy=0.5))

# Rotate around (0, 0)
# M -14 -15 s -7.5 5 -7.5 15 s 7.5 15 7.5 15 z
print(path.rotate(ox=0, oy=0, degrees=90).as_string(decimals=2))
```

## 🔁 Absolute vs. Relative Commands

Convert between equivalent absolute (`M`, `L`, `C`, …) and relative (`m`, `l`, `c`, …) representations, either in-place or out-of-place:

```python
# In-place: `SvgPath.relative` mutates the instance
absolute = path.clone()
absolute.relative = False
# M -15 14 S -10 21.5 0 21.5 S 15 14 15 14 Z
print(absolute)

# Out-of-place: `SvgPath.with_relative()` returns a new path
relative = path.with_relative(True)
# m -15 14 s 5 7.5 15 7.5 s 15 -7.5 15 -7.5 z
print(relative)
```

## 🧱 Higher-Level Path Operations

These functions operate on paths out-of-place:

```python
# Reverse path direction
# M 15 14 S 10 21.5 0 21.5 S -15 14 -15 14 Z
print(reverse_path(path))

# Change the origin (starting command) within a subpath
# M 0 21.5 c 10 0 15 -7.5 15 -7.5 L -15 14 s 5 7.5 15 7.5
print(change_path_origin(path, new_origin_index=2))
```

## 🧹 Path Optimization

`optimize_path` rewrites a path into an equivalent but more compact form and is also out-of-place:

```python
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
print(optimized.as_string(minify=True))
```

## 🧪 Testing

The project includes `pytest`-based tests that cover most operations.

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
