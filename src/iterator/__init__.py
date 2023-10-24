from __future__ import annotations
from typing import TYPE_CHECKING

from .base import GCodeIterator, GCodeProxyIterator
from .comment_filter import CommentFilter
from .file_reader import GCodeFileReader
from .recursive_iterator import RecursiveIterator
from .string_reader import GCodeStringReader, GCodeMacroReader

if TYPE_CHECKING:
    from ..file import GCodeFile
    from ..renderer import Renderer


def full_file_iterator(file: GCodeFile, renderer: Renderer):
    return RecursiveIterator(CommentFilter(GCodeFileReader(file)), renderer)
