from __future__ import annotations
from .base import GCodeProxyIterator


class CommentFilter(GCodeProxyIterator):
    def __next__(self):
        while True:
            line = next(self.inner)
            if len(line.data) == 0 or line.data.startswith(';'):
                continue
            return line
