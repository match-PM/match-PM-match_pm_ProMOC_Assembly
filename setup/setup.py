#!/usr/bin/env python3
"""One small setup helper for ProMOC development machines.

This script is intentionally a convenience tool. The canonical build path is
still the normal ROS workspace flow documented in the repository README.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import shlex
import subprocess
import sys


SETUP_DIR = Path(__file__).resolve().parent
REPO_ROOT = SETUP_DIR.parent
WORKSPACE_ROOT = REPO_ROOT.parent.parent
DEFAULT_CAMERA_WS = Path.home() / "ros2_ws"
DEFAULT_VENV = Path.home() / "ros2_promoc_venv"
CAMERA_ARAVIS2_REPO = "https://github.com/FraunhoferIOSB/camera_aravis2.git"

SYSTEM_PACKAGES = [
    "aspnetcore-runtime-8.0",
    "aravis-tools",
    "build-essential",
    "clang",
    "cmake",
    "dotnet-sdk-8.0",
    "gir1.2-aravis-0.8",
    "git",
    "libaravis-dev",
    "libglib2.0-dev",
    "libgstreamer-plugins-base1.0-dev",
    "libgstreamer1.0-dev",
    "libopencv-dev",
    "mono-complete",
    "mono-devel",
    "pkg-config",
    "python3-colcon-common-extensions",
    "python3-dev",
    "python3-full",
    "python3-opencv",
    "python3-pip",
    "python3-venv",
    "zlib1g",
]

PYTHON_PACKAGES = [
    "pip --upgrade",
    "wheel",
    "numpy",
    "pyserial",
    "pyusb",
    "pythonnet",
    "llvmlite==0.42.0",
    "numba==0.59.1",
    "coverage<7.4",
    "pylablib>=1.4.0",
]


@dataclass
class Result:
    name: str
    ok: bool
    detail: str = ""


def print_header(title: str) -> None:
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)


def run(command: list[str] | str, *, cwd: Path | None = None, dry_run: bool = False) -> int:
    if isinstance(command, list):
        display = " ".join(shlex.quote(part) for part in command)
    else:
        display = command
    if cwd:
        print(f"$ cd {cwd} && {display}")
    else:
        print(f"$ {display}")
    if dry_run:
        return 0
    completed = subprocess.run(command, cwd=cwd, shell=isinstance(command, str), check=False)
    return int(completed.returncode)


def capture(command: list[str] | str) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        shell=isinstance(command, str),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return int(completed.returncode), completed.stdout.strip()


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def python_import(module: str, python: str = sys.executable) -> bool:
    return subprocess.run(
        [python, "-c", f"import {module}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def ros_setup_path() -> Path | None:
    distro = os.environ.get("ROS_DISTRO")
    if distro in {"humble", "jazzy"} and (Path("/opt/ros") / distro / "setup.bash").exists():
        return Path("/opt/ros") / distro / "setup.bash"
    for distro in ("humble", "jazzy"):
        candidate = Path("/opt/ros") / distro / "setup.bash"
        if candidate.exists():
            return candidate
    return None


def ros_shell(command: str, *, workspace: Path | None = None) -> str:
    parts = []
    ros_setup = ros_setup_path()
    if ros_setup:
        parts.append(f"source {ros_setup}")
    if workspace and (workspace / "install/setup.bash").exists():
        parts.append(f"source {workspace / 'install/setup.bash'}")
    parts.append(command)
    return "bash -lc " + repr(" && ".join(parts))


def collect_checks() -> list[Result]:
    results = [
        Result("ROS 2 setup", ros_setup_path() is not None, str(ros_setup_path() or "missing")),
        Result("ros2 command", command_exists("ros2")),
        Result("colcon", command_exists("colcon")),
        Result("rosdep", command_exists("rosdep")),
        Result("dotnet", command_exists("dotnet")),
        Result("mono", command_exists("mono")),
        Result("arv-tool-0.8", command_exists("arv-tool-0.8")),
        Result("pylablib", python_import("pylablib")),
        Result("pythonnet", python_import("pythonnet")),
        Result("pyserial", python_import("serial")),
        Result("dialout group", "dialout" in os.popen("groups").read().split()),
        Result("plugdev group", "plugdev" in os.popen("groups").read().split()),
        Result("IDS udev rules", Path("/etc/udev/rules.d/99-ids-usb-cameras.rules").exists()),
        Result("workspace install", (WORKSPACE_ROOT / "install/setup.bash").exists(), str(WORKSPACE_ROOT)),
        Result(
            "PMCLib vendor folder",
            (REPO_ROOT / "planar_motor_nodes/planar_motor_nodes/drivers/vendor/pmclib").exists(),
            "optional, hardware planar motor only",
        ),
    ]
    tty_ports = sorted(Path("/dev").glob("ttyUSB*")) + sorted(Path("/dev").glob("ttyACM*"))
    results.append(Result("linear-axis serial ports", bool(tty_ports), " ".join(map(str, tty_ports))))
    return results


def command_check(_args: argparse.Namespace) -> int:
    print_header("ProMOC Setup Check")
    missing = 0
    for result in collect_checks():
        mark = "OK" if result.ok else "--"
        print(f"[{mark}] {result.name:<28} {result.detail}")
        if not result.ok and result.name not in {"PMCLib vendor folder", "linear-axis serial ports"}:
            missing += 1
    print()
    print(f"Missing required/recommended checks: {missing}")
    print("Use: python3 setup/setup.py install --all")
    return 0 if missing == 0 else 1


def command_install(args: argparse.Namespace) -> int:
    print_header("ProMOC Install")
    selected = args.all or not any([args.system, args.python, args.rosdep, args.build, args.camera])

    if selected or args.system:
        if run(["sudo", "apt-get", "update"], dry_run=args.dry_run) != 0:
            return 1
        if run(["sudo", "apt-get", "install", "-y", *SYSTEM_PACKAGES], dry_run=args.dry_run) != 0:
            return 1
        install_groups(args.dry_run)
        install_camera_udev(args.dry_run)

    if selected or args.python:
        if install_python_packages(sys.executable, args.dry_run) != 0:
            return 1
        check_dotnet_runtime(args.dry_run)

    if args.camera:
        if install_camera_aravis2(Path(args.camera_ws).expanduser(), args.dry_run) != 0:
            return 1

    if selected or args.rosdep:
        command = ros_shell(f"rosdep update && rosdep install --from-paths {REPO_ROOT} --ignore-src -y")
        run(command, dry_run=args.dry_run)

    if selected or args.build:
        if run(["colcon", "build", "--symlink-install"], cwd=WORKSPACE_ROOT, dry_run=args.dry_run) != 0:
            return 1

    print()
    print("Install step complete. If groups changed, log out and back in.")
    return 0


def install_python_packages(python: str, dry_run: bool) -> int:
    for spec in PYTHON_PACKAGES:
        package_args = spec.split()
        command = [python, "-m", "pip", "install", *package_args]
        if run(command, dry_run=dry_run) != 0:
            return 1
    return 0


def check_dotnet_runtime(dry_run: bool) -> None:
    print()
    print("Checking .NET/pythonnet runtime...")
    if dry_run:
        print("$ dotnet --version")
        print("$ mono --version")
        print("$ python3 -c 'from pythonnet import load; load(\"coreclr\")'")
        return

    dotnet_ok = command_exists("dotnet")
    mono_ok = command_exists("mono")
    print(f"[{'OK' if dotnet_ok else '--'}] dotnet")
    print(f"[{'OK' if mono_ok else '--'}] mono")
    if not dotnet_ok and not mono_ok:
        print("No .NET runtime found; planar PMCLib hardware mode will not work.")
        return

    for runtime_name in ("coreclr", "mono"):
        if runtime_name == "coreclr" and not dotnet_ok:
            continue
        if runtime_name == "mono" and not mono_ok:
            continue
        code = (
            "from pythonnet import load\n"
            f"load({runtime_name!r})\n"
            "import clr\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        print(f"[{'OK' if result.returncode == 0 else '--'}] pythonnet {runtime_name}")


def install_groups(dry_run: bool) -> None:
    user = os.environ.get("USER", "")
    if user:
        run(["sudo", "usermod", "-a", "-G", "dialout", user], dry_run=dry_run)
        run(["sudo", "usermod", "-a", "-G", "plugdev", user], dry_run=dry_run)


def install_camera_udev(dry_run: bool) -> None:
    rule = (
        'SUBSYSTEM=="usb", ATTRS{idVendor}=="1409", MODE="0666", GROUP="plugdev"\\n'
        'SUBSYSTEM=="usb", ATTRS{bDeviceClass}=="ef", ATTRS{bDeviceSubClass}=="02", '
        'MODE="0666", GROUP="plugdev"\\n'
    )
    command = (
        "printf " + repr(rule) +
        " | sudo tee /etc/udev/rules.d/99-ids-usb-cameras.rules >/dev/null"
    )
    run(command, dry_run=dry_run)
    run(["sudo", "udevadm", "control", "--reload-rules"], dry_run=dry_run)
    run(["sudo", "udevadm", "trigger"], dry_run=dry_run)


def install_camera_aravis2(camera_ws: Path, dry_run: bool) -> int:
    src = camera_ws / "src"
    repo_dir = src / "camera_aravis2"
    if not dry_run:
        src.mkdir(parents=True, exist_ok=True)
    if repo_dir.exists():
        if run(["git", "pull"], cwd=repo_dir, dry_run=dry_run) != 0:
            return 1
    else:
        if run(["git", "clone", CAMERA_ARAVIS2_REPO], cwd=src, dry_run=dry_run) != 0:
            return 1
    run(ros_shell("rosdep update", workspace=camera_ws), dry_run=dry_run)
    run(
        ros_shell("rosdep install --from-paths src --ignore-src -y", workspace=camera_ws),
        cwd=camera_ws,
        dry_run=dry_run,
    )
    return run(
        ["colcon", "build", "--packages-select", "camera_aravis2", "--symlink-install"],
        cwd=camera_ws,
        dry_run=dry_run,
    )


def command_validate(args: argparse.Namespace) -> int:
    print_header("ProMOC Validate")
    checks_failed = command_check(args)
    quick = run([sys.executable, str(REPO_ROOT / "tools/check_project.py"), "--quick"], cwd=REPO_ROOT)
    if args.full:
        full = run(
            [
                sys.executable,
                str(REPO_ROOT / "tools/check_project.py"),
                "--full",
                "--workspace-root",
                str(WORKSPACE_ROOT),
            ],
            cwd=REPO_ROOT,
        )
    else:
        full = 0
    return 0 if checks_failed == 0 and quick == 0 and full == 0 else 1


def command_repair(args: argparse.Namespace) -> int:
    print_header("ProMOC Python Repair")
    venv = Path(args.venv).expanduser().resolve()
    if REPO_ROOT in venv.parents or venv in {Path("/"), Path.home(), REPO_ROOT, SETUP_DIR}:
        print(f"Refusing unsafe venv path: {venv}")
        return 1

    if venv.exists() and not args.keep_venv:
        if not args.force:
            answer = input(f"Delete and recreate {venv}? [y/N] ").strip().lower()
            if answer != "y":
                print("Cancelled.")
                return 0
        shutil.rmtree(venv)

    if not venv.exists():
        if run([sys.executable, "-m", "venv", str(venv)]) != 0:
            return 1

    python = str(venv / "bin/python")
    if install_python_packages(python, dry_run=False) != 0:
        return 1
    print()
    print(f"Repair complete. Activate with: source {venv}/bin/activate")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ProMOC setup helper")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="show dependency and workspace status")
    check.set_defaults(func=command_check)

    install = sub.add_parser("install", help="install dependencies and optionally build")
    install.add_argument("--all", action="store_true", help="install system/python/rosdep and build")
    install.add_argument("--system", action="store_true", help="install apt packages and permissions")
    install.add_argument("--python", action="store_true", help="install Python packages")
    install.add_argument("--rosdep", action="store_true", help="run rosdep")
    install.add_argument("--build", action="store_true", help="run colcon build")
    install.add_argument("--camera", action="store_true", help="clone/build camera_aravis2")
    install.add_argument("--camera-ws", default=str(DEFAULT_CAMERA_WS))
    install.add_argument("--dry-run", action="store_true")
    install.set_defaults(func=command_install)

    validate = sub.add_parser("validate", help="run setup check plus project checks")
    validate.add_argument("--full", action="store_true", help="also run tools/check_project.py --full")
    validate.set_defaults(func=command_validate)

    repair = sub.add_parser("repair", help="recreate or refresh the Python venv")
    repair.add_argument("--venv", default=str(DEFAULT_VENV))
    repair.add_argument("--force", action="store_true")
    repair.add_argument("--keep-venv", action="store_true")
    repair.set_defaults(func=command_repair)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
