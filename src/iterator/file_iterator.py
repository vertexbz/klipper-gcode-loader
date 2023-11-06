from __future__ import annotations
from typing import Optional
from typing import TYPE_CHECKING
from . import GCodeIterator
from .base import GCodeProxyIterator

if TYPE_CHECKING:
    from ..line import GCodeLine
    from ..file import GCodeFile


class FileIterator(GCodeProxyIterator):
    current_line: Optional[GCodeLine]
    preread_line: Optional[GCodeLine]

    def __init__(self, file: GCodeFile, inner: GCodeIterator):
        super().__init__(inner)
        self.file = file
        self.current_line = None
        self.preread_line = None

    def __next__(self):
        if self.preread_line is not None:
            self.current_line = self.preread_line
            self.preread_line = None
        else:
            self.current_line = next(self.inner)

        return self.current_line

    def current(self) -> GCodeLine:
        if self.current_line is not None:
            return self.current_line

        if self.preread_line is not None:
            return self.preread_line

        self.preread_line = next(self.inner)
        return self.preread_line

    @property
    def basedir(self):
        return self.file.basedir

    @property
    def name(self):
        return self.file.name

    @property
    def path(self):
        return self.file.path

    @property
    def size(self):
        return self.file.size
