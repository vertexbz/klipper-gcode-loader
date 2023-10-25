from __future__ import annotations
import collections
from typing import TYPE_CHECKING, Iterable

from .exceptions import NotAMacroException
from .iterator import CommentFilter, GCodeMacroReader, GCodeIterator

if TYPE_CHECKING:
    from .line import GCodeLine
    from extras.gcode_macro import GCodeMacro


class Renderer:
    known_macros: set[str]
    shallow_macros: set[str]
    objects: collections.OrderedDict

    def __init__(self, macros: Iterable[str], objects: collections.OrderedDict, shallow_macros: list[str]):
        self.known_macros = set(map(lambda m: m.upper(), macros))
        self.shallow_macros = set(map(lambda m: m.upper(), shallow_macros))
        self.objects = objects

    def render(self, line: GCodeLine) -> GCodeIterator:
        if line.cmd.upper() in self.shallow_macros or line.cmd.upper() not in self.known_macros:
            raise NotAMacroException()

        return self._render(line)

    def add_known_macro(self, macro: str):
        self.known_macros.add(macro.upper())

    def remove_known_macro(self, macro: str):
        self.known_macros.remove(macro.upper())

    def _render(self, line: GCodeLine) -> GCodeIterator:
        return CommentFilter(GCodeMacroReader(line.cmd, self._render_macro(line), line))

    def _find_macro(self, macro: str) -> GCodeMacro:
        if f'gcode_macro {macro}' in self.objects:
            return self.objects[f'gcode_macro {macro}']

        if f'gcode_macro {macro.lower()}' in self.objects:
            return self.objects[f'gcode_macro {macro.lower()}']

        for key in self.objects.keys():
            if key.upper() == f'GCODE_MACRO {macro}':
                return self.objects[key]

        raise KeyError(f'no macro {macro} found')

    def _render_macro(self, line: GCodeLine) -> str:
        macro = self._find_macro(line.cmd.upper())

        kwparams = dict(macro.variables)
        kwparams.update(macro.template.create_template_context())
        kwparams['params'] = line.params
        kwparams['rawparams'] = line.rawparams

        return macro.template.render(kwparams)
