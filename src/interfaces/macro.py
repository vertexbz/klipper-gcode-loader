from __future__ import annotations
from abc import abstractmethod
from typing import TYPE_CHECKING, Optional, Any, Union

if TYPE_CHECKING:
    from gcode import GCodeCommand

RequiredMacroContextKeys = Union[
    'printer', 'action_emergency_stop', 'action_respond_info', 'action_raise_error', 'action_call_remote_method']


class PrinterGCodeMacroInterface:
    @abstractmethod
    def load_template(self, config, option, default=None) -> MacroTemplateInterface:
        pass

    @abstractmethod
    def create_template_context(self, eventtime=None) -> dict[Union[RequiredMacroContextKeys, str], Any]:
        pass


class MacroTemplateInterface:
    @abstractmethod
    def render(self, context: Optional[dict] = None) -> str:
        pass

    @abstractmethod
    def run_gcode_from_command(self, context: Optional[dict] = None):
        pass

    @abstractmethod
    def create_template_context(self, eventtime=None) -> dict[Union[RequiredMacroContextKeys, str], Any]:
        pass


class MacroInterface:
    @abstractmethod
    def __init__(self):
        self.alias: str = ''
        self.template: MacroTemplateInterface = MacroTemplateInterface()
        self.rename_existing: Optional[str] = None
        self.cmd_desc: str = ''
        self.variables: dict[str, Any] = {}

    @abstractmethod
    def cmd(self, gcmd: GCodeCommand):
        pass

    @abstractmethod
    def cmd_SET_GCODE_VARIABLE(self, gcmd: GCodeCommand):
        pass

    def get_status(self, *_):
        return self.variables
