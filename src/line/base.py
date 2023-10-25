from __future__ import annotations

from functools import cached_property
import re
from typing import Optional
import copy

BLANK_SPLIT_REGEX = re.compile('\s+')
CLASSIC_SPLIT_REGEX = re.compile('([A-Z*/])')


def _fix_param(param: str) -> str:
    if param.startswith('"') and param.endswith('"') or param.startswith('"') and param.endswith('"'):
        return param[1:-1]
    return param


class GCodeLine:
    def __init__(self, data: str):
        self.data = data.strip()

    def copy(self, data: Optional[str] = None):
        copied = copy.copy(self)

        if data is not None:
            copied.data = data

        return copied

    def __repr__(self):
        return f'[{self.data}]'

    def __str__(self):
        return self.__repr__()

    @cached_property
    def _split(self):
        line = self.data
        cpos = line.find(';')
        if cpos >= 0:
            line = line[:cpos]

        split = line.strip().split(' ', maxsplit=1)
        if len(split) == 2:
            return (split[0].upper(), split[1].lstrip())
        return (split[0].upper(), '')

    @cached_property
    def cmd(self) -> Optional[str]:
        command, _ = self._split
        if len(command) == 0:
            return None

        return command

    @cached_property
    def is_classic(self) -> bool:
        if self.cmd is None:
            return False

        return re.match(r'^[MGT][0-9]+(:?\.[0-9]+)?$', self.cmd) is not None

    @cached_property
    def params(self):
        _, rawparams = self._split
        if len(rawparams) == 0:
            return {}

        parts = BLANK_SPLIT_REGEX.split(rawparams)

        mapper = lambda s: s.split('=', maxsplit=1)
        if self.is_classic:
            mapper = lambda s: CLASSIC_SPLIT_REGEX.split(s)[1:]

        return {s[0].upper(): _fix_param(s[1].strip()) for s in map(mapper, parts)}

    @cached_property
    def rawparams(self):
        command = self.cmd or ''
        if command in ('M117', 'M118'):
            command = command[:4]
        rawparams = self.data
        urawparams = rawparams.upper()
        if not urawparams.startswith(command):
            rawparams = rawparams[urawparams.find(command):]
            end = rawparams.rfind('*')
            if end >= 0:
                rawparams = rawparams[:end]
        rawparams = rawparams[len(command):]
        if rawparams.startswith(' '):
            rawparams = rawparams[1:]
        return rawparams


if __name__ == '__main__':
    for s in ('; asd', ' ; asd', '  \t  ; asd', '\t  ; asd', '\t; asd'):
        line = GCodeLine(s)
        assert line.cmd is None, f"{line.cmd} == None"
        assert line.rawparams == s.strip(), f"{line.rawparams} == {s.strip()}"
        assert len(line.params) == 0, f"{len(line.params) == 0}"

    line = GCodeLine('G1 A6.876 B887.06')
    assert line.cmd == 'G1', f"{line.cmd} == G1"
    assert line.rawparams == 'A6.876 B887.06', f"{line.rawparams} == 'A6.876 B887.06'"
    assert len(line.params) == 2, f"{len(line.params)} == 2; {line.params}"
    assert line.params['A'] == '6.876', f"{line.params['A']} == '6.876'"
    assert line.params['B'] == '887.06', f"{line.params['B']} == '887.06'"

    for s in ('M117 asd goes here', 'M118 asd goes here'):
        line = GCodeLine(s)
        assert line.cmd in ('M117', 'M118'), f"{line.cmd} in ('M117', 'M118')"
        assert line.rawparams == 'asd goes here', f"{line.rawparams} == 'asd goes here'"

    line = GCodeLine('MY_MACRO A=6 param=8 foo="baz"')
    assert line.cmd == 'MY_MACRO', f"{line.cmd} == MY_MACRO"
    assert line.rawparams == 'A=6 param=8 foo="baz"', f"{line.rawparams} == 'A=6 param=8 foo=\"baz\"'"
    assert len(line.params) == 3, f"{len(line.params)} == 0; {line.params}"
    assert line.params['A'] == '6', f"{line.params['A']} == '6'"
    assert line.params['PARAM'] == '8', f"{line.params['PARAM']} == '8'"
    assert line.params['FOO'] == '"baz"', f"{line.params['FOO']} == '\"baz\"'"
