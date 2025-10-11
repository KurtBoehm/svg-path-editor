# SVG Path Editor

This is a straight-forward port of [`svg-path-editor-lib`](https://www.npmjs.com/package/svg-path-editor-lib) 1.0.3 to Python with minor changes to make the interface more Pythonic.
Despite these changes, most operations still operate in-place, and changing this behaviour is beyond the scope of this port.

This package is available on PyPI and can be installed using `pip`:

```sh
pip install svg-path-editor
```

Basic usage:

```python
from svg_path_editor import SvgPath, change_path_origin, optimize_path, reverse_path

path = SvgPath("M-15 14s5 7.5 15 7.5 15-7.5 15-7.5")
# M -15 14 s 5 7.5 15 7.5 s 15 -7.5 15 -7.5
print(path)
# M-15 14s5 7.5 15 7.5 15-7.5 15-7.5
# default: decimals=None, minify=False
print(path.as_string(decimals=1, minify=True))

# Transformations
# M -30 28 s 10 15 30 15 s 30 -15 30 -15
print(path.scale(kx=2, ky=2))
# M -29 28.5 s 10 15 30 15 s 30 -15 30 -15
print(path.translate(dx=1, dy=0.5))
# M -28.5 -29 s -15 10 -15 30 s 15 30 15 30
print(path.rotate(ox=0, oy=0, degrees=90).as_string(decimals=2))

# Make absolute/relative
# M -28.5 -29 S -43.5 -19 -43.5 1 S -28.5 31 -28.5 31
print(path.set_relative(False))
# m -28.5 -29 s -15 10 -15 30 s 15 30 15 30
print(path.set_relative(True))

# Reverse path
reverse_path(path)
# M -28.5 31 S -43.5 21 -43.5 1 S -28.5 -29 -28.5 -29
print(path)

# Change origin of path
change_path_origin(path, 2)
# M -43.5 1 C -43.5 -19 -28.5 -29 -28.5 -29 M -28.5 31 S -43.5 21 -43.5 1
print(path)

# Optimized path
optimize_path(
    path,
    # default `False`
    remove_useless_commands=True,
    # default `False`
    use_shorthands=True,
    # default `False`
    use_horizontal_and_vertical_lines=True,
    # default `False`
    use_relative_absolute=True,
    # default `False`
    use_reverse=True,
    # default `False`, may be destructive for stroked paths
    remove_orphan_dots=True,
    # default `False`, may be destructive for stroked paths
    use_close_path=True,
)
# M -28.5 31 s -15 -10 -15 -30 s 15 -30 15 -30
print(path)
# M-28.5 31s-15-10-15-30 15-30 15-30
print(path.as_string(minify=True))
```

# License

This port is licensed under the terms of the Mozilla Public Licence 2.0, which is provided in [`License`](License).
The library this port is based on is licensed under the terms of the Apache License, Version 2.0, which is provided in [`LicenseYqnn`](LicenseYqnn).
