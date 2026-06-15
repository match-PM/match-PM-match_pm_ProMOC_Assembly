#!/usr/bin/env python3
"""Focused tests for the project-check tool."""

import importlib.util
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "check_project.py"
STALE_AUTOFOCUS = "/promoc/camera/" "autofocus"
PLACEHOLDER_VALUE = "MODEL_" "PLACEHOLDER"
CONFLICT_OPEN_HEAD = "<" * 7 + " HEAD"
CONFLICT_OPEN_BRANCH = "<" * 7 + " branch-name"
CONFLICT_SEPARATOR = "=" * 7
CONFLICT_CLOSE_BRANCH = ">" * 7 + " branch-name"


def load_module():
    spec = importlib.util.spec_from_file_location("check_project", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_tool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL_PATH), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def init_workspace_repo(tmp_path: Path) -> tuple[Path, Path]:
    workspace_root = tmp_path / "workspace"
    repository_root = workspace_root / "src" / ROOT.name
    repository_root.mkdir(parents=True)
    subprocess.run(
        ["git", "init", "-b", "cs_development"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "tests@example.com"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Tests"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    write_file(repository_root / ".gitignore", "build/\ninstall/\nlog/\n")
    return workspace_root, repository_root


def stage_all(repository_root: Path) -> None:
    subprocess.run(
        ["git", "add", "."],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )


def commit_all(repository_root: Path) -> None:
    stage_all(repository_root)
    subprocess.run(
        ["git", "commit", "-m", "baseline"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )


def fake_repo_with_file(tmp_path: Path, rel_path: str, content: str) -> Path:
    _, repository_root = init_workspace_repo(tmp_path)
    write_file(repository_root / rel_path, content)
    commit_all(repository_root)
    return repository_root


def patch_quick_success(monkeypatch, module, repository_root: Path) -> None:
    monkeypatch.setattr(
        module,
        "determine_repository_root",
        lambda *_args, **_kwargs: repository_root,
    )
    monkeypatch.setattr(module, "check_merge_markers", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        module, "check_agent_local_not_tracked", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(module, "check_gitlink_not_staged", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(module, "check_generated_dirs", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(module, "check_python_syntax", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(module, "check_yaml_parsing", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        module, "check_package_yaml_files_exist", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(module, "check_stale_references", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        module, "check_placeholder_models", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(
        module, "check_optional_ros_environment", lambda *_args, **_kwargs: "SKIP"
    )


class FakePopen:
    def __init__(self, exit_immediately: bool = False, communicate_timeout: bool = False):
        self.pid = 43210
        self.returncode = 0 if exit_immediately else None
        self.exit_immediately = exit_immediately
        self.communicate_timeout = communicate_timeout
        self.communicate_calls = 0

    def poll(self):
        return self.returncode

    def communicate(self, timeout=None):
        self.communicate_calls += 1
        if self.communicate_timeout and self.communicate_calls == 1:
            raise subprocess.TimeoutExpired(cmd="fake", timeout=timeout)
        self.returncode = 0
        return ("launch output", "")


def test_help_output():
    res = run_tool("--help")
    assert res.returncode == 0
    assert "--quick" in res.stdout
    assert "--full" in res.stdout
    assert "--workspace-root" in res.stdout


def test_missing_required_arguments_prints_help():
    res = run_tool()
    assert res.returncode == 0
    assert "usage:" in res.stdout.lower()


def test_quick_mode_passes():
    res = run_tool("--quick", "--allow-dirty")
    assert res.returncode == 0, f"Quick mode failed:\nstdout={res.stdout}\nstderr={res.stderr}"
    assert "Branch cs_development" in res.stdout
    assert "Summary:" in res.stdout


def test_subprocess_timeout_produces_failure(monkeypatch):
    module = load_module()

    def fake_run(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="slow", timeout=1.0)

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    with pytest.raises(module.CommandTimeout):
        module.run_command(["slow"], cwd=ROOT, timeout=1.0)


def test_resolve_workspace_root_distinguishes_repository_root(tmp_path):
    module = load_module()
    workspace_root, repository_root = init_workspace_repo(tmp_path)
    resolved = module.resolve_workspace_root(
        repository_root,
        module.TimeoutConfig.from_env(),
    )
    assert resolved == workspace_root.resolve()
    assert resolved != repository_root.resolve()


def test_valid_workspace_override_is_accepted(tmp_path):
    module = load_module()
    workspace_root, repository_root = init_workspace_repo(tmp_path)
    resolved = module.resolve_workspace_root(
        repository_root,
        module.TimeoutConfig.from_env(),
        workspace_override=str(workspace_root),
    )
    assert resolved == workspace_root.resolve()


def test_invalid_workspace_override_fails(tmp_path):
    module = load_module()
    _, repository_root = init_workspace_repo(tmp_path)
    invalid_root = tmp_path / "invalid"
    invalid_root.mkdir()
    with pytest.raises(module.WorkspaceResolutionError):
        module.resolve_workspace_root(
            repository_root,
            module.TimeoutConfig.from_env(),
            workspace_override=str(invalid_root),
        )


def test_colcon_commands_use_workspace_root(monkeypatch, tmp_path):
    module = load_module()
    workspace_root, _repository_root = init_workspace_repo(tmp_path)
    (workspace_root / "install").mkdir()
    write_file(workspace_root / "install" / "setup.bash", "true\n")
    calls: list[tuple[tuple[str, ...], Path]] = []

    def fake_run_command(args, *, cwd, timeout, env=None, check=True):
        calls.append((tuple(args), cwd))
        if args[:2] == ["bash", "-lc"]:
            return subprocess.CompletedProcess(args, 0, stdout="PATH=/usr/bin\0", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(module, "run_command", fake_run_command)
    monkeypatch.setattr(module, "clean_workspace_outputs", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module, "verify_workspace_outputs", lambda *_args, **_kwargs: None)
    timeouts = module.TimeoutConfig.from_env()
    ros_env = {"ROS_DISTRO": "lyrical", "PATH": os.environ["PATH"]}

    assert module.check_colcon_build(workspace_root, ros_env, timeouts) is True
    assert module.check_colcon_test(workspace_root, ros_env, timeouts) is True
    assert module.check_colcon_test_result(workspace_root, ros_env, timeouts) is True

    assert calls[0] == (("colcon", "build", "--symlink-install"), workspace_root)
    assert calls[1][1] == workspace_root
    assert calls[2] == (("colcon", "test"), workspace_root)
    assert calls[3][1] == workspace_root
    assert calls[4] == (("colcon", "test-result", "--verbose"), workspace_root)


def test_smoke_cleanup_runs_after_success(monkeypatch, tmp_path):
    module = load_module()
    workspace_root, _repository_root = init_workspace_repo(tmp_path)
    write_file(workspace_root / "install" / "setup.bash", "true\n")
    killed: list[tuple[int, int]] = []
    fake_process = FakePopen()

    monkeypatch.setattr(
        module,
        "ensure_workspace_environment",
        lambda *_args, **_kwargs: {"PATH": os.environ["PATH"]},
    )
    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: fake_process)
    monkeypatch.setattr(module.os, "killpg", lambda pid, sig: killed.append((pid, sig)))
    monkeypatch.setattr(
        module,
        "run_ros_listing",
        lambda *_args, **_kwargs: "\n".join(
            [
                "camera_node",
                "lts300_x_axis",
                "lts300_z_axis",
                "mover",
                "system_controller",
                "/promoc/camera/image_raw",
                "/promoc/camera/status",
                "/promoc/status",
                "/promoc/stop_all",
                "/promoc/reset_stop",
            ]
        ),
    )

    assert module.run_smoke_check(
        module.FULL_MOCK_SPEC,
        workspace_root,
        {"PATH": os.environ["PATH"]},
        module.TimeoutConfig.from_env(),
    )
    assert killed == [(fake_process.pid, signal.SIGINT)]


def test_smoke_cleanup_runs_after_failed_smoke(monkeypatch, tmp_path):
    module = load_module()
    workspace_root, _repository_root = init_workspace_repo(tmp_path)
    write_file(workspace_root / "install" / "setup.bash", "true\n")
    killed: list[tuple[int, int]] = []
    fake_process = FakePopen(exit_immediately=True)

    monkeypatch.setattr(
        module,
        "ensure_workspace_environment",
        lambda *_args, **_kwargs: {"PATH": os.environ["PATH"]},
    )
    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: fake_process)
    monkeypatch.setattr(module.os, "killpg", lambda pid, sig: killed.append((pid, sig)))

    assert (
        module.run_smoke_check(
            module.FULL_MOCK_SPEC,
            workspace_root,
            {"PATH": os.environ["PATH"]},
            module.TimeoutConfig.from_env(),
        )
        is False
    )
    assert killed == []


def test_smoke_cleanup_runs_after_command_failure(monkeypatch, tmp_path):
    module = load_module()
    workspace_root, _repository_root = init_workspace_repo(tmp_path)
    write_file(workspace_root / "install" / "setup.bash", "true\n")
    killed: list[tuple[int, int]] = []
    fake_process = FakePopen()

    monkeypatch.setattr(
        module,
        "ensure_workspace_environment",
        lambda *_args, **_kwargs: {"PATH": os.environ["PATH"]},
    )
    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: fake_process)
    monkeypatch.setattr(module.os, "killpg", lambda pid, sig: killed.append((pid, sig)))
    monkeypatch.setattr(
        module,
        "run_ros_listing",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(module.CheckFailure("listing failed")),
    )

    with pytest.raises(module.CheckFailure):
        module.run_smoke_check(
            module.FULL_MOCK_SPEC,
            workspace_root,
            {"PATH": os.environ["PATH"]},
            module.TimeoutConfig.from_env(),
        )
    assert killed == [(fake_process.pid, signal.SIGINT)]


def test_smoke_cleanup_runs_after_timeout(monkeypatch, tmp_path):
    module = load_module()
    workspace_root, _repository_root = init_workspace_repo(tmp_path)
    write_file(workspace_root / "install" / "setup.bash", "true\n")
    killed: list[tuple[int, int]] = []
    fake_process = FakePopen()
    clock = {"now": 0.0}

    def fake_monotonic():
        return clock["now"]

    def fake_sleep(seconds):
        clock["now"] += seconds + 1.0

    monkeypatch.setattr(
        module,
        "ensure_workspace_environment",
        lambda *_args, **_kwargs: {"PATH": os.environ["PATH"]},
    )
    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: fake_process)
    monkeypatch.setattr(module.os, "killpg", lambda pid, sig: killed.append((pid, sig)))
    monkeypatch.setattr(module.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(module.time, "sleep", fake_sleep)
    monkeypatch.setattr(module, "run_ros_listing", lambda *_args, **_kwargs: "")

    timeouts = module.TimeoutConfig(
        static_command=1.0,
        build=1.0,
        test=1.0,
        launch_startup=1.0,
        launch_shutdown=1.0,
        cleanup=1.0,
    )
    assert (
        module.run_smoke_check(
            module.FULL_MOCK_SPEC,
            workspace_root,
            {"PATH": os.environ["PATH"]},
            timeouts,
        )
        is False
    )
    assert killed == [(fake_process.pid, signal.SIGINT)]


def test_ctrl_c_cleanup_terminates_process_group(monkeypatch, tmp_path):
    module = load_module()
    workspace_root, _repository_root = init_workspace_repo(tmp_path)
    write_file(workspace_root / "install" / "setup.bash", "true\n")
    killed: list[tuple[int, int]] = []
    fake_process = FakePopen()

    monkeypatch.setattr(
        module,
        "ensure_workspace_environment",
        lambda *_args, **_kwargs: {"PATH": os.environ["PATH"]},
    )
    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: fake_process)
    monkeypatch.setattr(module.os, "killpg", lambda pid, sig: killed.append((pid, sig)))
    monkeypatch.setattr(
        module,
        "run_ros_listing",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    with pytest.raises(KeyboardInterrupt):
        module.run_smoke_check(
            module.FULL_MOCK_SPEC,
            workspace_root,
            {"PATH": os.environ["PATH"]},
            module.TimeoutConfig.from_env(),
        )
    assert killed == [(fake_process.pid, signal.SIGINT)]


def test_cleanup_is_bounded(monkeypatch):
    module = load_module()
    fake_process = FakePopen(communicate_timeout=True)
    killed: list[tuple[int, int]] = []

    monkeypatch.setattr(module.os, "killpg", lambda pid, sig: killed.append((pid, sig)))
    timeouts = module.TimeoutConfig(
        static_command=1.0,
        build=1.0,
        test=1.0,
        launch_startup=1.0,
        launch_shutdown=1.0,
        cleanup=1.0,
    )
    output = module.terminate_process_group(fake_process, timeouts)
    assert output == "launch output"
    assert killed == [(fake_process.pid, signal.SIGINT), (fake_process.pid, signal.SIGKILL)]


def test_main_returns_nonzero_on_required_timeout(monkeypatch, tmp_path):
    module = load_module()
    workspace_root, repository_root = init_workspace_repo(tmp_path)
    patch_quick_success(monkeypatch, module, repository_root)
    monkeypatch.setattr(
        module,
        "preflight_full_mode",
        lambda *_args, **_kwargs: (workspace_root, {"PATH": os.environ["PATH"]}),
    )
    monkeypatch.setattr(
        module,
        "check_colcon_build",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            module.CommandTimeout("build timed out")
        ),
    )
    monkeypatch.setattr(module, "check_colcon_test", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        module, "check_colcon_test_result", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(module, "run_smoke_check", lambda *_args, **_kwargs: True)

    assert module.main(["--full"]) == 1


def test_cleanup_failure_produces_nonzero_exit_status(monkeypatch, tmp_path):
    module = load_module()
    workspace_root, repository_root = init_workspace_repo(tmp_path)
    patch_quick_success(monkeypatch, module, repository_root)
    monkeypatch.setattr(
        module,
        "preflight_full_mode",
        lambda *_args, **_kwargs: (workspace_root, {"PATH": os.environ["PATH"]}),
    )
    monkeypatch.setattr(module, "check_colcon_build", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(module, "check_colcon_test", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        module, "check_colcon_test_result", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(
        module,
        "run_smoke_check",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(module.CleanupError("cleanup failed")),
    )

    assert module.main(["--full"]) == 1


def test_missing_ros_is_nonzero_in_full_mode(monkeypatch, tmp_path):
    module = load_module()
    _, repository_root = init_workspace_repo(tmp_path)
    patch_quick_success(monkeypatch, module, repository_root)
    monkeypatch.setattr(module, "preflight_full_mode", lambda *_args, **_kwargs: None)
    assert module.main(["--full"]) == 1


def test_missing_ros_is_skipped_in_quick_mode(monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "load_ros_environment", lambda *_args, **_kwargs: None)
    assert module.check_optional_ros_environment(module.TimeoutConfig.from_env()) == "SKIP"


@pytest.mark.parametrize(
    ("content", "expected_fragment"),
    [
        (
            f"{CONFLICT_OPEN_HEAD}\nours\n{CONFLICT_SEPARATOR}\ntheirs\n{CONFLICT_CLOSE_BRANCH}\n",
            "separator marker",
        ),
        (f"{CONFLICT_OPEN_BRANCH}\nonly ours\n", "incomplete conflict block"),
        (f"{CONFLICT_CLOSE_BRANCH}\n", "standalone closing marker"),
    ],
)
def test_merge_markers_are_detected(tmp_path, content, expected_fragment):
    module = load_module()
    repository_root = fake_repo_with_file(tmp_path, "example.txt", content)
    assert module.check_merge_markers(repository_root, module.TimeoutConfig.from_env()) is False
    issues = module.find_conflict_marker_issues(content)
    assert any(expected_fragment in issue for issue in issues)


def test_complete_conflict_block_reports_all_marker_forms():
    module = load_module()
    issues = module.find_conflict_marker_issues(
        f"{CONFLICT_OPEN_HEAD}\nours\n{CONFLICT_SEPARATOR}\ntheirs\n{CONFLICT_CLOSE_BRANCH}\n"
    )
    assert any(CONFLICT_OPEN_HEAD in issue for issue in issues)
    assert any(CONFLICT_SEPARATOR in issue for issue in issues)
    assert any(CONFLICT_CLOSE_BRANCH in issue for issue in issues)


def test_markdown_separators_are_accepted(tmp_path):
    module = load_module()
    repository_root = fake_repo_with_file(tmp_path, "README.md", "Title\n=======\nBody\n")
    assert module.check_merge_markers(repository_root, module.TimeoutConfig.from_env()) is True


def test_stale_reference_in_test_file_is_detected(tmp_path):
    module = load_module()
    repository_root = fake_repo_with_file(
        tmp_path,
        "test/example_test.py",
        f'VALUE = "{STALE_AUTOFOCUS}"\n',
    )
    assert module.check_stale_references(repository_root, module.TimeoutConfig.from_env()) is False


def test_placeholder_in_test_check_project_is_detected(tmp_path):
    module = load_module()
    repository_root = fake_repo_with_file(
        tmp_path,
        "test/test_check_project.py",
        f'MODEL = "{PLACEHOLDER_VALUE}"\n',
    )
    assert module.check_placeholder_models(repository_root, module.TimeoutConfig.from_env()) is False


def test_exact_self_reference_exclusion_is_allowed(tmp_path):
    module = load_module()
    repository_root = fake_repo_with_file(
        tmp_path,
        "tools/check_project.py",
        f'"{STALE_AUTOFOCUS}",\n',
    )
    assert module.check_stale_references(repository_root, module.TimeoutConfig.from_env()) is True


def test_external_gitlink_contents_are_not_traversed(monkeypatch, tmp_path):
    module = load_module()
    _, repository_root = init_workspace_repo(tmp_path)
    write_file(
        repository_root / module.EXTERNAL_GITLINK / "nested.txt",
        f"{CONFLICT_OPEN_HEAD}\n",
    )
    stage_all(repository_root)
    monkeypatch.setattr(
        module,
        "list_tracked_paths",
        lambda *_args, **_kwargs: [module.EXTERNAL_GITLINK],
    )
    assert module.check_merge_markers(repository_root, module.TimeoutConfig.from_env()) is True


def test_staged_gitlink_pointer_is_detected(tmp_path):
    module = load_module()
    _, repository_root = init_workspace_repo(tmp_path)
    write_file(repository_root / "tracked.txt", "ok\n")
    commit_all(repository_root)
    head = (
        subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        )
        .stdout.strip()
    )
    subprocess.run(
        [
            "git",
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{head},{module.EXTERNAL_GITLINK.as_posix()}",
        ],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert module.check_gitlink_not_staged(repository_root, module.TimeoutConfig.from_env()) is False


def test_dirty_tree_fails_without_allow_dirty(monkeypatch, tmp_path):
    module = load_module()
    _, repository_root = init_workspace_repo(tmp_path)
    write_file(repository_root / "tracked.txt", "baseline\n")
    commit_all(repository_root)
    write_file(repository_root / "tracked.txt", "modified\n")
    patch_quick_success(monkeypatch, module, repository_root)
    assert module.main(["--quick"]) == 1


def test_dirty_tree_passes_with_allow_dirty(monkeypatch, tmp_path):
    module = load_module()
    _, repository_root = init_workspace_repo(tmp_path)
    write_file(repository_root / "tracked.txt", "baseline\n")
    commit_all(repository_root)
    write_file(repository_root / "tracked.txt", "modified\n")
    patch_quick_success(monkeypatch, module, repository_root)
    assert module.main(["--quick", "--allow-dirty"]) == 0


def test_required_subprocess_failure_returns_nonzero(monkeypatch, tmp_path):
    module = load_module()
    workspace_root, repository_root = init_workspace_repo(tmp_path)
    patch_quick_success(monkeypatch, module, repository_root)
    monkeypatch.setattr(
        module,
        "preflight_full_mode",
        lambda *_args, **_kwargs: (workspace_root, {"PATH": os.environ["PATH"]}),
    )
    monkeypatch.setattr(module, "check_colcon_build", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(module, "check_colcon_test", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        module, "check_colcon_test_result", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(module, "run_smoke_check", lambda *_args, **_kwargs: True)
    assert module.main(["--full"]) == 1


def test_print_timeout():
    res = run_tool("--print-timeout")
    assert res.returncode == 0
    assert "static_command: 30.0" in res.stdout
    assert "build: 1800.0" in res.stdout
    assert "test: 1800.0" in res.stdout
    assert "launch_startup: 90.0" in res.stdout
    assert "launch_shutdown: 10.0" in res.stdout
    assert "cleanup: 10.0" in res.stdout


def test_print_timeout_env(monkeypatch, capsys):
    module = load_module()
    monkeypatch.setenv("CHECK_PROJECT_TIMEOUT_STATIC", "45.0")
    monkeypatch.setenv("CHECK_PROJECT_TIMEOUT_BUILD", "120.0")
    assert module.main(["--print-timeout"]) == 0
    captured = capsys.readouterr()
    assert "static_command: 45.0" in captured.out
    assert "build: 120.0" in captured.out
    assert "test: 1800.0" in captured.out
