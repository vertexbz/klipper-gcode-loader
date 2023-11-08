from __future__ import annotations
import jinja2
import logging
import traceback
from typing import Any
from typing import Union
from typing import TYPE_CHECKING
from configfile import error as ConfigError
from ..interfaces.macro import PrinterGCodeMacroInterface
from ..interfaces.macro import RequiredMacroContextKeys
from .template import MacroTemplate

if TYPE_CHECKING:
    from ..dispatch import GCodeDispatchHelper


class PrinterMacro(PrinterGCodeMacroInterface):
    def __init__(self, helper: GCodeDispatchHelper):
        self.helper = helper
        self.jinja = jinja2.Environment('{%', '%}', '{', '}')

    def load_template(self, config, option, default=None) -> MacroTemplate:
        name = "%s:%s" % (config.get_name(), option)
        if default is None:
            script = config.get(option)
        else:
            script = config.get(option, default)
        try:
            return MacroTemplate(self.helper, script)
        except Exception as e:
            msg = "Error loading template '%s': %s" % (name, traceback.format_exception_only(type(e), e)[-1])
            logging.exception(msg)
            raise ConfigError(msg)

    def create_template_context(self, eventtime=None) -> dict[Union[RequiredMacroContextKeys, str], Any]:
        return self.helper.create_template_context(eventtime)
