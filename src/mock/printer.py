from __future__ import annotations
from .printer_gcode import GCode


class Printer:
    def lookup_object(self, key: str):
        if key == 'gcode':
            return GCode()

        raise NotImplementedError(f'lookup_object({key}) is not mocked')
