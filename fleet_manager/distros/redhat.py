from .base import LinuxDistro

class RedHatManager(LinuxDistro):
    def get_update_command(self) -> str:
        return "sudo dnf check-update || true"

    def get_upgrade_command(self) -> str:
        return "sudo dnf upgrade -y"

    def get_kernel_version(self) -> str:
        return "uname -r"

    def get_check_updates_command(self) -> str:
        return "sudo dnf -q check-update || true"
