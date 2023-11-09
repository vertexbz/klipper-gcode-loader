from __future__ import annotations
from typing import TYPE_CHECKING

from .base import GCodeLine

if TYPE_CHECKING:
    from ..file import GCodeFile


class GCodeFileLine(GCodeLine):
    def __init__(self, file: GCodeFile, offset: int, data: str):
        super().__init__(data)
        self.file = file
        self.offset = offset

    def __repr__(self):
        return f'  - {self.offset}: {self.data}'
