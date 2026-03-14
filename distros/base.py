from abc import ABC, abstractmethod

class LinuxDistro(ABC):
    @abstractmethod
    def get_update_command(self) -> str:
        pass

    @abstractmethod
    def get_upgrade_command(self) -> str:
        pass

    @abstractmethod
    def get_kernel_version(self) -> str:
        pass

    @abstractmethod
    def get_check_updates_command(self) -> str:
        pass
