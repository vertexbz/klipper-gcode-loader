from __future__ import annotations
import ast
import json
from typing import Any
from configfile import ConfigWrapper
from configfile import error as ConfigError


def parse_value(value: str):
    literal = ast.literal_eval(value)
    json.dumps(literal, separators=(',', ':'))
    return literal


def load_variables(config: ConfigWrapper) -> dict[str, Any]:
    variables = {}
    prefix = 'variable_'
    for option in config.get_prefix_options(prefix):
        try:
            literal = parse_value(config.get(option))
            variables[option[len(prefix):]] = literal
        except (SyntaxError, TypeError, ValueError) as e:
            raise ConfigError(f"Option '{option}' in section '{config.get_name()}' is not a valid literal: {e}")
    return variables


def is_classic_gcode(cmd: str) -> bool:
    try:
        cmd = cmd.upper()
        _ = float(cmd[1:])
        return cmd[0].isupper() and cmd[1].isdigit()
    except BaseException:
        return False
