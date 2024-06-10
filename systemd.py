# -*- coding: utf-8 -*-

import argparse
import os
import time

from config.settings import check_sudo_permission
from utils.utils import do_command

path_current_py = os.path.realpath(__file__)
path_base = os.path.dirname(path_current_py)

service_name = "nvinotify"

target_service_path = "/etc/systemd/system/{}.service".format(service_name)

length_spilt_line = 40

systemd_template = (
    """
[Unit]
Description=NVIDIA GPU Webhook Notify
After=syslog.target

[Service]
ExecStart={}
Restart=on-failure
RestartSec=60s
ExecStop=/bin/kill -2 $MAINPID
KillMode=control-group
TimeoutStopSec=300

[Install]
WantedBy=multi-user.target
    """.strip()
    + "\n"
)

spilt_line = "=" * length_spilt_line

bash_template = (
    """
#!/bin/bash
echo "{}"
date
cd "{}" || exit
{} \\
"{}"
    """.strip()
    + "\n"
)


def install(auto_start: bool = False):
    # Check

    ret = do_command("which nvifan")
    if ret[0] != 0:
        print('"nvifan" is not available')
        exit(1)

    ret = do_command("which python")
    if ret[0] != 0:
        print('"python" is not available???')
        print("R u kidding me?")
        exit(1)

    path_python = ret[1].strip()
    print("Python Path:", path_python)

    print("Target path:", target_service_path)

    service_file_content = systemd_template

    # Modify ExecStart Path
    exec_start_path = os.path.join(path_base, "main.py")

    script_path = os.path.join(path_base, "systemd.sh")
    script_content = bash_template.format(
        spilt_line, path_base, path_python, exec_start_path
    )
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    service_file_content = service_file_content.format('bash "{}"'.format(script_path))

    # Write To Service
    with open(target_service_path, "w") as f:
        f.write(service_file_content)

    if auto_start:
        # daemon-reload
        command = "sudo systemctl daemon-reload"
        print("Command:", command)
        os.system(command)

        # Enable
        command = "sudo systemctl enable {}".format(service_name)
        print("Command:", command)
        os.system(command)

        # Start
        command = "sudo systemctl enable {}".format(service_name)
        print("Command:", command)
        os.system(command)


def uninstall():
    if not os.path.exists(target_service_path):
        print("Service file not found.")
        exit(1)

    # Stop
    print("Stop and disable service...")
    command = "sudo systemctl stop {}".format(service_name)
    print("Command:", command)
    os.system(command)

    # Kill
    time.sleep(5)
    command = "sudo systemctl kill {}".format(service_name)
    print("Command:", command)
    os.system(command)

    # Disable Service
    command = "sudo systemctl disable {}".format(service_name)
    print("Command:", command)
    os.system(command)

    print("Target path:", target_service_path)
    # Remove
    if os.path.exists(target_service_path):
        command = "sudo rm -f " + target_service_path
        print("Command:", command)
        os.system(command)


def print_info():
    print("=" * length_spilt_line)
    print("NVIDIA GPU Webhook Notify")
    print("Systemd Service Installer for Linux")
    print("=" * length_spilt_line)


def main():
    print("Program directory path:", path_base)

    parser = argparse.ArgumentParser(
        description="nvidia-smi-webhook-notify systemd service manager",
    )

    parser.add_argument("-i", "--install", help="Install service", action="store_true")
    parser.add_argument(
        "-r",
        "--remove",
        "-u",
        "--uninstall",
        help="Remove service",
        action="store_true",
    )

    args = parser.parse_args()

    if hasattr(args, "install") and args.install:
        print("Try to Install...")
        install(auto_start=True)
    elif (hasattr(args, "uninstall") and args.uninstall) or (
        hasattr(args, "remove") and args.remove
    ):
        print("Try to Uninstall...")
        uninstall()
    else:
        parser.print_help()


if __name__ == "__main__":
    print_info()
    if not check_sudo_permission():
        print("Please run this program as root(Using 'sudo').")
        exit(-1)

    main()
