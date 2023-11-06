from __future__ import annotations
import logging
from typing import Any
from typing import TYPE_CHECKING
from typing import Union
from configfile import error as ConfigError
from extras.gcode_macro import GetStatusWrapper
from .interfaces.macro import MacroInterface
from .interfaces.macro import RequiredMacroContextKeys

if TYPE_CHECKING:
    from gcode import GCodeDispatch
    from klippy import Printer

KEY = 'gcode_dispatch_helper'


class GCodeDispatchHelper:
    def __init__(self, printer: Printer, inner: GCodeDispatch):
        self._registry: dict[str: MacroInterface] = {}
        self._inner = inner
        self.printer = printer

    def register_macro(self, name: str, macro: MacroInterface):
        if macro.rename_existing is not None:
            def handle_connect():
                prev_cmd = self._inner.register_command(macro.alias, None)
                if prev_cmd is None:
                    raise ConfigError(f"Existing command '{macro.alias}' not found in gcode_macro rename")
                self._inner.register_command(macro.rename_existing, prev_cmd,
                                             desc=f"Renamed builtin of '{macro.alias}'")
                self._inner.register_command(macro.alias, macro.cmd, desc=macro.cmd_desc)

            self.printer.register_event_handler("klippy:connect", handle_connect)
        else:
            self._inner.register_command(macro.alias, macro.cmd, desc=macro.cmd_desc)

        self._inner.register_mux_command("SET_GCODE_VARIABLE", "MACRO", name, macro.cmd_SET_GCODE_VARIABLE,
                                         desc="Set the value of a G-Code macro variable")
        self._registry[macro.alias] = macro

    def has_macro(self, name: str) -> bool:
        name = name.upper()
        return name in self._registry

    def get_macro(self, name: str) -> MacroInterface:
        name = name.upper()
        if name not in self._registry:
            raise KeyError(f'no macro {name} found')
        return self._registry[name]

    def run_script_atomic(self, script):
        return self._inner.run_script_from_command(script)

    def create_template_context(self, eventtime=None) -> dict[Union[RequiredMacroContextKeys, str], Any]:
        return {
            'printer': GetStatusWrapper(self.printer, eventtime),
            'action_emergency_stop': self._action_emergency_stop,
            'action_respond_info': self._action_respond_info,
            'action_raise_error': self._action_raise_error,
            'action_call_remote_method': self._action_call_remote_method,
        }

    def _action_emergency_stop(self, msg="action_emergency_stop"):
        self.printer.invoke_shutdown(f"Shutdown due to {msg}")
        return ''

    def _action_respond_info(self, msg):
        self.printer.lookup_object('gcode').respond_info(msg)
        return ''

    def _action_raise_error(self, msg):
        raise self.printer.command_error(msg)  # TODO ensure stack is added, configured debug mode

    def _action_call_remote_method(self, method, **kwargs):
        webhooks = self.printer.lookup_object('webhooks')
        try:
            webhooks.call_remote_method(method, **kwargs)
        except self.printer.command_error:
            logging.exception("Remote Call Error")
        return ''


def get_gcode_dispatch(printer: Printer) -> GCodeDispatchHelper:
    if KEY not in printer.objects:
        printer.objects[KEY] = GCodeDispatchHelper(printer, printer.lookup_object('gcode'))

    return printer.lookup_object(KEY)
