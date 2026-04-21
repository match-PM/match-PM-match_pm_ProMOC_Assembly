"""Static checks for canonical mover namespace wiring."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_system_launch_uses_promoc_mover_name():
    content = (ROOT / "promoc_bringup" / "launch" / "system.launch.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert 'package="planar_motor_nodes"' in content
    assert 'name="mover"' in content
    assert 'namespace="promoc"' in content
