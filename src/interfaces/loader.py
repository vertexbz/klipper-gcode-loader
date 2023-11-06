from __future__ import annotations
from abc import abstractmethod


class VirtualSDCardInterface:
    @abstractmethod
    def get_file_position(self) -> int:
        pass

    @abstractmethod
    def set_file_position(self, pos: int):
        pass

    @abstractmethod
    def is_cmd_from_sd(self) -> int:
        pass

    @abstractmethod
    def do_pause(self) -> None:
        pass

    @abstractmethod
    def do_resume(self) -> None:
        pass

    @abstractmethod
    def do_cancel(self) -> None:
        pass

    @abstractmethod
    def is_active(self) -> bool:
        pass

    @abstractmethod
    def get_file_list(self, check_subdirs=False) -> tuple[str, int]:  # name, size
        pass
