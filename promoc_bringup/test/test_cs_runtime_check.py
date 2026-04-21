"""Smoke tests for CS runtime automation scripts."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def test_cs_runtime_check_script_passes():
    script = ROOT / "promoc_bringup" / "scripts" / "cs_runtime_check.py"
    result = subprocess.run(
        [sys.executable, str(script), "--quiet"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "failed" in result.stdout.lower() or "summary" in result.stdout.lower()


def test_cs_runtime_smoke_script_lists_sim_and_hardware_paths():
    script = ROOT / "promoc_bringup" / "scripts" / "cs_runtime_smoke.py"
    result = subprocess.run(
        [sys.executable, str(script), "--mode", "all"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CS runtime smoke path: sim" in result.stdout
    assert "CS runtime smoke path: hardware" in result.stdout
