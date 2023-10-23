from __future__ import annotations
from typing import Optional
from .base import GCodeIterator

from ..line import GCodeLine, CompiledGcodeLine


class GCodeStringReader(GCodeIterator):
    def __init__(self, data: str):
        self.data = data
        self.lines = data.split('\n')
        self.no = 0
        self._pos = 0

    def __next__(self) -> GCodeLine:
        try:
            line = self.lines.pop(0)
            self.no += 1
            gcode_line = self._create_line(line)
            self._pos += 1 + len(line)
            return gcode_line
        except IndexError:
            raise StopIteration()

    def _create_line(self, line: str) -> GCodeLine:
        return GCodeLine(line)

    def close(self):
        self.lines = []

    @property
    def pos(self):
        return self._pos

    def seek(self, pos: int):
        pass # todo


class GCodeMacroReader(GCodeStringReader):
    def __init__(self, macro: str, data: str, parent: Optional[GCodeLine] = None):
        super().__init__(data)
        self.macro = macro
        self.parent = parent


    def _create_line(self, line: str) -> GCodeLine:
        return CompiledGcodeLine(self.macro, self.no, line, self.parent)
