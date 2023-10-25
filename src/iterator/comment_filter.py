from __future__ import annotations
from .base import GCodeProxyIterator


class CommentFilter(GCodeProxyIterator):
    def __next__(self):
        while True:
            line = next(self.inner)
            if line.cmd is None:
                continue

            return line
