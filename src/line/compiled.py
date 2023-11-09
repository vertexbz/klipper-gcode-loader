from __future__ import annotations
from typing import Optional
from .base import GCodeLine


class CompiledGcodeLine(GCodeLine):
    def __init__(self, macro: str, line: int, data: str, parent: Optional[GCodeLine] = None):
        super().__init__(data)
        self.macro = macro
        self.line = line
        self.parent = parent

    def __repr__(self):
        current = f'  - {self.macro}:{self.line}: {self.data}'
        if self.parent:
            return f'{str(self.parent)}\n{current}'
        return current
