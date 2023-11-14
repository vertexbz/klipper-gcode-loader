from __future__ import annotations
from typing import Iterable
import os
from .file import GCodeFile
from ..virtual_sdcard import VALID_GCODE_EXTS


class GCodeLocator:
    def __init__(self, basedir: str):
        self.basedir = basedir

    def get_file_list(self, check_subdirs: bool = False) -> Iterable[GCodeFile]:
        if check_subdirs:
            flist = []
            for root, dirs, files in os.walk(self.basedir, followlinks=True):
                base = os.path.relpath(root, self.basedir)
                for name in files:
                    if name[name.rfind('.') + 1:] not in VALID_GCODE_EXTS:
                        continue

                    flist.append(GCodeFile(self.basedir, os.path.join(base, name).lstrip('.\\/')))
            return sorted(flist, key=lambda f: f.name.lower())
        else:
            flist = []
            for name in sorted(os.listdir(self.basedir), key=str.lower):
                if name.startswith('.'):
                    continue
                if name[name.rfind('.') + 1:] not in VALID_GCODE_EXTS:
                    continue
                if not os.path.isfile((os.path.join(self.basedir, name))):
                    continue
                flist.append(GCodeFile(self.basedir, name))
            return flist

    def load_file(self, filename: str, check_subdirs: bool = False) -> GCodeFile:
        filename = filename.strip().lstrip('.\\/')

        if check_subdirs or '/' not in filename:
            if os.path.exists(os.path.join(self.basedir, filename)):
                return GCodeFile(self.basedir, filename)

        files = self.get_file_list(check_subdirs)
        for file in files:
            if file.name == filename:
                return file

        filename = filename.lower()
        for file in files:
            if file.name.lower() == filename:
                return file

        raise FileNotFoundError(f'File: \'{filename}\' not found')
