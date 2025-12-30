# This file is part of https://github.com/KurtBoehm/svg_path_editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re
from typing import Final

__all__ = ["PathParser"]

_cmd_type_re: Final = re.compile(r"^[\t\n\f\r ]*([MLHVZCSQTAmlhvzcsqta])[\t\n\f\r ]*")
_flag_re: Final = re.compile(r"^[01]")
_number_re: Final = re.compile(r"^[+-]?((\d*\.\d+)|(\d+\.)|(\d+))([eE][+-]?\d+)?")
_coord_re: Final = _number_re
_comma_wsp: Final = re.compile(r"^(([\t\n\f\r ]+,?[\t\n\f\r ]*)|(,[\t\n\f\r ]*))")

grammar: Final = {
    "M": [_coord_re, _coord_re],
    "L": [_coord_re, _coord_re],
    "H": [_coord_re],
    "V": [_coord_re],
    "Z": [],
    "C": [_coord_re, _coord_re, _coord_re, _coord_re, _coord_re, _coord_re],
    "S": [_coord_re, _coord_re, _coord_re, _coord_re],
    "Q": [_coord_re, _coord_re, _coord_re, _coord_re],
    "T": [_coord_re, _coord_re],
    "A": [_number_re, _number_re, _coord_re, _flag_re, _flag_re, _coord_re, _coord_re],
}


class PathParser:
    """Low-level SVG path string parser.

    This class understands the SVG path mini-language (M/L/H/V/Z/C/S/Q/T/A)
    and converts a path string into a list of token lists
    ``[command, arg1, arg2, ...]`` without interpreting coordinates.
    """

    @staticmethod
    def components(
        cmd_type: str, path: str, cursor: int
    ) -> tuple[int, list[list[str]]]:
        """Parse a run of components for a single command type.

        Starting at ``cursor``, this consumes as many valid components of
        ``cmd_type`` as possible (including implicit repeats of the command)
        and returns the new cursor position together with the parsed
        components.

        :param cmd_type: Single-letter SVG path command (e.g. ``"M"``, ``"l"``).
        :param path: Full SVG path string being parsed.
        :param cursor: Current index in ``path`` to start parsing from.
        :returns: A tuple ``(new_cursor, components)`` where ``components`` is
                  a list of ``[command, arg1, arg2, ...]`` token lists.
        :raises ValueError: If the path is malformed at or after ``cursor``.
        """
        expected_regex_list = grammar[cmd_type.upper()]

        components: list[list[str]] = []
        while cursor <= len(path):
            component: list[str] = [cmd_type]
            for regex in expected_regex_list:
                segment = path[cursor:]
                match = regex.match(segment)
                if match is not None:
                    text = match.group(0)
                    component.append(text)
                    cursor += len(text)
                    ws_match = _comma_wsp.match(path[cursor:])
                    if ws_match is not None:
                        cursor += len(ws_match.group(0))
                elif len(component) == 1 and len(components) >= 1:
                    return cursor, components
                else:
                    raise ValueError(f"malformed path (first error at {cursor})")
            components.append(component)
            if len(expected_regex_list) == 0:
                return cursor, components
            if cmd_type == "m":
                cmd_type = "l"
            if cmd_type == "M":
                cmd_type = "L"
        raise ValueError(f"malformed path (first error at {cursor})")

    @staticmethod
    def parse(path: str) -> list[list[str]]:
        """Parse an SVG path data string into a list of token lists.

        Each element in the returned list is of the form
        ``[command, arg1, arg2, ...]``, where all items are strings and
        no semantic interpretation (e.g. absolute vs. relative coordinates)
        is performed here.

        :param path: Raw SVG path data string (the value of a ``d`` attribute).
        :returns: A list of command components as token lists.
        :raises ValueError: If the path is syntactically malformed.
        """
        cursor = 0
        tokens: list[list[str]] = []
        while cursor < len(path):
            match = _cmd_type_re.match(path[cursor:])
            if match is not None:
                command = match.group(1)
                if cursor == 0 and command.lower() != "m":
                    raise ValueError(f"malformed path (first error at {cursor})")
                cursor += len(match.group(0))
                new_cursor, component_list = PathParser.components(
                    command, path, cursor
                )
                cursor = new_cursor
                tokens.extend(component_list)
            else:
                raise ValueError(f"malformed path (first error at {cursor})")
        return tokens
