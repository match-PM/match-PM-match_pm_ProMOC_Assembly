# ruff: noqa: E402
"""Focused regression checks for the unified node implementation."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_node_uses_shared_controller_and_multithreaded_executor():
    content = (
        ROOT / "linear_axis_nodes" / "linear_axis_nodes" / "node.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "class AxisController" in content
    assert "MultiThreadedExecutor(num_threads=3)" in content
    assert "ReentrantCallbackGroup()" in content
    assert "MutuallyExclusiveCallbackGroup()" in content


def test_node_keeps_public_service_names_and_removes_cross_axis_logic():
    content = (
        ROOT / "linear_axis_nodes" / "linear_axis_nodes" / "node.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert 'f"{self._base_topic}/move_absolute"' in content
    assert 'f"{self._base_topic}/move_relative"' in content
    assert 'f"{self._base_topic}/home"' in content
    assert 'f"{self._base_topic}/jog_axis"' in content
    assert 'f"{self._base_topic}/stop"' in content
    assert "other_axis_position" not in content
    assert "collision_threshold" not in content


def test_shutdown_no_longer_moves_or_homes_axis():
    content = (
        ROOT / "linear_axis_nodes" / "linear_axis_nodes" / "node.py"
    ).read_text(encoding="utf-8", errors="ignore")

    assert "move_absolute(15.0)" not in content
    assert "driver.home()" not in content
    assert "self.controller.shutdown()" in content
