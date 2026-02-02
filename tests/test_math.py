# This file is part of https://github.com/KurtBoehm/svg-path-editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from svg_path_editor.math import as_bool, polynomial_roots


def test_as_bool_invalid() -> None:
    import sympy as sp

    x = sp.Symbol("x")

    with pytest.raises(ValueError):
        as_bool(x)


def test_constant_roots() -> None:
    import sympy as sp

    x = sp.Symbol("x")

    with pytest.raises(ValueError):
        polynomial_roots(sp.S.Zero, x)

    assert polynomial_roots(sp.S.One, x) == {}


def test_linear_roots() -> None:
    import sympy as sp

    x = sp.Symbol("x")

    assert polynomial_roots(x + 1, x) == {-1: 1}
    assert polynomial_roots(x - 2, x) == {2: 1}


def test_cubic_roots() -> None:
    import sympy as sp

    x = sp.Symbol("x")

    sols = polynomial_roots((x + 1) ** 3, x)
    assert sols == {-1: 3}

    sols = polynomial_roots(x**3 + 8, x, real_only=True)
    assert sols == {-2: 1}


def test_quintic_roots() -> None:
    import sympy as sp

    x = sp.Symbol("x")

    with pytest.raises(ValueError):
        polynomial_roots(x**5, x)
