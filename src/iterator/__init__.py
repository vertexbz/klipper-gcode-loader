from __future__ import annotations
from typing import Optional
from typing import TYPE_CHECKING
from .base import GCodeIterator, GCodeFileIterator
from .comment_filter import CommentFilter
from .file_reader import GCodeFileReader
from .recursive_iterator import RecursiveIterator
from .string_reader import GCodeStringReader, GCodeMacroReader
from .with_file_iterator import WithFileIterator
from .with_virtual_file_iterator import WithVirtualFileIterator

if TYPE_CHECKING:
    from ..file import GCodeFile
    from ..dispatch import GCodeDispatchHelper


def full_gcode_iterator(reader: GCodeIterator, helper: GCodeDispatchHelper, uninterrupted: Optional[set[str]] = None):
    return RecursiveIterator(CommentFilter(reader), helper, uninterrupted_macros=uninterrupted)


def full_macro_iterator(name: str, script: str, helper: GCodeDispatchHelper, uninterrupted: Optional[set[str]] = None):
    return RecursiveIterator(CommentFilter(GCodeMacroReader(name, script)), helper, uninterrupted_macros=uninterrupted)


def full_script_iterator(script: str, helper: GCodeDispatchHelper, uninterrupted: Optional[set[str]] = None):
    return RecursiveIterator(CommentFilter(GCodeStringReader(script)), helper, uninterrupted_macros=uninterrupted)


def full_virtual_file_iterator(script: str, helper: GCodeDispatchHelper, uninterrupted_macros: Optional[set[str]] = None,
                         name: str = 'Custom script', size: int = 0):
    return WithVirtualFileIterator(name, full_gcode_iterator(GCodeStringReader(script), helper, uninterrupted_macros),
                                   size=size)


def full_file_iterator(file: GCodeFile, helper: GCodeDispatchHelper, uninterrupted_macros: Optional[set[str]] = None):
    return WithFileIterator(file, full_gcode_iterator(GCodeFileReader(file), helper, uninterrupted_macros))
