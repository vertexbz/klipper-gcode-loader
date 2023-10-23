from __future__ import annotations
from typing import TYPE_CHECKING

from .base import GCodeIterator, GCodeProxyIterator
from .comment_filter import CommentFilter
from .file_reader import GCodeFileReader
from .machine_code_generator import MachineGCodeGenerator
from .string_reader import GCodeStringReader, GCodeMacroReader

if TYPE_CHECKING:
    from ..file import GCodeFile
    from ..template_renderer import Renderer

def full_file_iterator(file: GCodeFile, renderer: Renderer):
    return MachineGCodeGenerator(CommentFilter(GCodeFileReader(file)), renderer)
