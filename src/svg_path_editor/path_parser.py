# This file is part of https://github.com/KurtBoehm/svg_path_editor.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re
from typing import Final

cmd_type_re: Final = re.compile(r"^[\t\n\f\r ]*([MLHVZCSQTAmlhvzcsqta])[\t\n\f\r ]*")
flag_re: Final = re.compile(r"^[01]")
number_re: Final = re.compile(r"^[+-]?((\d*\.\d+)|(\d+\.)|(\d+))([eE][+-]?\d+)?")
coord_re: Final = number_re
comma_wsp: Final = re.compile(r"^(([\t\n\f\r ]+,?[\t\n\f\r ]*)|(,[\t\n\f\r ]*))")

grammar: Final = {
    "M": [coord_re, coord_re],
    "L": [coord_re, coord_re],
    "H": [coord_re],
    "V": [coord_re],
    "Z": [],
    "C": [coord_re, coord_re, coord_re, coord_re, coord_re, coord_re],
    "S": [coord_re, coord_re, coord_re, coord_re],
    "Q": [coord_re, coord_re, coord_re, coord_re],
    "T": [coord_re, coord_re],
    "A": [number_re, number_re, coord_re, flag_re, flag_re, coord_re, coord_re],
}


class PathParser:
    @staticmethod
    def components(
        cmd_type: str, path: str, cursor: int
    ) -> tuple[int, list[list[str]]]:
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
                    ws_match = comma_wsp.match(path[cursor:])
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
        cursor = 0
        tokens: list[list[str]] = []
        while cursor < len(path):
            match = cmd_type_re.match(path[cursor:])
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
