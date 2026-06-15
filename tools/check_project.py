#!/usr/bin/env python3
"""Project checks for the ProMOC Assembly repository."""

import argparse
import ast
import os
import shlex
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

import yaml

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_REPOSITORY_ROOT = SCRIPT_PATH.parents[1]
EXTERNAL_GITLINK = Path(
    "planar_motor_nodes/planar_motor_nodes/drivers/match_pm_xBot"
)
WORKSPACE_OUTPUT_DIRS = ("build", "install", "log")
REQUIRED_CONFIGS = (
    "camera_nodes/config/camera.yaml",
    "linear_axis_nodes/config/x_axis.yaml",
    "linear_axis_nodes/config/z_axis.yaml",
    "planar_motor_nodes/config/planar_motor.yaml",
    "promoc_bringup/config/system.yaml",
    "promoc_core/config/system_controller.yaml",
)
STALE_REFERENCE_NEEDLES = (
    "/promoc/camera/autofocus",
    "/promoc/camera/set_exposure",
    "services.autofocus",
    "services.exposure",
    "camera_simulator",
    "pm_genicam_controller",
    "sim_mode",
)
AUTOFOCUS_REFERENCE = "/promoc/camera/" "autofocus"
EXPOSURE_REFERENCE = "/promoc/camera/" "set_exposure"
AUTOFOCUS_SERVICE_REFERENCE = "services." "autofocus"
EXPOSURE_SERVICE_REFERENCE = "services." "exposure"
CAMERA_SIMULATOR_REFERENCE = "camera_" "simulator"
PM_GENICAM_REFERENCE = "pm_" "genicam_controller"
SIM_MODE_REFERENCE = "sim_" "mode"
PLACEHOLDER_MODEL = "MODEL_" "PLACEHOLDER"
ROS_SETUP_SCRIPT = Path("/opt/ros/lyrical/setup.bash")
DEFAULT_REQUIRED_BRANCH = "cs_development"
SELF_AUTOFOCUS_LIST_LINE = f'"{AUTOFOCUS_REFERENCE}",'
SELF_EXPOSURE_LIST_LINE = f'"{EXPOSURE_REFERENCE}",'
SELF_AUTOFOCUS_SERVICE_LIST_LINE = f'"{AUTOFOCUS_SERVICE_REFERENCE}",'
SELF_EXPOSURE_SERVICE_LIST_LINE = f'"{EXPOSURE_SERVICE_REFERENCE}",'
SELF_CAMERA_SIMULATOR_LIST_LINE = f'"{CAMERA_SIMULATOR_REFERENCE}",'
SELF_PM_GENICAM_LIST_LINE = f'"{PM_GENICAM_REFERENCE}",'
SELF_SIM_MODE_LIST_LINE = f'"{SIM_MODE_REFERENCE}",'
CAMERA_IMPORT_ALLOWLIST_LINE = (
    f'if name.startswith("{PM_GENICAM_REFERENCE}_interfaces") or name == "cv2":'
)
CAMERA_IMPORT_ASSERT_LINE = (
    f'assert "{PM_GENICAM_REFERENCE}_interfaces" not in sys.modules'
)
CAMERA_NODE_AUTOFOCUS_ASSERT_LINE = (
    f'assert "{AUTOFOCUS_REFERENCE}" not in node_content'
)
CAMERA_NODE_EXPOSURE_ASSERT_LINE = (
    f'assert "{EXPOSURE_REFERENCE}" not in node_content'
)
CAMERA_SIMULATOR_ASSERT_SETUP_LINE = (
    f'assert "{CAMERA_SIMULATOR_REFERENCE}" not in setup_content'
)
CAMERA_SIMULATOR_ASSERT_LAUNCH_LINE = (
    f'assert "{CAMERA_SIMULATOR_REFERENCE}" not in launch_content'
)
CAMERA_NODE_SERVICE_AUTOFOCUS_ASSERT_LINE = (
    f'assert "{AUTOFOCUS_SERVICE_REFERENCE}" not in node_content'
)
CAMERA_NODE_SERVICE_EXPOSURE_ASSERT_LINE = (
    f'assert "{EXPOSURE_SERVICE_REFERENCE}" not in node_content'
)
SIM_MODE_ASSERT_LINE = (
    f'assert not _declares_launch_argument(content, "{SIM_MODE_REFERENCE}")'
)
CS_RUNTIME_PAIR_LINE = (
    f'["{CAMERA_SIMULATOR_REFERENCE}", "{PM_GENICAM_REFERENCE}"],'
)
CS_RUNTIME_SIM_MODE_DETAIL_LINE = (
    f'"camera.launch no longer exposes {SIM_MODE_REFERENCE}",'
)
CAMERA_IMPORT_ALLOWLIST_SET = {
    CAMERA_IMPORT_ALLOWLIST_LINE,
    CAMERA_IMPORT_ASSERT_LINE,
}
CAMERA_NAMESPACE_AUTOFOCUS_SET = {CAMERA_NODE_AUTOFOCUS_ASSERT_LINE}
CAMERA_NAMESPACE_EXPOSURE_SET = {CAMERA_NODE_EXPOSURE_ASSERT_LINE}
CAMERA_NAMESPACE_SIMULATOR_SET = {
    CAMERA_SIMULATOR_ASSERT_SETUP_LINE,
    CAMERA_SIMULATOR_ASSERT_LAUNCH_LINE,
}
CAMERA_NAMESPACE_AUTOFOCUS_SERVICE_SET = {
    CAMERA_NODE_SERVICE_AUTOFOCUS_ASSERT_LINE,
}
CAMERA_NAMESPACE_EXPOSURE_SERVICE_SET = {
    CAMERA_NODE_SERVICE_EXPOSURE_ASSERT_LINE,
}
SIM_MODE_ASSERT_SET = {SIM_MODE_ASSERT_LINE}

STALE_REFERENCE_LINE_ALLOWLIST: dict[str, dict[str, set[str]]] = {
    "camera_nodes/test/test_camera_imports.py": {
        PM_GENICAM_REFERENCE: CAMERA_IMPORT_ALLOWLIST_SET
    },
    "camera_nodes/test/test_camera_namespace_contract.py": {
        AUTOFOCUS_REFERENCE: CAMERA_NAMESPACE_AUTOFOCUS_SET,
        EXPOSURE_REFERENCE: CAMERA_NAMESPACE_EXPOSURE_SET,
        CAMERA_SIMULATOR_REFERENCE: CAMERA_NAMESPACE_SIMULATOR_SET,
        AUTOFOCUS_SERVICE_REFERENCE: CAMERA_NAMESPACE_AUTOFOCUS_SERVICE_SET,
        EXPOSURE_SERVICE_REFERENCE: CAMERA_NAMESPACE_EXPOSURE_SERVICE_SET,
    },
    "promoc_bringup/scripts/cs_runtime_check.py": {
        AUTOFOCUS_REFERENCE: {SELF_AUTOFOCUS_LIST_LINE},
        EXPOSURE_REFERENCE: {SELF_EXPOSURE_LIST_LINE},
        AUTOFOCUS_SERVICE_REFERENCE: {SELF_AUTOFOCUS_SERVICE_LIST_LINE},
        EXPOSURE_SERVICE_REFERENCE: {SELF_EXPOSURE_SERVICE_LIST_LINE},
        CAMERA_SIMULATOR_REFERENCE: {CS_RUNTIME_PAIR_LINE},
        PM_GENICAM_REFERENCE: {CS_RUNTIME_PAIR_LINE},
        SIM_MODE_REFERENCE: {
            SELF_SIM_MODE_LIST_LINE,
            CS_RUNTIME_SIM_MODE_DETAIL_LINE,
        },
    },
    "promoc_bringup/test/test_launch_runtime_mode.py": {
        SIM_MODE_REFERENCE: SIM_MODE_ASSERT_SET
    },
    "tools/check_project.py": {
        AUTOFOCUS_REFERENCE: {SELF_AUTOFOCUS_LIST_LINE},
        EXPOSURE_REFERENCE: {SELF_EXPOSURE_LIST_LINE},
        AUTOFOCUS_SERVICE_REFERENCE: {SELF_AUTOFOCUS_SERVICE_LIST_LINE},
        EXPOSURE_SERVICE_REFERENCE: {SELF_EXPOSURE_SERVICE_LIST_LINE},
        CAMERA_SIMULATOR_REFERENCE: {SELF_CAMERA_SIMULATOR_LIST_LINE},
        PM_GENICAM_REFERENCE: {SELF_PM_GENICAM_LIST_LINE},
        SIM_MODE_REFERENCE: {SELF_SIM_MODE_LIST_LINE},
    },
    "tools/check_project.py": {
        AUTOFOCUS_REFERENCE: {
            SELF_AUTOFOCUS_LIST_LINE,
            CAMERA_NODE_AUTOFOCUS_ASSERT_LINE,
        },
        EXPOSURE_REFERENCE: {
            SELF_EXPOSURE_LIST_LINE,
            CAMERA_NODE_EXPOSURE_ASSERT_LINE,
        },
        AUTOFOCUS_SERVICE_REFERENCE: {
            SELF_AUTOFOCUS_SERVICE_LIST_LINE,
            CAMERA_NODE_SERVICE_AUTOFOCUS_ASSERT_LINE,
        },
        EXPOSURE_SERVICE_REFERENCE: {
            SELF_EXPOSURE_SERVICE_LIST_LINE,
            CAMERA_NODE_SERVICE_EXPOSURE_ASSERT_LINE,
        },
        CAMERA_SIMULATOR_REFERENCE: {
            SELF_CAMERA_SIMULATOR_LIST_LINE,
            CS_RUNTIME_PAIR_LINE,
            CAMERA_SIMULATOR_ASSERT_SETUP_LINE,
            CAMERA_SIMULATOR_ASSERT_LAUNCH_LINE,
        },
        PM_GENICAM_REFERENCE: {
            SELF_PM_GENICAM_LIST_LINE,
            CS_RUNTIME_PAIR_LINE,
            CAMERA_IMPORT_ALLOWLIST_LINE,
            CAMERA_IMPORT_ASSERT_LINE,
        },
        SIM_MODE_REFERENCE: {
            SELF_SIM_MODE_LIST_LINE,
            CS_RUNTIME_SIM_MODE_DETAIL_LINE,
            SIM_MODE_ASSERT_LINE,
        },
    },
}

STALE_REFERENCE_NEEDLES = (
    AUTOFOCUS_REFERENCE,
    EXPOSURE_REFERENCE,
    AUTOFOCUS_SERVICE_REFERENCE,
    EXPOSURE_SERVICE_REFERENCE,
    CAMERA_SIMULATOR_REFERENCE,
    PM_GENICAM_REFERENCE,
    SIM_MODE_REFERENCE,
)


class CheckFailure(RuntimeError):
    """Raised when a required command or validation fails."""


class CommandTimeout(CheckFailure):
    """Raised when a subprocess exceeds its timeout."""


class WorkspaceResolutionError(CheckFailure):
    """Raised when no valid ROS workspace root can be determined."""


class CleanupError(CheckFailure):
    """Raised when child-process cleanup does not complete cleanly."""


@dataclass(frozen=True)
class TimeoutConfig:
    static_command: float
    build: float
    test: float
    launch_startup: float
    launch_shutdown: float
    cleanup: float

    @classmethod
    def from_env(cls) -> "TimeoutConfig":
        return cls(
            static_command=_env_float("CHECK_PROJECT_TIMEOUT_STATIC", 30.0),
            build=_env_float("CHECK_PROJECT_TIMEOUT_BUILD", 1800.0),
            test=_env_float("CHECK_PROJECT_TIMEOUT_TEST", 1800.0),
            launch_startup=_env_float("CHECK_PROJECT_TIMEOUT_LAUNCH_STARTUP", 90.0),
            launch_shutdown=_env_float("CHECK_PROJECT_TIMEOUT_LAUNCH_SHUTDOWN", 10.0),
            cleanup=_env_float("CHECK_PROJECT_TIMEOUT_CLEANUP", 10.0),
        )


@dataclass(frozen=True)
class SmokeSpec:
    name: str
    launch_arguments: tuple[str, ...]
    expected_nodes: tuple[str, ...]
    expected_topics: tuple[str, ...] = ()
    expected_services: tuple[str, ...] = ()
    forbidden_nodes: tuple[str, ...] = ()


FULL_MOCK_SPEC = SmokeSpec(
    name="Full mock smoke",
    launch_arguments=("driver_mode:=mock",),
    expected_nodes=(
        "camera_node",
        "lts300_x_axis",
        "lts300_z_axis",
        "mover",
        "system_controller",
    ),
    expected_topics=(
        "/promoc/camera/image_raw",
        "/promoc/camera/status",
        "/promoc/status",
    ),
    expected_services=("/promoc/stop_all", "/promoc/reset_stop"),
)

PARTIAL_MOCK_SPEC = SmokeSpec(
    name="Partial mock smoke",
    launch_arguments=("driver_mode:=mock", "camera:=false", "planar_motor:=false"),
    expected_nodes=("lts300_x_axis", "system_controller"),
    forbidden_nodes=("camera_node", "mover"),
)


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError as exc:
        raise CheckFailure(f"Environment variable {name} must be numeric.") from exc
    if parsed <= 0:
        raise CheckFailure(f"Environment variable {name} must be positive.")
    return parsed


class Checker:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.required_skips = 0

    def run_check(
        self,
        name: str,
        check_fn: Callable[[], bool | str],
        *,
        required: bool = False,
    ) -> None:
        print(f"Running check: {name} ... ", end="", flush=True)
        try:
            result = check_fn()
        except KeyboardInterrupt:
            print("\033[91mFAIL\033[0m")
            print("  Interrupted by user.")
            self.failed += 1
            return
        except Exception as exc:
            print("\033[91mFAIL\033[0m")
            print(f"  Error: {exc}")
            self.failed += 1
            return

        if result is True:
            print("\033[92mPASS\033[0m")
            self.passed += 1
            return
        if result == "SKIP":
            print("\033[93mSKIP\033[0m")
            self.skipped += 1
            if required:
                self.required_skips += 1
            return

        print("\033[91mFAIL\033[0m")
        self.failed += 1

    def exit_code(self) -> int:
        if self.failed > 0 or self.required_skips > 0:
            return 1
        return 0


def _command_text(args: Sequence[str]) -> str:
    return shlex.join(str(part) for part in args)


def run_command(
    args: Sequence[str],
    *,
    cwd: Path,
    timeout: float,
    env: Mapping[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            list(args),
            cwd=cwd,
            env=dict(env) if env is not None else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CommandTimeout(
            f"Command timed out after {timeout:.1f}s: {_command_text(args)}"
        ) from exc

    if check and completed.returncode != 0:
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        raise CheckFailure(
            f"Command failed ({completed.returncode}): {_command_text(args)}\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        )
    return completed


def capture_sourced_environment(
    *,
    cwd: Path,
    source_scripts: Sequence[Path],
    timeout: float,
    base_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    command_parts = []
    for script in source_scripts:
        command_parts.append(f"source {shlex.quote(str(script))}")
    command_parts.append("env -0")
    completed = run_command(
        ["bash", "-lc", " && ".join(command_parts)],
        cwd=cwd,
        timeout=timeout,
        env=base_env,
    )
    environment: dict[str, str] = {}
    for chunk in completed.stdout.split("\0"):
        if not chunk or "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        environment[key] = value
    return environment


def determine_repository_root(script_repository_root: Path, timeouts: TimeoutConfig) -> Path:
    try:
        completed = run_command(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=script_repository_root,
            timeout=timeouts.static_command,
        )
        return Path(completed.stdout.strip()).resolve()
    except CheckFailure:
        return script_repository_root.resolve()


def validate_workspace_root(workspace_root: Path, repository_root: Path) -> Path:
    candidate = workspace_root.resolve()
    src_dir = candidate / "src"
    expected_repo = src_dir / repository_root.name
    if not src_dir.is_dir():
        raise WorkspaceResolutionError(
            f"Workspace root is invalid: missing src/ directory under {candidate}"
        )
    if not expected_repo.exists():
        raise WorkspaceResolutionError(
            "Workspace root is invalid: expected package repository "
            f"{expected_repo} does not exist."
        )
    if not expected_repo.samefile(repository_root):
        raise WorkspaceResolutionError(
            "Workspace root is invalid: expected package repository does not match "
            f"{repository_root}"
        )
    return candidate


def resolve_workspace_root(
    repository_root: Path,
    timeouts: TimeoutConfig,
    workspace_override: str | None = None,
) -> Path:
    if workspace_override:
        return validate_workspace_root(Path(workspace_override), repository_root)

    src_dir = repository_root.parent
    if src_dir.name != "src":
        raise WorkspaceResolutionError(
            "Unable to determine ROS workspace root automatically. "
            "Use --workspace-root /path/to/workspace."
        )

    workspace_root = src_dir.parent
    return validate_workspace_root(workspace_root, repository_root)


def load_ros_environment(timeouts: TimeoutConfig) -> dict[str, str] | None:
    current = dict(os.environ)
    if current.get("ROS_DISTRO") == "lyrical" and shutil.which("colcon"):
        return current
    if not ROS_SETUP_SCRIPT.exists():
        return None
    try:
        return capture_sourced_environment(
            cwd=SCRIPT_REPOSITORY_ROOT,
            source_scripts=(ROS_SETUP_SCRIPT,),
            timeout=timeouts.static_command,
            base_env=current,
        )
    except CheckFailure:
        return None


def ensure_workspace_environment(
    workspace_root: Path,
    base_env: Mapping[str, str],
    timeouts: TimeoutConfig,
) -> dict[str, str]:
    install_setup = workspace_root / "install" / "setup.bash"
    if not install_setup.exists():
        raise CheckFailure(f"Missing workspace setup script: {install_setup}")
    return capture_sourced_environment(
        cwd=workspace_root,
        source_scripts=(ROS_SETUP_SCRIPT, install_setup),
        timeout=timeouts.static_command,
        base_env=base_env,
    )


def run_git_command(
    repository_root: Path,
    timeouts: TimeoutConfig,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return run_command(
        ["git", *args],
        cwd=repository_root,
        timeout=timeouts.static_command,
        check=check,
    )


def list_tracked_paths(repository_root: Path, timeouts: TimeoutConfig) -> list[Path]:
    completed = run_git_command(repository_root, timeouts, "ls-files", "-z")
    return [
        Path(item)
        for item in completed.stdout.split("\0")
        if item and not item.startswith(".agent-local/")
    ]


def iter_tracked_regular_files(
    repository_root: Path,
    timeouts: TimeoutConfig,
    *,
    suffixes: Iterable[str] | None = None,
) -> list[Path]:
    suffix_filter = set(suffixes or ())
    regular_files: list[Path] = []
    for rel_path in list_tracked_paths(repository_root, timeouts):
        if rel_path == EXTERNAL_GITLINK:
            continue
        if rel_path.parts and rel_path.parts[0] in WORKSPACE_OUTPUT_DIRS:
            continue
        if suffix_filter and rel_path.suffix not in suffix_filter:
            continue
        candidate = repository_root / rel_path
        if candidate.is_file():
            regular_files.append(rel_path)
    return regular_files


def allowed_stale_reference_line(rel_path: Path, needle: str, line: str) -> bool:
    per_file = STALE_REFERENCE_LINE_ALLOWLIST.get(rel_path.as_posix(), {})
    allowed_lines = per_file.get(needle, set())
    return line.strip() in allowed_lines


def check_branch(repository_root: Path, timeouts: TimeoutConfig) -> bool:
    completed = run_git_command(
        repository_root,
        timeouts,
        "branch",
        "--show-current",
        check=False,
    )
    current_branch = completed.stdout.strip()
    if completed.returncode == 0 and current_branch == DEFAULT_REQUIRED_BRANCH:
        return True
    print(f"  Current branch is not {DEFAULT_REQUIRED_BRANCH}: {current_branch}")
    return False


def check_git_status(repository_root: Path, timeouts: TimeoutConfig) -> bool:
    completed = run_git_command(
        repository_root,
        timeouts,
        "status",
        "--ignore-submodules=all",
        "--short",
    )
    if completed.stdout.strip():
        print(f"  Working tree not clean:\n{completed.stdout.rstrip()}")
        return False
    return True


def find_conflict_marker_issues(text: str) -> list[str]:
    issues: list[str] = []
    opening_line: int | None = None
    opening_marker: str | None = None
    saw_separator = False

    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.rstrip()
        if stripped.startswith("<<<<<<<"):
            if opening_marker is not None:
                issues.append(
                    f"line {line_number}: nested opening marker '{stripped}'"
                )
            opening_line = line_number
            opening_marker = stripped
            saw_separator = False
            issues.append(
                f"line {line_number}: opening marker '{stripped}' starts conflict block"
            )
            continue

        if stripped.startswith("======="):
            if opening_marker is not None:
                saw_separator = True
                issues.append(
                    f"line {line_number}: separator marker '{stripped}' inside conflict block"
                )
            continue

        if stripped.startswith(">>>>>>>"):
            if opening_marker is None:
                issues.append(
                    f"line {line_number}: standalone closing marker '{stripped}'"
                )
            else:
                issues.append(
                    f"line {line_number}: closing marker '{stripped}' ends conflict block"
                )
                opening_line = None
                opening_marker = None
                saw_separator = False

    if opening_marker is not None and opening_line is not None:
        if not saw_separator:
            issues.append(
                f"line {opening_line}: suspicious opening marker '{opening_marker}' without separator"
            )
        issues.append(
            f"line {opening_line}: incomplete conflict block started by '{opening_marker}'"
        )
    return issues


def check_merge_markers(repository_root: Path, timeouts: TimeoutConfig) -> bool:
    problems: list[str] = []
    for rel_path in iter_tracked_regular_files(repository_root, timeouts):
        content = (repository_root / rel_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )
        issues = find_conflict_marker_issues(content)
        if issues:
            problems.append(f"{rel_path}: {issues[0]}")
    if problems:
        print("  Merge markers found:")
        for problem in problems[:20]:
            print(f"  - {problem}")
        return False
    return True


def check_agent_local_not_tracked(repository_root: Path, timeouts: TimeoutConfig) -> bool:
    completed = run_git_command(
        repository_root,
        timeouts,
        "ls-files",
        ".agent-local/",
        check=False,
    )
    if completed.stdout.strip():
        print(f"  .agent-local/ files are tracked:\n{completed.stdout.rstrip()}")
        return False
    return True


def check_gitlink_not_staged(repository_root: Path, timeouts: TimeoutConfig) -> bool:
    completed = run_git_command(
        repository_root,
        timeouts,
        "diff",
        "--cached",
        "--name-only",
    )
    staged_paths = completed.stdout.splitlines()
    if EXTERNAL_GITLINK.as_posix() in staged_paths:
        print(f"  External gitlink is staged: {EXTERNAL_GITLINK}")
        return False
    return True


def check_generated_dirs(repository_root: Path, timeouts: TimeoutConfig) -> bool:
    completed = run_git_command(
        repository_root,
        timeouts,
        "ls-files",
        *WORKSPACE_OUTPUT_DIRS,
        check=False,
    )
    if completed.stdout.strip():
        print(f"  Generated dirs are tracked:\n{completed.stdout.rstrip()}")
        return False
    return True


def check_python_syntax(repository_root: Path, timeouts: TimeoutConfig) -> bool:
    for rel_path in iter_tracked_regular_files(
        repository_root,
        timeouts,
        suffixes=(".py",),
    ):
        try:
            ast.parse((repository_root / rel_path).read_text(encoding="utf-8"))
        except SyntaxError as exc:
            print(f"  Syntax error in {rel_path}: {exc}")
            return False
    return True


def check_yaml_parsing(repository_root: Path, timeouts: TimeoutConfig) -> bool:
    for rel_path in iter_tracked_regular_files(
        repository_root,
        timeouts,
        suffixes=(".yaml",),
    ):
        try:
            yaml.safe_load(
                (repository_root / rel_path).read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
            )
        except Exception as exc:
            print(f"  YAML parsing error in {rel_path}: {exc}")
            return False
    return True


def check_package_yaml_files_exist(repository_root: Path) -> bool:
    for rel_path in REQUIRED_CONFIGS:
        if not (repository_root / rel_path).exists():
            print(f"  Missing required config: {rel_path}")
            return False
    return True


def check_stale_references(repository_root: Path, timeouts: TimeoutConfig) -> bool:
    for rel_path in iter_tracked_regular_files(
        repository_root,
        timeouts,
        suffixes=(".py",),
    ):
        lines = (repository_root / rel_path).read_text(
            encoding="utf-8",
            errors="ignore",
        ).splitlines()
        for line_number, line in enumerate(lines, start=1):
            for needle in STALE_REFERENCE_NEEDLES:
                if needle in line and not allowed_stale_reference_line(rel_path, needle, line):
                    print(
                        f"  Stale reference '{needle}' in {rel_path}:{line_number}: {line.strip()}"
                    )
                    return False
    return True


def check_placeholder_models(repository_root: Path, timeouts: TimeoutConfig) -> bool:
    for rel_path in iter_tracked_regular_files(repository_root, timeouts):
        for line_number, line in enumerate(
            (repository_root / rel_path).read_text(
                encoding="utf-8",
                errors="ignore",
            ).splitlines(),
            start=1,
        ):
            if PLACEHOLDER_MODEL in line:
                print(
                    f"  Unresolved placeholder in {rel_path}:{line_number}: {line.strip()}"
                )
                return False
    return True


def check_optional_ros_environment(timeouts: TimeoutConfig) -> bool | str:
    ros_env = load_ros_environment(timeouts)
    if ros_env is None:
        print("  ROS Lyrical environment unavailable; ROS-dependent checks skipped in quick mode.")
        return "SKIP"
    return True


def clean_workspace_outputs(workspace_root: Path) -> None:
    for name in WORKSPACE_OUTPUT_DIRS:
        target = workspace_root / name
        if not target.exists():
            continue
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)


def verify_workspace_outputs(workspace_root: Path) -> None:
    missing = [name for name in WORKSPACE_OUTPUT_DIRS if not (workspace_root / name).exists()]
    if missing:
        raise CheckFailure(
            "Expected ROS workspace output directories were not created at the workspace root: "
            + ", ".join(missing)
        )


def check_colcon_build(
    workspace_root: Path,
    ros_env: Mapping[str, str],
    timeouts: TimeoutConfig,
) -> bool:
    try:
        clean_workspace_outputs(workspace_root)
        run_command(
            ["colcon", "build", "--symlink-install"],
            cwd=workspace_root,
            env=ros_env,
            timeout=timeouts.build,
        )
        verify_workspace_outputs(workspace_root)
        return True
    except CheckFailure as exc:
        print(f"  {exc}")
        return False


def check_colcon_test(
    workspace_root: Path,
    ros_env: Mapping[str, str],
    timeouts: TimeoutConfig,
) -> bool:
    try:
        workspace_env = ensure_workspace_environment(workspace_root, ros_env, timeouts)
        run_command(
            ["colcon", "test"],
            cwd=workspace_root,
            env=workspace_env,
            timeout=timeouts.test,
        )
        verify_workspace_outputs(workspace_root)
        return True
    except CheckFailure as exc:
        print(f"  {exc}")
        return False


def check_colcon_test_result(
    workspace_root: Path,
    ros_env: Mapping[str, str],
    timeouts: TimeoutConfig,
) -> bool:
    try:
        workspace_env = ensure_workspace_environment(workspace_root, ros_env, timeouts)
        run_command(
            ["colcon", "test-result", "--verbose"],
            cwd=workspace_root,
            env=workspace_env,
            timeout=timeouts.test,
        )
        return True
    except CheckFailure as exc:
        print(f"  {exc}")
        return False


def collect_process_output(process: subprocess.Popen[str], timeout: float) -> str:
    try:
        stdout, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise CleanupError(
            f"Timed out while reaping launch process after {timeout:.1f}s."
        ) from exc
    return stdout or ""


def terminate_process_group(
    process: subprocess.Popen[str],
    timeouts: TimeoutConfig,
) -> str:
    if process.poll() is not None:
        return collect_process_output(process, timeouts.cleanup)

    try:
        os.killpg(process.pid, signal.SIGINT)
    except ProcessLookupError:
        return collect_process_output(process, timeouts.cleanup)

    try:
        return collect_process_output(process, timeouts.launch_shutdown)
    except CleanupError:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return collect_process_output(process, timeouts.cleanup)


def run_ros_listing(
    ros_env: Mapping[str, str],
    workspace_root: Path,
    timeouts: TimeoutConfig,
    *args: str,
) -> str:
    completed = run_command(
        list(args),
        cwd=workspace_root,
        env=ros_env,
        timeout=timeouts.static_command,
        check=False,
    )
    return completed.stdout


def smoke_condition_met(
    *,
    spec: SmokeSpec,
    nodes: str,
    topics: str,
    services: str,
) -> bool:
    if not all(node in nodes for node in spec.expected_nodes):
        return False
    if not all(topic in topics for topic in spec.expected_topics):
        return False
    if not all(service in services for service in spec.expected_services):
        return False
    if any(node in nodes for node in spec.forbidden_nodes):
        return False
    return True


def run_smoke_check(
    spec: SmokeSpec,
    workspace_root: Path,
    ros_env: Mapping[str, str],
    timeouts: TimeoutConfig,
) -> bool:
    workspace_env = ensure_workspace_environment(workspace_root, ros_env, timeouts)
    launch_args = [
        "ros2",
        "launch",
        "promoc_bringup",
        "system.launch.py",
        *spec.launch_arguments,
    ]
    process = subprocess.Popen(
        launch_args,
        cwd=workspace_root,
        env=workspace_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    deadline = time.monotonic() + timeouts.launch_startup
    last_nodes = ""
    last_topics = ""
    last_services = ""

    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                output = terminate_process_group(process, timeouts)
                print(
                    f"  Launch exited early with code {process.returncode}.\n"
                    f"  Output:\n{output.rstrip()}"
                )
                return False

            last_nodes = run_ros_listing(
                workspace_env,
                workspace_root,
                timeouts,
                "ros2",
                "node",
                "list",
            )
            last_topics = run_ros_listing(
                workspace_env,
                workspace_root,
                timeouts,
                "ros2",
                "topic",
                "list",
            )
            last_services = run_ros_listing(
                workspace_env,
                workspace_root,
                timeouts,
                "ros2",
                "service",
                "list",
            )
            if smoke_condition_met(
                spec=spec,
                nodes=last_nodes,
                topics=last_topics,
                services=last_services,
            ):
                return True
            time.sleep(1.0)

        print(
            f"  Timed out waiting for {spec.name} readiness after "
            f"{timeouts.launch_startup:.1f}s.\n"
            f"  Nodes:\n{last_nodes.rstrip()}\n"
            f"  Topics:\n{last_topics.rstrip()}\n"
            f"  Services:\n{last_services.rstrip()}"
        )
        return False
    finally:
        try:
            terminate_process_group(process, timeouts)
        except CleanupError as exc:
            print(f"  Cleanup failed: {exc}")
            raise


def preflight_full_mode(
    repository_root: Path,
    workspace_override: str | None,
    timeouts: TimeoutConfig,
) -> tuple[Path, dict[str, str]] | None:
    try:
        workspace_root = resolve_workspace_root(
            repository_root,
            timeouts,
            workspace_override,
        )
    except WorkspaceResolutionError as exc:
        print(f"  {exc}")
        return None

    ros_env = load_ros_environment(timeouts)
    if ros_env is None:
        print("  ROS Lyrical environment or colcon is unavailable.")
        return None

    if shutil.which("colcon", path=ros_env.get("PATH")) is None:
        print("  colcon is unavailable in the resolved ROS environment.")
        return None

    print(f"  Repository root: {repository_root}")
    print(f"  Resolved ROS workspace root: {workspace_root}")
    return workspace_root, ros_env


def run_quick_checks(
    checker: Checker,
    repository_root: Path,
    timeouts: TimeoutConfig,
    *,
    allow_dirty: bool,
) -> None:
    checker.run_check(
        f"Branch {DEFAULT_REQUIRED_BRANCH}",
        lambda: check_branch(repository_root, timeouts),
    )
    if not allow_dirty:
        checker.run_check(
            "Git status clean",
            lambda: check_git_status(repository_root, timeouts),
        )
    checker.run_check(
        "No merge markers",
        lambda: check_merge_markers(repository_root, timeouts),
    )
    checker.run_check(
        ".agent-local not tracked",
        lambda: check_agent_local_not_tracked(repository_root, timeouts),
    )
    checker.run_check(
        "Gitlink not staged",
        lambda: check_gitlink_not_staged(repository_root, timeouts),
    )
    checker.run_check(
        "Generated dirs not tracked",
        lambda: check_generated_dirs(repository_root, timeouts),
    )
    checker.run_check(
        "Python syntax",
        lambda: check_python_syntax(repository_root, timeouts),
    )
    checker.run_check(
        "YAML parsing",
        lambda: check_yaml_parsing(repository_root, timeouts),
    )
    checker.run_check(
        "Package YAMLs exist",
        lambda: check_package_yaml_files_exist(repository_root),
    )
    checker.run_check(
        "No stale references",
        lambda: check_stale_references(repository_root, timeouts),
    )
    checker.run_check(
        "No placeholder models",
        lambda: check_placeholder_models(repository_root, timeouts),
    )
    checker.run_check(
        "ROS Lyrical environment available",
        lambda: check_optional_ros_environment(timeouts),
    )


def run_full_checks(
    checker: Checker,
    repository_root: Path,
    timeouts: TimeoutConfig,
    *,
    workspace_override: str | None,
) -> None:
    preflight = preflight_full_mode(repository_root, workspace_override, timeouts)
    if preflight is None:
        checker.run_check(
            "ROS workspace and environment available",
            lambda: "SKIP",
            required=True,
        )
        return

    workspace_root, ros_env = preflight
    checker.run_check(
        "colcon build",
        lambda: check_colcon_build(workspace_root, ros_env, timeouts),
        required=True,
    )
    checker.run_check(
        "colcon test",
        lambda: check_colcon_test(workspace_root, ros_env, timeouts),
        required=True,
    )
    checker.run_check(
        "colcon test-result",
        lambda: check_colcon_test_result(workspace_root, ros_env, timeouts),
        required=True,
    )
    checker.run_check(
        FULL_MOCK_SPEC.name,
        lambda: run_smoke_check(FULL_MOCK_SPEC, workspace_root, ros_env, timeouts),
        required=True,
    )
    checker.run_check(
        PARTIAL_MOCK_SPEC.name,
        lambda: run_smoke_check(PARTIAL_MOCK_SPEC, workspace_root, ros_env, timeouts),
        required=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ProMOC Project Checker")
    parser.add_argument("--quick", action="store_true", help="Run quick checks")
    parser.add_argument("--full", action="store_true", help="Run full checks")
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Do not require a clean working tree",
    )
    parser.add_argument(
        "--workspace-root",
        help="Explicit ROS workspace root to validate and use for full mode",
    )
    parser.add_argument(
        "--print-timeout",
        action="store_true",
        help="Print timeout configuration and exit",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.print_timeout:
        timeouts = TimeoutConfig.from_env()
        print(f"static_command: {timeouts.static_command}")
        print(f"build: {timeouts.build}")
        print(f"test: {timeouts.test}")
        print(f"launch_startup: {timeouts.launch_startup}")
        print(f"launch_shutdown: {timeouts.launch_shutdown}")
        print(f"cleanup: {timeouts.cleanup}")
        return 0

    if not args.quick and not args.full:
        build_parser().print_help()
        return 0

    timeouts = TimeoutConfig.from_env()
    repository_root = determine_repository_root(SCRIPT_REPOSITORY_ROOT, timeouts)
    checker = Checker()

    try:
        run_quick_checks(
            checker,
            repository_root,
            timeouts,
            allow_dirty=args.allow_dirty,
        )
        if args.full:
            run_full_checks(
                checker,
                repository_root,
                timeouts,
                workspace_override=args.workspace_root,
            )
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130
    except CommandTimeout as exc:
        print(f"\nTimeout: {exc}")
        return 1
    except subprocess.SubprocessError as exc:
        print(f"\nSubprocess failure: {exc}")
        return 1
    except Exception as exc:
        print(f"\nUnexpected error: {exc}")
        return 1

    print(
        f"\nSummary: {checker.passed} passed, {checker.skipped} skipped, "
        f"{checker.failed} failed."
    )
    return checker.exit_code()


if __name__ == "__main__":
    sys.exit(main())
