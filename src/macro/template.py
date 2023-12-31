from __future__ import annotations
import hashlib
import jinja2
import logging
import traceback
from typing import Any
from typing import Optional
from typing import Union
from typing import TYPE_CHECKING
from gcode import CommandError
from ..interfaces.macro import MacroTemplateInterface
from ..interfaces.macro import RequiredMacroContextKeys

if TYPE_CHECKING:
    from ..dispatch import GCodeDispatchHelper


class MacroTemplate(MacroTemplateInterface):
    @classmethod
    def hash_source(cls, value: str):
        return hashlib.sha256(value.encode('utf-8')).hexdigest()

    def __init__(self, helper: GCodeDispatchHelper, template: str, name: str):
        self.name = name
        self.helper = helper
        self.hash = MacroTemplate.hash_source(template)
        self.template: jinja2.Template = helper.gcode_macro.jinja.from_string(template)

    def render(self, context: Optional[dict] = None) -> str:
        if context is None:
            context = self.create_template_context()
        try:
            return str(self.template.render(context))
        except Exception as e:
            msg = "Error evaluating macro %s: %s" % (self.name, traceback.format_exception_only(type(e), e)[-1])
            logging.exception(msg)
            if isinstance(e, CommandError):
                raise e
            raise CommandError(msg)

    def run_gcode_from_command(self, context: Optional[dict] = None):
        self.helper.run_script_from_command(self.render(context), name=self.name)

    def create_template_context(self, eventtime=None) -> dict[Union[RequiredMacroContextKeys, str], Any]:
        return self.helper.create_template_context(eventtime)
