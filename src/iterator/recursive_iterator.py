from __future__ import annotations
from typing import TYPE_CHECKING
from .base import GCodeIterator, GCodeProxyIterator
from ..line import GCodeLine
from ..exceptions import NotAMacroException
import logging

if TYPE_CHECKING:
    from ..renderer import Renderer


class RecursiveIterator(GCodeProxyIterator):
    renderer: Renderer
    nested: list[GCodeIterator]

    def __init__(self, inner: GCodeIterator, renderer: Renderer):
        super().__init__(inner)
        self.renderer = renderer
        self.nested = []

    def _get_next_line(self) -> GCodeLine:
        logging.info(f'recursive next line')
        while True:
            if len(self.nested) > 0:
                try:
                    return next(self.nested[0])
                except StopIteration:
                    self.nested.pop(0)
                    continue

        return next(self.inner)

    def __next__(self):
        logging.info(f'recursive next')
        while True:
            line = self._get_next_line()

            logging.info(f'recursive line {line}')
            try:
                self.nested.insert(0, self.renderer.render(line))
                continue
            except NotAMacroException:
                return line

    def seek(self, pos: int):
        super().seek(pos)
        self.nested = []

    def close(self):
        super().close()
        self.nested = []
