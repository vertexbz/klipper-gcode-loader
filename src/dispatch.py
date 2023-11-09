from __future__ import annotations
from functools import cached_property
import logging
from typing import Any
from typing import Optional
from typing import TYPE_CHECKING
from typing import Union
from configfile import ConfigWrapper
from configfile import error as ConfigError
from extras.gcode_macro import GetStatusWrapper
from gcode import CommandError
from .iterator import full_macro_iterator
from .iterator import full_script_iterator
from .mock.gcode_command import GCodeCommand
from .macro import Macro

if TYPE_CHECKING:
    from gcode import GCodeDispatch
    from klippy import Printer
    from .macro import PrinterMacro
    from .line import GCodeLine
    from .interfaces.macro import MacroInterface
    from .interfaces.macro import RequiredMacroContextKeys


class GCodeDispatchHelper:
    def __init__(self, printer: Printer, inner: GCodeDispatch):
        self._registry: dict[str: MacroInterface] = {}
        self._inner = inner
        self.printer = printer

    @cached_property
    def gcode_macro(self) -> PrinterMacro:
        return self.printer.lookup_object('gcode_macro')

    def load_macro(self, macro_config: ConfigWrapper):
        macro = Macro(self, macro_config, self.gcode_macro)
        if macro.rename_existing is not None:
            def handle_connect():
                self.rename_command(macro.alias, macro.rename_existing)
                self._inner.register_command(macro.alias, macro.cmd, desc=macro.cmd_desc)

            self.printer.register_event_handler("klippy:connect", handle_connect)
        else:
            self._inner.register_command(macro.alias, macro.cmd, desc=macro.cmd_desc)

        self._inner.register_mux_command("SET_GCODE_VARIABLE", "MACRO", macro.name, macro.cmd_SET_GCODE_VARIABLE,
                                         desc="Set the value of a G-Code macro variable")

        self.printer.objects[f'gcode_macro {macro.name}'] = macro
        self._registry[macro.alias] = macro

    def remove_macro(self, macro_name: str):
        macro = self.get_macro(macro_name)
        key = f'gcode_macro {macro.name}'

        # remove variable access
        if 'SET_GCODE_VARIABLE' in self._inner.mux_commands:
            del self._inner.mux_commands['SET_GCODE_VARIABLE'][1][macro.name]

        # remove gcode
        if macro.alias in self._inner.ready_gcode_handlers:
            del self._inner.ready_gcode_handlers[macro.alias]
        if macro.alias in self._inner.base_gcode_handlers:
            del self._inner.base_gcode_handlers[macro.alias]
        if macro.alias in self._inner.gcode_help:
            del self._inner.gcode_help[macro.alias]

        if macro.rename_existing is not None:
            self.rename_command(macro.rename_existing, macro.alias)

        # remove from printer configuration
        if key in self.printer.objects:
            del self.printer.objects[key]

        del self._registry[macro_name]

        self.respond_info(f"Removed {macro_name}")

    def rename_command(self, old_name: str, new_name: str, renaming_existing: bool = False) -> bool:
        if old_name == new_name:
            return False

        orig = self._inner.register_command(old_name, None)
        if orig is None:
            raise ConfigError(f"Existing command '{old_name}' not found in gcode_macro rename")
        self._inner.register_command(new_name, orig)

        if old_name in self._inner.gcode_help:
            self.set_macro_description(new_name, self.get_macro_description(old_name))
            self.set_macro_description(old_name, None)
        elif renaming_existing:
            self.set_macro_description(new_name, f"Renamed builtin of '{old_name}'")
        return True

    def get_macro_description(self, name: str) -> Optional[str]:
        if name not in self._inner.gcode_help:
            return None
        return self._inner.gcode_help[name]

    def set_macro_description(self, name: str, desc: Optional[str]):
        if desc is None:
            if name in self._inner.gcode_help:
                del self._inner.gcode_help[name]
        else:
            self._inner.gcode_help[name] = desc

    def has_macro(self, name: str) -> bool:
        name = name.upper()
        return name in self._registry

    def get_macro(self, name: str) -> Macro:
        name = name.upper()
        if name not in self._registry:
            raise KeyError(f'no macro {name} found')
        return self._registry[name]

    def get_macros(self):
        return self._registry.keys()

    def run_script_from_command(self, script: str, name: Optional[str] = None):
        iterator = full_script_iterator(script, self) if name is None else full_macro_iterator(name, script, self)
        try:
            for line in iterator:
                self.run_line(line, False)
        finally:
            iterator.close()

    # top level run
    def run_script_line(self, line: GCodeLine):
        with self._inner.mutex:
            self.run_line(line, False)

    # top level run
    def run_script(self, script: str):
        with self._inner.mutex:
            iterator = full_script_iterator(script, self)
            try:
                for line in iterator:
                    self.run_line(line, False)
            finally:
                iterator.close()

    def run_line(self, line: GCodeLine, need_ack: bool = False):
        gcmd = GCodeCommand(self, line, need_ack)
        handler = self._inner.gcode_handlers.get(gcmd.get_command(), None)
        try:
            if handler is None:
                self._line_cmd_default(line, gcmd)
            else:
                handler(gcmd)
        except CommandError as e:
            self.printer.send_event("gcode:command_error")
            self.respond_info(f'{str(e)}. Backtrace:\n{repr(line)}')
            if not need_ack:
                raise
        except BaseException:
            msg = f'Internal error on command:"{gcmd.get_command()}"'
            logging.exception(msg)
            self.respond_info(f'{msg}. Backtrace:\n{repr(line)}')
            self.printer.invoke_shutdown(msg)
            if not need_ack:
                raise
        gcmd.ack()

    def _line_cmd_default(self, line: GCodeLine, gcmd: GCodeCommand):
        gcmd.respond_info = lambda s: None
        self._inner.cmd_default(gcmd)
        self.respond_info(f'Unknown command: "{gcmd.get_command()}". Backtrace:\n{repr(line)}')

    def create_template_context(self, eventtime=None) -> dict[Union[RequiredMacroContextKeys, str], Any]:
        return {
            'printer': GetStatusWrapper(self.printer, eventtime),
            'action_emergency_stop': self._action_emergency_stop,
            'action_respond_info': self._action_respond_info,
            'action_raise_error': self._action_raise_error,
            'action_call_remote_method': self._action_call_remote_method,
        }

    def respond_info(self, msg: str):
        self._inner.respond_info(msg)

    def respond_raw(self, msg: str):
        self._inner.respond_raw(msg)

    def _action_emergency_stop(self, msg: str = "action_emergency_stop"):
        self.printer.invoke_shutdown(f"Shutdown due to {msg}")
        return ''

    def _action_respond_info(self, msg: str):
        self.respond_info(msg)
        return ''

    def _action_raise_error(self, msg: str):
        raise self.printer.command_error(msg)

    def _action_call_remote_method(self, method, **kwargs):
        webhooks = self.printer.lookup_object('webhooks')
        try:
            webhooks.call_remote_method(method, **kwargs)
        except self.printer.command_error:
            logging.exception("Remote Call Error")
        return ''
