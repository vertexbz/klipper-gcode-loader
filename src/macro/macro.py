from __future__ import annotations
from enum import Enum
from typing import Optional
from typing import TYPE_CHECKING, Any
from jinja2.exceptions import TemplateError
from configfile import ConfigWrapper
from configfile import error as ConfigError
from gcode import CommandError
from .utils import is_classic_gcode
from .utils import load_variables
from .utils import parse_value
from ..interfaces.macro import MacroInterface

if TYPE_CHECKING:
    from gcode import GCodeCommand
    from ..dispatch import GCodeDispatchHelper
    from .template import MacroTemplate
    from .printer_macro import PrinterMacro


class VariableMode(Enum):
    SKIP = 0
    MERGE = 1
    REPLACE = 2


class Macro(MacroInterface):
    helper: GCodeDispatchHelper
    name: str
    alias: str
    template: MacroTemplate
    rename_existing: Optional[str]
    cmd_desc: str
    variables: dict[str, Any]
    in_script: bool

    def __init__(self, helper: GCodeDispatchHelper, config: ConfigWrapper, printer_macro: PrinterMacro):
        name: str = config.get_name().split(maxsplit=1)[1]
        if ' ' in name:
            raise ConfigError(f"Name of section '{name}' contains illegal whitespace")

        self.helper = helper
        self.name = name
        self.alias = name.upper()
        self.template = printer_macro.load_template(config, 'gcode', name=self.alias)
        self.rename_existing = config.get("rename_existing", None)
        self.cmd_desc = config.get("description", "G-Code macro")
        self.variables = load_variables(config)
        self.in_script = False

        if self.rename_existing is not None and is_classic_gcode(self.alias) != is_classic_gcode(self.rename_existing):
            raise ConfigError(f"G-Code macro rename of different types ('{self.alias}' vs '{self.rename_existing}')")

    def render(self, params: dict, rawparams: str) -> str:
        kwparams = dict(self.variables)
        kwparams.update(self.helper.create_template_context())
        kwparams['params'] = params
        kwparams['rawparams'] = rawparams
        return self.template.render(kwparams)

    def execute(self, params: dict, rawparams: str):
        self.in_script = True
        try:
            self.helper.run_script_from_command(self.render(params, rawparams), name=self.alias)
        finally:
            self.in_script = False

    def update_variable(self, name: str, value: Any):
        v = dict(self.variables)
        v[name] = value
        self.variables = v

    def cmd(self, gcmd: GCodeCommand):
        if self.in_script:
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

    def update_config(self, macro_config: ConfigWrapper, vars_mode: VariableMode, verbose: bool = False) -> bool:
        rename_existing: Optional[str] = macro_config.get("rename_existing", None)
        if self.rename_existing is None and rename_existing is not None:
            # this shouldn't happen
            if verbose:
                self.helper.respond_info(f"Warning: {self.alias}:rename_existing added to config, not updating!")
            return False

        if self.rename_existing is not None and rename_existing is None:
            # this shouldn't happen
            if verbose:
                self.helper.respond_info(f"Warning: {self.alias}:rename_existing removed from config, not updating!")
            return False

        try:
            new_template = self.helper.gcode_macro.load_template(macro_config, 'gcode')
        except (TemplateError, ConfigError) as e:
            if verbose:
                self.helper.respond_info(f'Skipped {self.alias} - template error: {e}')
            return False

        changed_code = False
        if new_template.hash != self.template.hash:
            self.template = new_template
            changed_code = True

        changed_vars = False
        if vars_mode == VariableMode.MERGE:
            new_vars = load_variables(macro_config)
            new_vars.update(self.variables)
            if self.variables != new_vars:
                self.variables = new_vars
                changed_vars = True
        if vars_mode == VariableMode.REPLACE:
            new_vars = load_variables(macro_config)
            if self.variables != new_vars:
                self.variables = new_vars
                changed_vars = True

        changed_orig = False
        if self.rename_existing is not None and rename_existing is not None:
            if self.helper.rename_command(self.rename_existing, rename_existing, renaming_existing=True):
                self.rename_existing = rename_existing
                changed_orig = True

        changed_desc = False
        new_desc = macro_config.get("description", "G-Code macro")
        if self.cmd_desc != new_desc:
            self.helper.set_macro_description(self.alias, new_desc)
            self.cmd_desc = new_desc
            changed_desc = True

        updated = changed_code or changed_vars or changed_orig or changed_desc

        if updated and verbose:
            changes = ", ".join(filter(lambda s: s is not None, [
                'code' if changed_code else None,
                'vars' if changed_vars else None,
                'orig' if changed_orig else None,
                'desc' if changed_desc else None,
            ]))
            self.helper.respond_info(f"Updated {self.alias}'s {changes}")
        return updated
