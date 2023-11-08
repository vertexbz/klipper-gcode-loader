from __future__ import annotations
from abc import abstractmethod
from typing import Iterator
from typing import Optional

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


class GCodeFileIterator(GCodeIterator):
    __slots__ = ()

    @abstractmethod
    def current(self) -> GCodeLine:
        pass

    @property
    @abstractmethod
    def name(self):
        pass

    @property
    @abstractmethod
    def path(self):
        pass

    @property
    @abstractmethod
    def size(self):
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


class GCodeFileProxyIterator(GCodeFileIterator):
    current_line: Optional[GCodeLine]
    preread_line: Optional[GCodeLine]

    __slots__ = ()

    def __init__(self, inner: GCodeIterator):
        self.inner = inner
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
    def pos(self) -> int:
        return self.inner.pos

    def seek(self, pos: int):
        self.inner.seek(pos)

    def close(self):
        self.inner.close()
