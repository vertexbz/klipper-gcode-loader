from __future__ import annotations
from typing import Optional
from typing import TYPE_CHECKING
from .base import GCodeIterator, GCodeProxyIterator
from .comment_filter import CommentFilter
from .file_reader import GCodeFileReader
from .recursive_iterator import RecursiveIterator
from .string_reader import GCodeStringReader, GCodeMacroReader
from .file_iterator import FileIterator

if TYPE_CHECKING:
    from ..file import GCodeFile
    from ..dispatch import GCodeDispatchHelper


def full_gcode_iterator(reader: GCodeIterator, helper: GCodeDispatchHelper, uninterrupted: Optional[set[str]] = None):
    return RecursiveIterator(CommentFilter(reader), helper, uninterrupted_macros=uninterrupted)


def full_file_iterator(file: GCodeFile, helper: GCodeDispatchHelper, uninterrupted_macros: Optional[set[str]] = None):
    return FileIterator(file, full_gcode_iterator(GCodeFileReader(file), helper, uninterrupted_macros))
