from __future__ import annotations

from abc import abstractmethod
from typing import Iterator
from ..line import GCodeLine


class GCodeIterator(Iterator[GCodeLine]):
    __slots__ = ()

    @abstractmethod
    def __init__(self):
        pass

    def __iter__(self):
        return self

    @abstractmethod
    def close(self):
        pass

    @property
    @abstractmethod
    def pos(self) -> int:
        pass

    @abstractmethod
    def seek(self, pos: int):
        pass


class GCodeProxyIterator(GCodeIterator):
    __slots__ = ()

    def __init__(self, inner: GCodeIterator):
        self.inner = inner

    def __next__(self):
        return next(self.inner)

    @property
    def pos(self) -> int:
        return self.inner.pos

    def seek(self, pos: int):
        self.inner.seek(pos)

    def close(self):
        self.inner.close()
