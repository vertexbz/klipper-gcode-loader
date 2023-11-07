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

Jinja = jinja2.Environment('{%', '%}', '{', '}')


class MacroTemplate(MacroTemplateInterface):
    @classmethod
    def hash_source(cls, value: str):
        return hashlib.sha256(value.encode('utf-8')).hexdigest()

    def __init__(self, helper: GCodeDispatchHelper, template: str):
        self.helper = helper
        self.hash = MacroTemplate.hash_source(template)
        self.template: jinja2.Template = Jinja.from_string(template)

    def render(self, context: Optional[dict] = None) -> str:
        if context is None:
            context = self.create_template_context()
        try:
            return str(self.template.render(context))
        except Exception as e:
            msg = "Error evaluating macro: %s" % (traceback.format_exception_only(type(e), e)[-1])
            logging.exception(msg)
            raise CommandError(msg)  # todo ensure this goes trough the chain and has stack trace added

    def run_gcode_from_command(self, context: Optional[dict] = None):
        self.helper.run_script_atomic(self.render(context))

    def create_template_context(self, eventtime=None) -> dict[Union[RequiredMacroContextKeys, str], Any]:
        return self.helper.create_template_context(eventtime)
