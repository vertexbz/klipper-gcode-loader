from __future__ import annotations
from typing import TYPE_CHECKING
from ....gcode import GCodeCommand as BaseGCodeCommand

if TYPE_CHECKING:
    from ..line import GCodeLine
    from ..dispatch import GCodeDispatchHelper


class GCodeCommand(BaseGCodeCommand):
    def __init__(self, helper: GCodeDispatchHelper, line: GCodeLine, need_ack: bool):
        super().__init__(helper, line.cmd, line.data, line.params, need_ack)
        self._rawparams = line.rawparams

    def get_raw_command_parameters(self) -> str:
        return self._rawparams

    def get_need_ack(self) -> bool:
        return self._need_ack
