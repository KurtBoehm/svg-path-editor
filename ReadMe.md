# SVG Path Editor

This is a straight-forward port of [`svg-path-editor-lib`](https://www.npmjs.com/package/svg-path-editor-lib) 1.0.3 to Python with minor changes to make the interface more Pythonic.

This package is available on PyPI and can be installed using `pip`:

```sh
pip install svg-path-editor
```

Basic usage:

```python
from svg_path_editor import SvgPath, change_path_origin, optimize_path, reverse_path

path = SvgPath("M-15 14s5 7.5 15 7.5 15-7.5 15-7.5 z")
# M -15 14 s 5 7.5 15 7.5 s 15 -7.5 15 -7.5 z
print(path)
# Custom decimals and minified output (decimals=None, minify=False by default)
# M-15 14s5 7.5 15 7.5 15-7.5 15-7.5 z
print(path.as_string(decimals=1, minify=True))

# Geometric transformations (all out-of-place)
# M -30 28 s 10 15 30 15 s 30 -15 30 -15 z
print(path.scale(kx=2, ky=2))
# M -14 14.5 s 5 7.5 15 7.5 s 15 -7.5 15 -7.5 z
print(path.translate(dx=1, dy=0.5))
# M -14 -15 s -7.5 5 -7.5 15 s 7.5 15 7.5 15 z
print(path.rotate(ox=0, oy=0, degrees=90).as_string(decimals=2))

# Make absolute/relative
# Setting relative=False mutates the clone in place
absolute = path.clone()
absolute.relative = False
# M -15 14 S -10 21.5 0 21.5 S 15 14 15 14 Z
print(absolute)
# `with_relative` is out-of-place; internally it sets `relative` on a clone
# m -15 14 s 5 7.5 15 7.5 s 15 -7.5 15 -7.5 z
print(path.with_relative(True))

# Reverse path (out-of-place)
# M 15 14 S 10 21.5 0 21.5 S -15 14 -15 14 Z
print(reverse_path(path))

# Change the origin of the path (out-of-place)
# M 0 21.5 c 10 0 15 -7.5 15 -7.5 L -15 14 s 5 7.5 15 7.5
print(change_path_origin(path, 2))

# Optimize path (out-of-place)
# All options default to False; here we enable all of them.
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
# M -15 14 s 5 7.5 15 7.5 S 15 14 15 14 z
print(optimized)
# M-15 14s5 7.5 15 7.5S15 14 15 14z
print(optimized.as_string(minify=True))
```

# License

This port is licensed under the terms of the Mozilla Public Licence 2.0, which is provided in [`License`](License).
The library this port is based on is licensed under the terms of the Apache License, Version 2.0, which is provided in [`LicenseYqnn`](LicenseYqnn).
