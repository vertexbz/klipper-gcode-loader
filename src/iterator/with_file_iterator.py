from __future__ import annotations
from typing import TYPE_CHECKING
from .base import GCodeIterator
from .base import GCodeFileProxyIterator

if TYPE_CHECKING:
    from ..file import GCodeFile


class WithFileIterator(GCodeFileProxyIterator):
    def __init__(self, file: GCodeFile, inner: GCodeIterator):
        super().__init__(inner)
        self.file = file

    @property
    def name(self):
        return self.file.name

    @property
    def path(self):
        return self.file.path

    @property
    def size(self):
        return self.file.size
