from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from .base import GCodeFile
from ..iterator import full_file_iterator, GCodeIterator

if TYPE_CHECKING:
    from ..line import GCodeLine
    from ..renderer import Renderer


class OpenGcodeFile(GCodeFile):
    handle: GCodeIterator
    current_line: Optional[GCodeLine]
    preread_line: Optional[GCodeLine]

    def __init__(self, renderer: Renderer, basedir: str, name: str):
        super().__init__(basedir, name)
        self.handle = full_file_iterator(self, renderer)
        self.current_line = None
        self.preread_line = None

    @property
    def pos(self) -> int:
        return self.handle.pos

    def next(self) -> GCodeLine:
        if self.preread_line is not None:
            self.current_line = self.preread_line
            self.preread_line = None
        else:
            self.current_line = next(self.handle)

        return self.current_line

    def current(self) -> GCodeLine:
        if self.current_line is not None:
            return self.current_line

        if self.preread_line is not None:
            return self.preread_line

        self.preread_line = next(self.handle)
        return self.preread_line

    def backoff(self):
        if self.preread_line is not None:
            raise RuntimeError('can backoff only once')
        self.preread_line = self.current_line

    def close(self):
        self.handle.close()

    def seek(self, pos: int):
        self.handle.seek(pos)
