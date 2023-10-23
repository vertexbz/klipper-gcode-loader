from __future__ import annotations
from .base import GCodeIterator, GCodeProxyIterator
from ..line import GCodeLine
from ..template_renderer import Renderer, NotAMacroException


class MachineGCodeGenerator(GCodeProxyIterator):
    renderer: Renderer
    compiled: list[GCodeLine]

    def __init__(self, inner: GCodeIterator, renderer: Renderer):
        super().__init__(inner)
        self.renderer = renderer
        self.compiled = []

    def _get_next_line(self) -> GCodeLine:
        if len(self.compiled) > 0:
            return self.compiled.pop(0)
        return self.inner.__next__()

    def __next__(self):
        while True:
            line = self._get_next_line()
            try:
                self.compiled = list(self.renderer.render(line)) + self.compiled
                continue
            except NotAMacroException:
                return line

    def seek(self, pos: int):
        super().seek(pos)
        self.compiled = []

    def close(self):
        super().close()
        self.compiled = []
