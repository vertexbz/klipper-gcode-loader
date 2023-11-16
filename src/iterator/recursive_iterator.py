from __future__ import annotations
from typing import Optional
from typing import TYPE_CHECKING
from gcode import CommandError
from .comment_filter import CommentFilter
from .string_reader import GCodeMacroReader
from .file_reader import GCodeFileReader
from .base import GCodeIterator
from .base import GCodeProxyIterator
from ..line import GCodeLine
from ..line import CommandLineError

if TYPE_CHECKING:
    from ..dispatch import GCodeDispatchHelper


class RecursiveIterator(GCodeProxyIterator):
    helper: GCodeDispatchHelper
    nested: list[GCodeIterator]
    uninterrupted_macros: set[str]

    def __init__(
        self, inner: GCodeIterator,
        helper: GCodeDispatchHelper,
        uninterrupted_macros: Optional[set[str]] = None
    ):
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
            if line.cmd == 'SDCARD_PRINT_FILE' and int(line.params.get('INCLUDE', 0)) > 0:
                filename = line.params['FILENAME']
                try:
                    self.nested.insert(0, CommentFilter(GCodeFileReader(self.helper.locator.load_file(filename, check_subdirs=True))))
                except (CommandError, FileNotFoundError) as e:
                    raise CommandLineError(line, e)
            elif self.helper.has_macro(line.cmd):
                if self._check_recursive_call(line.cmd):
                    raise CommandLineError(line, f"Macro {line.cmd} called recursively")
                macro = self.helper.get_macro(line.cmd)
                try:
                    content = macro.render(line.params, line.rawparams)
                except CommandError as e:
                    raise CommandLineError(line, e)
                else:
                    self.nested.insert(0, CommentFilter(GCodeMacroReader(line.cmd, content, line)))
            else:
                return line

    def seek(self, pos: int):
        super().seek(pos)
        self.nested = []

    def close(self):
        super().close()
        self.nested = []

    def _check_recursive_call(self, macro: str) -> bool:
        top = self.top()
        if isinstance(top, GCodeMacroReader) and top.macro == macro:
            return True

        for it in self.nested:
            top = it.top()
            if isinstance(top, GCodeMacroReader) and top.macro == macro:
                return True

        return False
