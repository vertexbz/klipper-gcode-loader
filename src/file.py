from __future__ import annotations
from functools import cached_property
import os


class GCodeFile:
    def __init__(self, basedir: str, name: str):
        self.basedir = basedir
        self.name = name

    @cached_property
    def path(self):
        return os.path.join(self.basedir, self.name)

    @cached_property
    def size(self):
        return os.path.getsize(self.path)
