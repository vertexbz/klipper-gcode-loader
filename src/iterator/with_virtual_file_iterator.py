from __future__ import annotations
from .base import GCodeIterator
from .base import GCodeFileProxyIterator


class WithVirtualFileIterator(GCodeFileProxyIterator):
    def __init__(self, name: str, inner: GCodeIterator, size: int = 0):
        super().__init__(inner)
        self._name = name
        self._size = size

    @property
    def name(self):
        return self._name

    @property
    def path(self):
        return '/dev/null'

    @property
    def size(self):
        return self._size
