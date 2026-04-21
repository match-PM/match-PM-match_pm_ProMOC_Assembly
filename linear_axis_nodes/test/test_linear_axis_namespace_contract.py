"""Static checks for canonical linear-axis namespace wiring."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_system_launch_applies_linear_axis_namespace():
    content = (ROOT / "promoc_bringup" / "launch" / "system.launch.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert 'namespace="promoc/linear_axis"' in content
    assert '"namespace": "promoc/linear_axis"' in content


def test_optical_launch_applies_linear_axis_namespace():
    content = (
        ROOT / "promoc_bringup" / "launch" / "optical_measurement_system.launch.py"
    ).read_text(encoding="utf-8", errors="ignore")
    assert 'namespace="promoc/linear_axis"' in content
    assert '"namespace": "promoc/linear_axis"' in content
