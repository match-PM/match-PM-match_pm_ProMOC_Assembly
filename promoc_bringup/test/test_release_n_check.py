"""Smoke tests for Release N+1 automation scripts."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def test_release_n_check_script_passes():
    script = ROOT / "promoc_bringup" / "scripts" / "release_n_check.py"
    result = subprocess.run(
        [sys.executable, str(script), "--quiet"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "failed" in result.stdout.lower()


def test_release_n_smoke_script_lists_hardware_path_only():
    script = ROOT / "promoc_bringup" / "scripts" / "release_n_smoke.py"
    result = subprocess.run(
        [sys.executable, str(script), "--mode", "all"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Release N smoke path: hardware" in result.stdout
