from __future__ import annotations

from typing import Optional
from typing import TYPE_CHECKING
from .comment_filter import CommentFilter
from .string_reader import GCodeMacroReader
from .base import GCodeIterator
from .base import GCodeProxyIterator
from ..line import GCodeLine

if TYPE_CHECKING:
    from ..dispatch import GCodeDispatchHelper


class RecursiveIterator(GCodeProxyIterator):
    helper: GCodeDispatchHelper
    nested: list[GCodeIterator]
    uninterrupted_macros: set[str]

    def __init__(self, inner: GCodeIterator, helper: GCodeDispatchHelper, uninterrupted_macros: Optional[set[str]] = None):
        super().__init__(inner)
        self.helper = helper
        self.nested = []
        self.uninterrupted_macros = uninterrupted_macros or set()

    def _get_next_line(self) -> GCodeLine:
        while len(self.nested) > 0:
            try:
                return next(self.nested[0])
            except StopIteration:
                self.nested.pop(0)
                continue

        return next(self.inner)

    def __next__(self):
        while True:
            line = self._get_next_line()
            if self.helper.has_macro(line.cmd):
                macro = self.helper.get_macro(line.cmd)
                content = macro.render(line.params, line.rawparams)
                self.nested.insert(0, CommentFilter(GCodeMacroReader(line.cmd, content, line)))
            else:
                return line

    def seek(self, pos: int):
        super().seek(pos)
        self.nested = []

    def close(self):
        super().close()
        self.nested = []
