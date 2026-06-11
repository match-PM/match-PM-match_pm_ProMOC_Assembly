#!/usr/bin/env python3
"""Print or execute reproducible reduced camera smoke paths."""

from __future__ import annotations

import argparse
import subprocess
import sys


SMOKE_PATHS = {
    "sim": [
        "ros2 launch promoc_bringup camera.launch.py runtime_mode:=sim",
        "ros2 topic list | grep /promoc/camera/image_raw",
        "ros2 topic echo /promoc/camera/image_raw --once",
        "ros2 topic echo /promoc/camera/status --once",
    ],
    "hardware": [
        "make doctor-hw",
        "ros2 launch promoc_bringup camera.launch.py runtime_mode:=hardware",
        "ros2 topic list | grep /promoc/camera/image_raw",
        "ros2 topic echo /promoc/camera/image_raw --once",
        "ros2 topic echo /promoc/camera/status --once",
    ],
}


def _run_commands(commands: list[str]) -> int:
    for index, command in enumerate(commands, start=1):
        print(f"[{index}/{len(commands)}] {command}")
        result = subprocess.run(command, shell=True, check=False)
        if result.returncode != 0:
            print(f"Command failed with exit code {result.returncode}.")
            return result.returncode
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CS runtime smoke path helper.")
    parser.add_argument(
        "--mode",
        choices=["sim", "hardware", "all"],
        default="all",
        help="Which smoke path to print or execute.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute commands instead of printing them.",
    )
    args = parser.parse_args(argv)

    modes = [args.mode] if args.mode in SMOKE_PATHS else ["sim", "hardware"]

    for mode in modes:
        commands = SMOKE_PATHS[mode]
        print(f"\nCS runtime smoke path: {mode}")
        if args.execute:
            rc = _run_commands(commands)
            if rc != 0:
                return rc
        else:
            for command in commands:
                print(command)

    return 0


if __name__ == "__main__":
    sys.exit(main())
