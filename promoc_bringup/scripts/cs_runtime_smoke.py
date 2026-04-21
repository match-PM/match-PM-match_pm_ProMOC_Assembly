#!/usr/bin/env python3
"""Print or execute reproducible CS runtime smoke paths."""

from __future__ import annotations

import argparse
import subprocess
import sys


SMOKE_PATHS = {
    "sim": [
        "ros2 launch promoc_bringup system.launch.py runtime_mode:=sim",
        'ros2 service call /promoc/camera/autofocus promoc_assembly_interfaces/srv/AutoFocus "{start_position: 260.0, end_position: 290.0, focus_mode: 0, skip_flyover: false}"',
        'ros2 service call /promoc/camera/set_exposure promoc_assembly_interfaces/srv/SetExposure "{exposure_time: 12000.0}"',
    ],
    "hardware": [
        "make doctor-hw",
        "ros2 launch promoc_bringup system.launch.py runtime_mode:=hardware",
        'ros2 service call /promoc/mover/activate_xbots promoc_assembly_interfaces/srv/ActivateXbots "{activation_status: true}"',
        'ros2 service call /promoc/camera/set_exposure promoc_assembly_interfaces/srv/SetExposure "{exposure_time: 12000.0}"',
        'ros2 service call /promoc/camera/autofocus promoc_assembly_interfaces/srv/AutoFocus "{start_position: 260.0, end_position: 290.0, focus_mode: 0, skip_flyover: false}"',
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
