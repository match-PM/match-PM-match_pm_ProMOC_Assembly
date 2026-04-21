"""Static contract checks for autofocus service and algorithm boundaries."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_autofocus_algorithm_exposes_runtime_entrypoints():
    content = (
        ROOT / "camera_nodes" / "camera_nodes" / "algorithms" / "autofocus.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "class MSPRAutofocus" in content
    assert "def start(" in content
    assert "def process_image(" in content
    assert "def _calculate_score(" in content
    assert "def __getattr__(name: str):" in content
    assert "'FourStepAutofocus': 'four_step'" in content


def test_autofocus_service_is_self_contained():
    handler_content = (
        ROOT / "camera_nodes" / "camera_nodes" / "services" / "autofocus.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "class AxisClientManager" in handler_content
    assert "class AutofocusRunner" in handler_content
    assert "from .fly_over import FlyOverDetector" in handler_content


def test_autofocus_runner_avoids_private_algorithm_field_access():
    runner_content = (
        ROOT / "camera_nodes" / "camera_nodes" / "services" / "autofocus.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "._measurements" not in runner_content
    assert "._calculate_score" not in runner_content
    assert "._best_measurement" not in runner_content
