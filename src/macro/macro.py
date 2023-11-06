from __future__ import annotations
from typing import TYPE_CHECKING, Any
from configfile import ConfigWrapper
from configfile import error as ConfigError
from gcode import CommandError
from .utils import is_classic_gcode
from .utils import load_variables
from .utils import parse_value
from ..interfaces.macro import MacroInterface
from ..interfaces.macro import PrinterGCodeMacroInterface

if TYPE_CHECKING:
    from gcode import GCodeCommand
    from ..dispatch import GCodeDispatchHelper


class Macro(MacroInterface):
    def __init__(self, helper: GCodeDispatchHelper, config: ConfigWrapper, printer_macro: PrinterGCodeMacroInterface):
        name: str = config.get_name().split(maxsplit=1)[0]
        if ' ' in name:
            raise ConfigError(f"Name of section '{name}' contains illegal whitespace")

        self.helper = helper
        self.alias = name.upper()
        self.template = printer_macro.load_template(config, 'gcode')
        self.rename_existing = config.get("rename_existing", None)
        self.cmd_desc = config.get("description", "G-Code macro")
        self.variables = load_variables(config)

        if self.rename_existing is not None and is_classic_gcode(self.alias) != is_classic_gcode(self.rename_existing):
            raise ConfigError(f"G-Code macro rename of different types ('{self.alias}' vs '{self.rename_existing}')")

        self.helper.register_macro(name, self)
        self.in_script = False

    def render(self, params: dict, rawparams: str) -> str:
        kwparams = dict(self.variables)
        kwparams.update(self.helper.create_template_context())
        kwparams['params'] = params
        kwparams['rawparams'] = rawparams
        return self.template.render(kwparams)

    def execute(self, params: dict, rawparams: str):
        self.in_script = True
        try:
            self.helper.run_script_atomic(self.render(params, rawparams))
        finally:
            self.in_script = False

    def update_variable(self, name: str, value: Any):
        v = dict(self.variables)
        v[name] = value
        self.variables = v

    def cmd(self, gcmd: GCodeCommand):
        if self.in_script:  # TODO is not checked in iterators
            raise CommandError(f"Macro {self.alias} called recursively")

        self.execute(gcmd.get_command_parameters(), gcmd.get_raw_command_parameters())

    def cmd_SET_GCODE_VARIABLE(self, gcmd: GCodeCommand):
        variable = gcmd.get('VARIABLE')
        value = gcmd.get('VALUE')
        if variable not in self.variables:
            raise CommandError(f"Unknown gcode_macro variable '{variable}'")
        try:
            self.update_variable(variable, parse_value(value))
        except (SyntaxError, TypeError, ValueError) as e:
            raise CommandError(f"Unable to parse '{value}' as a literal: {e}")
