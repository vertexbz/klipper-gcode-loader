from __future__ import annotations
import configfile
from .printer import Printer


class PrinterConfig(configfile.PrinterConfig):
    def __init__(self, printer):
        super().__init__(Printer())
        self.printer = printer
