from __future__ import annotations

from functools import cached_property
from typing import Optional
import copy
from gcode import GCodeDispatch


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
    def _parts(self):
        line = self.data
        cpos = line.find(';')
        if cpos >= 0:
            line = line[:cpos]

        return GCodeDispatch.args_r.split(line.upper())

    @cached_property
    def cmd(self):
        parts = self._parts
        numparts = len(parts)
        if numparts >= 3 and parts[1] != 'N':
            return parts[1] + parts[2].strip()
        elif numparts >= 5 and parts[1] == 'N':
            return parts[3] + parts[4].strip()

        return ''

    @cached_property
    def params(self):
        parts = self._parts
        return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}

    @cached_property
    def rawparams(self):
        command = self.cmd
        if command.startswith("M117 ") or command.startswith("M118 "):
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
