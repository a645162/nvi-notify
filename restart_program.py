#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Program restart script
Used to restart the main program after updates
"""

import os
import signal
import subprocess
import sys
import time


def update_dependencies(current_dir: str):
    """
    Update dependencies

    Args:
        current_dir: working directory
    """
    print("Updating dependencies...")

    # Update li-group-center package
    print("Updating li-group-center package...")
    result1 = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-U",
            "li-group-center",
            "-i",
            "https://pypi.python.org/simple",
        ],
        cwd=current_dir,
        capture_output=True,
        text=True,
    )

    if result1.returncode != 0:
        print(f"Failed to update li-group-center: {result1.stderr}")
        return False

    print(f"li-group-center update output: {result1.stdout}")

    # Update all packages from requirements.txt
    print("Updating requirements from requirements.txt...")
    result2 = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-U", "-r", "requirements.txt"],
        cwd=current_dir,
        capture_output=True,
        text=True,
    )

    if result2.returncode != 0:
        print(f"Failed to update requirements: {result2.stderr}")
        return False

    print(f"Requirements update output: {result2.stdout}")
    print("Dependencies updated successfully")
    return True


def restart_program(
    current_pid: int, python_executable: str, script_path: str, current_dir: str
):
    """
    Restart program function

    Args:
        current_pid: current process PID
        python_executable: Python interpreter path
        script_path: main program script path
        current_dir: working directory
    """
    print(f"Current process PID: {current_pid}")

    # Wait a short time to ensure Flask response is sent
    print("Waiting for response to be sent...")
    time.sleep(2)

    # Update dependencies
    if not update_dependencies(current_dir):
        print("Dependency update failed, proceeding with restart anyway...")

    # Start new process
    print("Starting new process...")
    new_process = subprocess.Popen([python_executable, script_path], cwd=current_dir)
    print(f"New process PID: {new_process.pid}")

    # Wait for new process to fully start
    print("Waiting for new process to start...")
    time.sleep(5)

    # Kill old process
    print(f"Killing old process {current_pid}")
    try:
        os.kill(current_pid, signal.SIGTERM)
        print("Restart completed")
    except ProcessLookupError:
        print("Process already terminated")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(
            "Usage: python restart_program.py <current_pid> <python_executable> <script_path> <current_dir>"
        )
        sys.exit(1)

    current_pid = int(sys.argv[1])
    python_executable = sys.argv[2]
    script_path = sys.argv[3]
    current_dir = sys.argv[4]

    restart_program(current_pid, python_executable, script_path, current_dir)
