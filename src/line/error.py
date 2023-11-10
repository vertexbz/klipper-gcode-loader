from __future__ import annotations
from .base import GCodeLine
from gcode import CommandError


class LineError(Exception):
    def __init__(self, line: GCodeLine, *args):
        if len(args) == 1 and isinstance(args[0], BaseException):
            super().__init__(str(args[0]))
        else:
            super().__init__(*args)
        self.line = line


class CommandLineError(CommandError):
    def __init__(self, line: GCodeLine, *args):
        if len(args) == 1 and isinstance(args[0], BaseException):
            super().__init__(str(args[0]))
        else:
            super().__init__(*args)
        self.line = line
