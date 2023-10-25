from __future__ import annotations
from .base import GCodeProxyIterator
import logging


class CommentFilter(GCodeProxyIterator):
    def __next__(self):
        while True:
            line = self.inner.__next__()
            if line.cmd is None:
                continue

            logging.info(f'noncomment line {line}')
            return line
