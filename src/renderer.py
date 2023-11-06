from __future__ import annotations
from typing import TYPE_CHECKING

from .exceptions import NotAMacroException
from .iterator import CommentFilter, GCodeMacroReader, GCodeIterator

if TYPE_CHECKING:
    from .line import GCodeLine
    from extras.gcode_loader.dispatch import GCodeDispatchHelper


class Renderer:  # todo remove
    helper: GCodeDispatchHelper
    shallow_macros: set[str]

    def __init__(self, helper: GCodeDispatchHelper, shallow_macros: list[str]):
        self.helper = helper
        self.shallow_macros = set(map(lambda m: m.upper(), shallow_macros))

    def render(self, line: GCodeLine) -> GCodeIterator:
        if line.cmd.upper() in self.shallow_macros or not self.helper.has_macro(line.cmd):
            raise NotAMacroException()

        return self._render(line)

    def _render(self, line: GCodeLine) -> GCodeIterator:
        return CommentFilter(GCodeMacroReader(line.cmd, self._render_macro(line), line))

    def _render_macro(self, line: GCodeLine) -> str:
        macro = self.helper.get_macro(line.cmd)

        kwparams = dict(macro.variables)
        kwparams.update(macro.template.create_template_context())
        kwparams['params'] = line.params
        kwparams['rawparams'] = line.rawparams

        return macro.template.render(kwparams)
