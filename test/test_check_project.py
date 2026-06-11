#!/usr/bin/env python3
"""Tests for the check_project tool."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "check_project.py"

def run_tool(*args):
    return subprocess.run(
        [sys.executable, str(TOOL_PATH)] + list(args),
        cwd=ROOT,
        capture_output=True,
        text=True
    )

def test_help_output():
    res = run_tool("--help")
    assert res.returncode == 0
    assert "--quick" in res.stdout
    assert "--full" in res.stdout

def test_quick_mode_passes():
    res = run_tool("--quick", "--allow-dirty")
    assert res.returncode == 0, f"Quick mode failed: {res.stdout} {res.stderr}"
    assert "Branch cs_development ... \033[92mPASS\033[0m" in res.stdout
    assert "Summary:" in res.stdout

def test_missing_required_arguments():
    res = run_tool()
    assert res.returncode == 0
    assert "usage:" in res.stdout.lower()

if __name__ == "__main__":
    test_help_output()
    test_quick_mode_passes()
    test_missing_required_arguments()
    print("All tests passed!")
