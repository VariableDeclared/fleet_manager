from .base import LinuxDistro

class UbuntuManager(LinuxDistro):
    def get_update_command(self) -> str:
        return "sudo apt-get update"

    def get_upgrade_command(self) -> str:
        return "sudo apt-get dist-upgrade -y"

    def get_kernel_version(self) -> str:
        return "uname -r"

    def get_check_updates_command(self) -> str:
        return "sudo apt-get update > /dev/null && apt-get -s upgrade | grep ^Inst || true"
