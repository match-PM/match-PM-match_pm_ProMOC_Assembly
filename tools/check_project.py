#!/usr/bin/env python3
"""Project checks for ProMOC Assembly."""

import argparse
import ast
import os
import subprocess
import sys
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_GITLINK = "planar_motor_nodes/planar_motor_nodes/drivers/match_pm_xBot"

class Checker:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def run_check(self, name, check_fn):
        print(f"Running check: {name} ... ", end="", flush=True)
        try:
            result = check_fn()
            if result is True:
                print("\033[92mPASS\033[0m")
                self.passed += 1
            elif result == "SKIP":
                print("\033[93mSKIP\033[0m")
                self.skipped += 1
            else:
                print("\033[91mFAIL\033[0m")
                self.failed += 1
        except Exception as e:
            print("\033[91mFAIL\033[0m")
            print(f"  Error: {e}")
            self.failed += 1

def run_cmd(cmd, cwd=ROOT, check=True):
    res = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\nOutput:\n{res.stdout}\n{res.stderr}")
    return res

def check_branch():
    res = run_cmd("git branch --show-current", check=False)
    if res.returncode == 0 and res.stdout.strip() == "cs_development":
        return True
    print(f"  Current branch is not cs_development: {res.stdout.strip()}")
    return False

def check_git_status():
    res = run_cmd("git status --ignore-submodules=all --short")
    if res.stdout.strip() != "":
        print(f"  Working tree not clean:\n{res.stdout}")
        return False
    return True

def check_merge_markers():
    res = run_cmd(f"git grep -n '<<<<<<< 'HEAD || true")
    if res.stdout.strip():
        print(f"  Merge markers found:\n{res.stdout}")
        return False
    return True

def check_agent_local_not_tracked():
    res = run_cmd("git ls-files .agent-local/ || true")
    if res.stdout.strip():
        print(f"  .agent-local/ files are tracked:\n{res.stdout}")
        return False
    return True

def check_gitlink_not_staged():
    res = run_cmd("git diff --cached --name-only")
    if EXTERNAL_GITLINK in res.stdout:
        print(f"  External gitlink is staged: {EXTERNAL_GITLINK}")
        return False
    return True

def check_generated_dirs():
    res = run_cmd("git ls-files build/ install/ log/ || true")
    if res.stdout.strip():
        print(f"  Generated dirs are tracked:\n{res.stdout}")
        return False
    return True

def check_python_syntax():
    files = run_cmd("git ls-files '*.py'").stdout.splitlines()
    for f in files:
        if EXTERNAL_GITLINK in f:
            continue
        try:
            ast.parse((ROOT / f).read_text(encoding="utf-8"))
        except SyntaxError as e:
            print(f"  Syntax error in {f}: {e}")
            return False
    return True

def check_yaml_parsing():
    files = run_cmd("git ls-files '*.yaml'").stdout.splitlines()
    for f in files:
        try:
            yaml.safe_load((ROOT / f).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  YAML parsing error in {f}: {e}")
            return False
    return True

def check_package_yaml_files_exist():
    expected = [
        "camera_nodes/config/camera.yaml",
        "linear_axis_nodes/config/x_axis.yaml",
        "linear_axis_nodes/config/z_axis.yaml",
        "planar_motor_nodes/config/planar_motor.yaml",
        "promoc_bringup/config/system.yaml",
        "promoc_core/config/system_controller.yaml",
    ]
    for f in expected:
        if not (ROOT / f).exists():
            print(f"  Missing required config: {f}")
            return False
    return True

def check_stale_references():
    needles = ["/promoc/camera/autofocus", "/promoc/camera/set_exposure", "services.autofocus", "services.exposure", "camera_simulator", "pm_genicam_controller", "sim_mode"]
    files = run_cmd("git ls-files '*.py'").stdout.splitlines()
    for f in files:
        if EXTERNAL_GITLINK in f or f.startswith("test/") or "/test/" in f or f.endswith("_test.py") or "check" in f:
            continue
        content = (ROOT / f).read_text(encoding="utf-8", errors="ignore")
        for n in needles:
            if n in content:
                print(f"  Stale reference '{n}' in {f}")
                return False
    return True

def check_placeholder_models():
    target = "MODEL_" + "PLACEHOLDER"
    files = run_cmd("git ls-files").stdout.splitlines()
    for f in files:
        if EXTERNAL_GITLINK in f or ".agent-local" in f or "check_project" in f:
            continue
        content = (ROOT / f).read_text(encoding="utf-8", errors="ignore")
        if target in content:
            print(f"  Unresolved placeholder in {f}")
            return False
    return True

def is_ros_available():
    return "ROS_DISTRO" in os.environ and os.environ["ROS_DISTRO"] == "lyrical"

def check_colcon_build():
    if not is_ros_available():
        print("  ROS Lyrical unavailable")
        return "SKIP"
    res = run_cmd("colcon build --symlink-install", check=False)
    if res.returncode != 0:
        print(f"  colcon build failed:\n{res.stderr}\n{res.stdout}")
        return False
    return True

def check_colcon_test():
    if not is_ros_available():
        return "SKIP"
    res = run_cmd("colcon test", check=False)
    if res.returncode != 0:
        print(f"  colcon test failed:\n{res.stderr}\n{res.stdout}")
        return False
    return True

def check_colcon_test_result():
    if not is_ros_available():
        return "SKIP"
    res = run_cmd("colcon test-result --verbose", check=False)
    if res.returncode != 0:
        print(f"  colcon test-result failed:\n{res.stdout}")
        return False
    return True

def check_mock_smoke():
    if not is_ros_available():
        return "SKIP"
    
    script = """
import os
import signal
import subprocess
import time

p = subprocess.Popen(["bash", "-c", "source /opt/ros/lyrical/setup.bash && source install/setup.bash && ros2 launch promoc_bringup system.launch.py driver_mode:=mock"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)

try:
    expected_nodes = ["camera_node", "lts300_x_axis", "lts300_z_axis", "mover", "system_controller"]
    expected_topics = ["/promoc/camera/image_raw", "/promoc/camera/status", "/promoc/status"]
    expected_services = ["/promoc/stop_all", "/promoc/reset_stop"]
    
    success = False
    for _ in range(30):
        time.sleep(1)
        nodes = subprocess.run(["ros2", "node", "list"], capture_output=True, text=True).stdout
        topics = subprocess.run(["ros2", "topic", "list"], capture_output=True, text=True).stdout
        services = subprocess.run(["ros2", "service", "list"], capture_output=True, text=True).stdout
        
        if all(n in nodes for n in expected_nodes) and all(t in topics for t in expected_topics) and all(s in services for s in expected_services):
            success = True
            break

    if not success:
        out = p.stdout.read() if p.stdout else ""
        print(f"Missing some nodes/topics/services.\\nNodes:\\n{nodes}\\nTopics:\\n{topics}\\nServices:\\n{services}\\nLaunch output:\\n{out}")
        os.killpg(p.pid, signal.SIGINT)
        exit(1)
finally:
    os.killpg(p.pid, signal.SIGINT)
    try:
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
"""
    res = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"  Smoke test failed: {res.stdout}")
        return False
    return True


def check_partial_mock_smoke():
    if not is_ros_available():
        return "SKIP"
    
    script = """
import os
import signal
import subprocess
import time

p = subprocess.Popen(["bash", "-c", "source /opt/ros/lyrical/setup.bash && source install/setup.bash && ros2 launch promoc_bringup system.launch.py driver_mode:=mock camera:=false planar_motor:=false"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)

try:
    success = False
    for _ in range(20):
        time.sleep(1)
        nodes = subprocess.run(["ros2", "node", "list"], capture_output=True, text=True).stdout
        if "lts300_x_axis" in nodes and "system_controller" in nodes:
            success = True
            break

    if not success:
        out = p.stdout.read() if p.stdout else ""
        print(f"Expected nodes missing:\\n{nodes}\\nLaunch output:\\n{out}")
        os.killpg(p.pid, signal.SIGINT)
        exit(1)
        
    if "camera_node" in nodes or "mover" in nodes:
        out = p.stdout.read() if p.stdout else ""
        print(f"Disabled nodes are running:\\n{nodes}\\nLaunch output:\\n{out}")
        os.killpg(p.pid, signal.SIGINT)
        exit(1)

finally:
    os.killpg(p.pid, signal.SIGINT)
    try:
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
"""
    res = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"  Partial smoke test failed: {res.stdout}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="ProMOC Project Checker")
    parser.add_argument("--quick", action="store_true", help="Run quick checks")
    parser.add_argument("--full", action="store_true", help="Run full checks")
    parser.add_argument("--allow-dirty", action="store_true", help="Do not require a clean working tree")
    args = parser.parse_args()

    if not args.quick and not args.full:
        parser.print_help()
        sys.exit(0)

    checker = Checker()

    # Quick checks
    checker.run_check("Branch cs_development", check_branch)
    if not args.allow_dirty:
        checker.run_check("Git status clean", check_git_status)
    checker.run_check("No merge markers", check_merge_markers)
    checker.run_check(".agent-local not tracked", check_agent_local_not_tracked)
    checker.run_check("Gitlink not staged", check_gitlink_not_staged)
    checker.run_check("Generated dirs not tracked", check_generated_dirs)
    checker.run_check("Python syntax", check_python_syntax)
    checker.run_check("YAML parsing", check_yaml_parsing)
    checker.run_check("Package YAMLs exist", check_package_yaml_files_exist)
    checker.run_check("No stale references", check_stale_references)
    checker.run_check("No placeholder models", check_placeholder_models)

    # Full checks
    if args.full:
        checker.run_check("colcon build", check_colcon_build)
        checker.run_check("colcon test", check_colcon_test)
        checker.run_check("colcon test-result", check_colcon_test_result)
        checker.run_check("Full mock smoke", check_mock_smoke)
        checker.run_check("Partial mock smoke", check_partial_mock_smoke)

    print(f"\\nSummary: {checker.passed} passed, {checker.skipped} skipped, {checker.failed} failed.")
    if checker.failed > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
