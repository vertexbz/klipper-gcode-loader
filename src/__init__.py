# GCode files support (print files directly from a host g-code file)
#
# Copyright (C) 2023  Adam Makświej <vertexbz@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
from __future__ import annotations
from typing import TYPE_CHECKING, Optional
import os, logging, ast

from .loader import GCodeLoader
from .renderer import Renderer

if TYPE_CHECKING:
    from gcode import GCodeCommand
    from configfile import ConfigWrapper
    from klippy import Printer
    from reactor import Reactor
    from gcode import GCodeDispatch
    from extras.print_stats import PrintStats
    from extras.gcode_macro import TemplateWrapper
    from .file import GCodeFile, OpenGcodeFile


class GCodeLoaderKlipper:
    renderer: Renderer
    loader: GCodeLoader
    current_file: Optional[OpenGcodeFile]
    printer: Printer
    print_stats: PrintStats
    reactor: Reactor
    must_pause_work: bool
    cmd_from_sd: bool
    gcode: GCodeDispatch
    on_error_gcode: TemplateWrapper

    def __init__(self, config: ConfigWrapper, basedir: str):
        # Loader setup
        self.renderer = Renderer(
            [section_config.get_name().split()[1] for section_config in config.get_prefix_sections('gcode_macro ')],
            config.get_printer().objects,
            config.getlist('uninterrupted', default=[])
        )
        self.loader = GCodeLoader(self.renderer, os.path.normpath(os.path.expanduser(basedir)))
        self.current_file = None

        # Klipper setup
        self.printer = config.get_printer()
        self.printer.register_event_handler("klippy:shutdown", self._handle_shutdown)

        # Print Stat Tracking
        self.print_stats = self.printer.load_object(config, 'print_stats')

        # Work timer
        self.reactor = self.printer.get_reactor()
        self.must_pause_work = self.cmd_from_sd = False
        self.work_timer = None

        # Error handling
        gcode_macro = self.printer.load_object(config, 'gcode_macro')
        self.on_error_gcode = gcode_macro.load_template(config, 'on_error_gcode', '')

        # Register commands
        self.gcode = self.printer.lookup_object('gcode')

        for cmd in ['M20', 'M21', 'M23', 'M24', 'M25', 'M26', 'M27']:
            self.gcode.register_command(cmd, getattr(self, 'cmd_' + cmd))

        for cmd in ['M28', 'M29', 'M30']:
            self.gcode.register_command(cmd, self._cmd_error)

        self.gcode.register_command("SDCARD_RESET_FILE", self.cmd_SDCARD_RESET_FILE,
                                    desc=self.cmd_SDCARD_RESET_FILE_help)
        self.gcode.register_command("SDCARD_PRINT_FILE", self.cmd_SDCARD_PRINT_FILE,
                                    desc=self.cmd_SDCARD_PRINT_FILE_help)

    def stats(self, _):
        if self.work_timer is None:
            return False, ""
        if self.current_file is None:
            return True, "sd_pos=0"
        return True, "sd_pos=%d" % (self.current_file.pos,)

    def get_file_list(self, check_subdirs: bool = False):
        try:
            return [(file.name, file.size) for file in self.loader.get_file_list(check_subdirs)]
        except:
            logging.exception("virtual_sdcard get_file_list")
            raise self.gcode.error("Unable to get file list")

    # G-Code commands
    def _cmd_error(self, gcmd: GCodeCommand):
        raise gcmd.error("SD write not supported")

    cmd_SDCARD_RESET_FILE_help = "Clears a loaded SD File. Stops the print if necessary"

    def cmd_SDCARD_RESET_FILE(self, gcmd: GCodeCommand):
        if self.cmd_from_sd:
            raise gcmd.error(
                "SDCARD_RESET_FILE cannot be run from the sdcard")
        self._reset_file()

    cmd_SDCARD_PRINT_FILE_help = "Loads a SD file and starts the print. May include files in subdirectories."

    def cmd_SDCARD_PRINT_FILE(self, gcmd: GCodeCommand):
        if self.work_timer is not None:
            raise gcmd.error("SD busy")
        self._reset_file()
        filename = gcmd.get("FILENAME")
        self._load_file(gcmd, filename, check_subdirs=True)
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
            raise gcmd.error("SD busy")
        self._reset_file()
        filename = gcmd.get_raw_command_parameters().strip()
        self._load_file(gcmd, filename)

    def cmd_M24(self, _: GCodeCommand):
        # Start/resume SD print
        self.do_resume()

    def cmd_M25(self, _: GCodeCommand):
        # Pause SD print
        self.do_pause()

    def cmd_M26(self, gcmd: GCodeCommand):
        # Set SD position
        if self.work_timer is not None:
            raise gcmd.error("SD busy")

        if self.current_file is None:
            raise gcmd.error("no file loaded")

        pos = gcmd.get_int('S', minval=0)
        self.current_file.seek(pos)

    def cmd_M27(self, gcmd: GCodeCommand):
        # Report SD print status
        if self.current_file is None:
            gcmd.respond_raw("Not SD printing.")
            return
        gcmd.respond_raw("SD printing byte %d/%d" % (self.current_file.pos, self.current_file.size))

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
            'file_position': self.current_file.pos if self.current_file else 0,
            'file_size': self.current_file.size if self.current_file else 0,
        }

    def file_path(self):
        if self.current_file:
            return self.current_file.name
        return None

    def progress(self):
        if self.current_file:
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
            raise self.gcode.error("SD busy")
        self.must_pause_work = False
        self.work_timer = self.reactor.register_timer(self._work_handler, self.reactor.NOW)

    def do_cancel(self):
        if self.current_file is not None:
            self.do_pause()
            self.current_file.close()
            self.current_file = None
            self.print_stats.note_cancel()

    def _load_file(self, gcmd, filename, check_subdirs=False):
        try:
            self.current_file = self.loader.load_file(filename, check_subdirs)
            gcmd.respond_raw("File opened:%s Size:%d" % (self.current_file.name, self.current_file.size))
            gcmd.respond_raw("File selected")
            self.print_stats.set_current_file(filename)
        except:
            logging.exception("virtual_sdcard file open")
            raise FileNotFoundError("Unable to open file")

    def _reset_file(self):
        if self.current_file is not None:
            self.do_pause()
            self.current_file.close()
            self.current_file = None
        self.print_stats.reset()
        self.printer.send_event("virtual_sdcard:reset_file")

    def _handle_shutdown(self):
        if self.work_timer is not None:
            self.must_pause_work = True
            try:
                message = f'Virtual sdcard\nCurrent: {repr(self.current_file.current())}'
                for _ in range(3):
                    message += f'\nUpcoming: {repr(self.current_file.next())}'
                logging.info(message)
            except:
                logging.exception("virtual_sdcard shutdown read")

    def _work_handler(self, _):
        logging.info("Starting SD card print (position %d)", self.current_file.pos)
        self.reactor.unregister_timer(self.work_timer)
        self.print_stats.note_start()

        gcode_mutex = self.gcode.get_mutex()
        error_message = None
        while not self.must_pause_work:
            try:
                line = self.current_file.next()
            except StopIteration:
                # End of file
                self.current_file.close()
                self.current_file = None
                logging.info("Finished SD card print")
                self.gcode.respond_raw("Done printing file")
                break
            except:
                logging.exception("virtual_sdcard read")
                break

            # Pause if any other request is pending in the gcode class
            if gcode_mutex.test():
                self.current_file.backoff()
                self.reactor.pause(self.reactor.monotonic() + 0.100)
                continue

            # Dispatch command
            self.cmd_from_sd = True

            try:
                self.gcode.run_script(line.data)
            except self.gcode.error as e:
                error_message = f'{str(e)}, stacktrace {repr(line)}'
                try:
                    self.gcode.run_script(self.on_error_gcode.render())
                except:
                    logging.exception("virtual_sdcard on_error")
                break
            except:
                logging.exception(f'virtual_sdcard dispatch, stacktrace {repr(line)}')
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
    loader = GCodeLoaderKlipper(config, basedir)
    printer.objects['virtual_sdcard'] = loader

    return loader
