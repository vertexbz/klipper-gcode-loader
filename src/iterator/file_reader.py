from __future__ import annotations
from typing import TYPE_CHECKING
from .base import GCodeIterator
from ..line import GCodeFileLine
import logging

if TYPE_CHECKING:
    from ..file import GCodeFile


class GCodeFileReader(GCodeIterator):
    def __init__(self, file: GCodeFile):
        self.file = file
        self.handle = open(file.path, 'r', encoding='utf-8')
        self.handle.seek(0)

    def _check_open(self):
        if self.handle.closed:
            raise RuntimeError('file closed')

    def __next__(self) -> GCodeFileLine:
        logging.info(f'file next')
        self._check_open()
        pos = self.handle.tell()
        line = self.handle.readline(1024 * 8)
        if line == "":
            raise StopIteration()

        logging.info(f'file line {line}')
        return GCodeFileLine(self.file, pos, line)

    def close(self):
        self.handle.close()

    @property
    def pos(self) -> int:
        if self.handle.closed:
            return 0

        return self.handle.tell()

    def seek(self, pos: int):
        self._check_open()
        self.handle.seek(pos)
