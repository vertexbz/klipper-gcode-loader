# GCode files support (print files directly from a host g-code file)
#
# Copyright (C) 2023  Adam Makświej <vertexbz@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
from __future__ import annotations
import re
from typing import TYPE_CHECKING
from typing import Optional
import logging
import os
from gcode import CommandError
from .mock.printer_config import PrinterConfig
from .interfaces.loader import VirtualSDCardInterface
from .iterator import full_file_iterator
from .iterator import full_virtual_file_iterator
from .iterator import WithVirtualFileIterator
from .locator import GCodeLocator
from .macro import Macro
from .macro import PrinterMacro
from .macro import VariableMode
from .dispatch import GCodeDispatchHelper

if TYPE_CHECKING:
    from gcode import GCodeCommand
    from configfile import ConfigWrapper
    from klippy import Printer
    from reactor import Reactor
    from gcode import GCodeDispatch
    from extras.print_stats import PrintStats
    from extras.gcode_macro import TemplateWrapper
    from webhooks import WebRequest
    from .file import GCodeFile
    from .iterator import GCodeFileIterator


class GCodeLoader(VirtualSDCardInterface):
    current_file: Optional[GCodeFileIterator]
    print_stats: PrintStats
    reactor: Reactor
    must_pause_work: bool
    cmd_from_sd: bool
    gcode: GCodeDispatch
    on_error_gcode: TemplateWrapper
    uninterrupted: set[str]

    def __init__(self, helper: GCodeDispatchHelper, config: ConfigWrapper):
        self.helper = helper
        self.uninterrupted = set(map(lambda m: m.upper(), config.getlist('uninterrupted', default=[])))
        self.current_file = None

        # Klipper setup
        self.helper.printer.register_event_handler("klippy:shutdown", self._handle_shutdown)

        # Print Stat Tracking
        self.print_stats = self.helper.printer.load_object(config, 'print_stats')

        # Work timer
        self.reactor = self.helper.printer.get_reactor()
        self.must_pause_work = False
        self.cmd_from_sd = False
        self.work_timer = None

        # Error handling
        gcode_macro = self.helper.printer.load_object(config, 'gcode_macro')
        self.on_error_gcode = gcode_macro.load_template(config, 'on_error_gcode', '')

        # Register commands
        self.gcode = self.helper.printer.lookup_object('gcode')

        for cmd in ['M20', 'M21', 'M23', 'M24', 'M25', 'M26', 'M27']:
            self.gcode.register_command(cmd, getattr(self, 'cmd_' + cmd))

        for cmd in ['M28', 'M29', 'M30']:
            self.gcode.register_command(cmd, self._cmd_error)

        self.gcode.register_command("SDCARD_RESET_FILE", self.cmd_SDCARD_RESET_FILE,
                                    desc=self.cmd_SDCARD_RESET_FILE_help)
        self.gcode.register_command("SDCARD_PRINT_FILE", self.cmd_SDCARD_PRINT_FILE,
                                    desc=self.cmd_SDCARD_PRINT_FILE_help)
        self.gcode.register_command('MACRO_RELOAD', self.cmd_MACRO_RELOAD,
                                    desc="Reloads macros from config files")
        self.gcode.register_command('PRINT_FROM_MACRO', self.cmd_PRINT_FROM_MACRO,
                                    desc="Runs macro as a print")

    def stats(self, _):
        if self.work_timer is None:
            return False, ""
        if self.current_file is None:
            return True, "sd_pos=0"
        return True, "sd_pos=%d" % (self.current_file.pos,)

    def get_file_list(self, check_subdirs: bool = False):
        try:
            return [(f.name, f.size) for f in self.helper.locator.get_file_list(check_subdirs)]
        except:
            logging.exception("gcode_loader get_file_list")
            raise CommandError("Unable to get file list")

    # G-Code commands
    def _cmd_error(self, gcmd: GCodeCommand):
        raise CommandError("write not supported")

    cmd_SDCARD_RESET_FILE_help = "Clears a loaded SD File. Stops the print if necessary"

    def cmd_SDCARD_RESET_FILE(self, _: GCodeCommand):
        if self.cmd_from_sd:
            raise CommandError("SDCARD_RESET_FILE cannot be run from the sdcard")
        self._reset_file()

    cmd_SDCARD_PRINT_FILE_help = "Loads a SD file and starts the print. May include files in subdirectories."

    def cmd_SDCARD_PRINT_FILE(self, gcmd: GCodeCommand):
        if self.work_timer is not None:
            raise CommandError("Printer busy")
        self._reset_file()
        filename = gcmd.get("FILENAME")
        self._load_file(filename, check_subdirs=True)
        self.do_resume()

    def cmd_M20(self, gcmd: GCodeCommand):
        # List SD card
        files = self.get_file_list()
        gcmd.respond_raw("Begin file list")
        for name, size in files:
            gcmd.respond_raw("%s %d" % (name, size))
        gcmd.respond_raw("End file list")

    def cmd_M21(self, gcmd: GCodeCommand):
        # Initialize SD card
        gcmd.respond_raw("SD card ok")

    def cmd_M23(self, gcmd: GCodeCommand):
        # Select SD file
        if self.work_timer is not None:
            raise CommandError("Printer busy")
        self._reset_file()
        filename = gcmd.get_raw_command_parameters().strip()
        self._load_file(filename)

    def cmd_M24(self, _: GCodeCommand):
        # Start/resume SD print
        self.do_resume()

    def cmd_M25(self, _: GCodeCommand):
        # Pause SD print
        self.do_pause()

    def cmd_M26(self, gcmd: GCodeCommand):
        # Set SD position
        if self.work_timer is not None:
            raise CommandError("Printer busy")

        if self.current_file is None:
            raise CommandError("no file loaded")

        pos = gcmd.get_int('S', minval=0)
        self.current_file.seek(pos)

    def cmd_M27(self, gcmd: GCodeCommand):
        # Report SD print status
        if self.current_file is None:
            gcmd.respond_raw("Not SD printing.")
            return
        gcmd.respond_raw("SD printing byte %d/%d" % (self.current_file.pos, self.current_file.size))

    def cmd_MACRO_RELOAD(self, gcmd: GCodeCommand):
        name_filter = gcmd.get('NAME', None)
        if name_filter:
            name_filter = name_filter.upper()
        vars_mode = gcmd.get_int('VARIABLES', 1)

        config = PrinterConfig(self.helper.printer).read_main_config()
        config = {s.get_name().split()[1].upper(): s for s in config.get_prefix_sections('gcode_macro ')}

        for name, macro_config in config.items():
            name = macro_config.get_name().split()[1].upper()
            if name_filter is not None and name != name_filter:
                continue

            if self.helper.has_macro(name):
                self.helper.get_macro(name).update_config(macro_config, VariableMode(vars_mode), verbose=True)
            else:
                self.helper.load_macro(macro_config, verbose=True)

        for name in self.helper.get_macros():
            if name_filter is not None and name != name_filter:
                continue

            if name not in config:
                self.helper.remove_macro(name, verbose=True)

        self.helper.respond_info("Reload complete")

    strip_macro_param = re.compile(r'^\s*MACRO\s*=\s*', re.IGNORECASE)

    def cmd_PRINT_FROM_MACRO(self, gcmd: GCodeCommand):
        if self.work_timer is not None:
            raise CommandError("Printer busy")
        self._reset_file()
        self._load_macro(self.strip_macro_param.sub('', gcmd.get_raw_command_parameters()))
        self.do_resume()

    def get_file_position(self):
        return self.current_file.pos if self.current_file else 0

    def set_file_position(self, pos):
        if self.current_file is None:
            return
        self.current_file.seek(pos)

    def is_cmd_from_sd(self):
        return self.cmd_from_sd

    def get_status(self, _):
        return {
            'file_path': self.file_path(),
            'progress': self.progress(),
            'is_active': self.is_active(),
            'is_virtual': isinstance(self.current_file, WithVirtualFileIterator),
            'file_position': self.current_file.pos if self.current_file else 0,
            'file_size': self.current_file.size if self.current_file else 0,
        }

    def file_path(self):
        if self.current_file:
            return self.current_file.name
        return None

    def progress(self):
        if self.current_file and self.current_file.size > 0:
            return float(self.current_file.pos) / self.current_file.size
        else:
            return 0.

    def is_active(self):
        return self.work_timer is not None

    def do_pause(self):
        if self.work_timer is not None:
            self.must_pause_work = True
            while self.work_timer is not None and not self.cmd_from_sd:
                self.reactor.pause(self.reactor.monotonic() + .001)

    def do_resume(self):
        if self.work_timer is not None:
            raise CommandError("Printer busy")
        self.must_pause_work = False
        self.work_timer = self.reactor.register_timer(self._work_handler, self.reactor.NOW)

    def do_cancel(self):
        if self.current_file is not None:
            self.do_pause()
            self.current_file.close()
            self.current_file = None
            self.print_stats.note_cancel()

    def handle_webhook_script(self, web_request: WebRequest):
        self.helper.run_script(web_request.get_str('script'))

    def _load_file(self, filename: str, check_subdirs=False):
        try:
            self.current_file = full_file_iterator(
                self.helper.locator.load_file(filename, check_subdirs),
                self.helper,
                uninterrupted_macros=self.uninterrupted
            )
            self.helper.respond_raw(f"File opened: {self.current_file.name} Size: {self.current_file.size}")
            self.helper.respond_raw("File selected")
            self.print_stats.set_current_file(filename)
        except:
            logging.exception("gcode_loader file open")
            raise FileNotFoundError("Unable to open file")

    def _load_macro(self, line: str):
        cmd = line.split(maxsplit=1)[0]
        try:
            self.current_file = full_virtual_file_iterator(
                line,
                self.helper,
                uninterrupted_macros=self.uninterrupted,
                name=cmd,
            )
            self.helper.respond_raw(f"File opened: {self.current_file.name} Size: {self.current_file.size}")
            self.helper.respond_raw("File selected")
            self.print_stats.set_current_file(cmd)
        except:
            logging.exception("gcode_loader file open")
            raise FileNotFoundError("Unable to open file")

    def _reset_file(self):
        if self.current_file is not None:
            self.do_pause()
            self.current_file.close()
            self.current_file = None
        self.print_stats.reset()
        self.helper.printer.send_event("virtual_sdcard:reset_file")

    def _handle_shutdown(self):
        if self.work_timer is not None:
            self.must_pause_work = True
            try:
                message = f'Virtual sdcard\nCurrent: {repr(self.current_file.current())}'
                for _ in range(3):
                    message += f'\nUpcoming: {repr(next(self.current_file))}'
                logging.info(message)
            except:
                logging.exception("gcode_loader shutdown read")

    def _work_handler(self, _):
        logging.info("Starting SD card print (position %d)", self.current_file.pos)
        self.reactor.unregister_timer(self.work_timer)
        self.print_stats.note_start()

        gcode_mutex = self.gcode.get_mutex()
        error_message = None
        last_line = None
        while not self.must_pause_work:
            try:
                if last_line is not None:
                    line = last_line
                    last_line = None
                else:
                    line = next(self.current_file)
            except StopIteration:
                # End of file
                self.current_file.close()
                self.current_file = None
                logging.info("Finished SD card print")
                self.helper.respond_raw("Done printing file")
                break
            except CommandError as e:
                error_message = str(e)
                try:
                    self.gcode.run_script(self.on_error_gcode.render())
                except:
                    logging.exception("gcode_loader read on_error")
                break
            except:
                logging.exception("gcode_loader read")
                break

            # Pause if any other request is pending in the gcode class
            if gcode_mutex.test():
                last_line = line
                self.reactor.pause(self.reactor.monotonic() + 0.100)
                continue

            # Dispatch command
            self.cmd_from_sd = True

            try:
                self.helper.run_script_line(line)
            except CommandError as e:
                error_message = str(e)
                try:
                    self.gcode.run_script(self.on_error_gcode.render())
                except:
                    logging.exception("gcode_loader on_error")
                break
            except:
                logging.exception(f'gcode_loader dispatch, stacktrace {repr(line)}')
                break

            self.cmd_from_sd = False

        if self.current_file:
            logging.info("Exiting SD card print (position %d)", self.current_file.pos)
        else:
            logging.info("Exiting SD card print")

        self.work_timer = None
        self.cmd_from_sd = False
        if error_message is not None:
            self.print_stats.note_error(error_message)
        elif self.current_file is not None:
            self.print_stats.note_pause()
        else:
            self.print_stats.note_complete()
        return self.reactor.NEVER


def load_config(config: ConfigWrapper):
    printer: Printer = config.get_printer()

    if printer.lookup_object('virtual_sdcard', None):
        raise config.error('virtual_sdcard already loaded')
    basedir = config.getsection('virtual_sdcard').get('path')

    locator = GCodeLocator(os.path.normpath(os.path.expanduser(basedir)))

    helper = GCodeDispatchHelper(printer, printer.lookup_object('gcode'), locator)

    extension = GCodeLoader(helper, config)

    printer.objects['virtual_sdcard'] = extension

    printer.objects['gcode_macro'] = PrinterMacro(helper)

    for section in config.get_prefix_sections('gcode_macro '):
        helper.load_macro(section)

    webhooks = printer.lookup_object('webhooks')
    webhooks._endpoints["gcode/script"] = extension.handle_webhook_script

    return extension
