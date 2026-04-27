"""Smoke tests for exposure handler wiring."""

from __future__ import annotations

from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camera_nodes", ROOT / "promoc_core"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

if "cv2" not in sys.modules:
    sys.modules["cv2"] = types.SimpleNamespace()

from camera_nodes.services.exposure import ExposureHandler  # noqa: E402


class _Param:
    def __init__(self, value):
        self.value = value


class _Logger:
    def info(self, *_args, **_kwargs):
        return None

    def warn(self, *_args, **_kwargs):
        return None

    def error(self, *_args, **_kwargs):
        return None


class _Node:
    def __init__(self, params: dict):
        self._params = dict(params)
        self._logger = _Logger()
        self._format_controller = None

    def has_parameter(self, name: str) -> bool:
        return name in self._params

    def get_parameter(self, name: str):
        return _Param(self._params[name])

    def get_logger(self):
        return self._logger


class _Driver:
    def __init__(self):
        self.calls = []

    def set_exposure(self, exposure_time):
        self.calls.append(float(exposure_time))
        return True


class _FormatController:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []
        self.current_exposure = None

    def set_live_exposure(self, exposure_time):
        self.calls.append(float(exposure_time))
        outcome = dict(self.outcomes.pop(0))
        if outcome.get("success"):
            self.current_exposure = float(
                outcome.get("applied_exposure_us", exposure_time)
            )
        return outcome

    def read_current_exposure_us(self):
        return self.current_exposure


class _Request:
    def __init__(self, exposure_time):
        self.exposure_time = exposure_time


class _Response:
    def __init__(self):
        self.success = False
        self.status_message = ""


def test_exposure_handler_sets_exposure_on_valid_request():
    driver = _Driver()
    node = _Node(
        {"exposure.settle_frames_after_set": 0, "exposure.frame_timeout_s": 0.1}
    )
    node._format_controller = _FormatController(
        [{"success": True, "applied_exposure_us": 2500.0}]
    )
    handler = ExposureHandler(node=node, camera_driver=driver)
    response = handler.manual_set_exposure_callback(_Request(2500.0), _Response())

    assert response.success is True
    assert driver.calls == []
    assert node._format_controller.calls == [2500.0]
    assert "2500.0 us" in response.status_message
    assert "2.500 ms" in response.status_message


def test_exposure_handler_marks_error_for_invalid_request():
    driver = _Driver()
    node = _Node({"exposure.settle_frames_after_set": 0})
    handler = ExposureHandler(node=node, camera_driver=driver)
    response = handler.manual_set_exposure_callback(_Request(0.0), _Response())

    assert response.success is False
    assert "positive" in response.status_message.lower()


def test_exposure_handler_restores_configured_default_when_live_write_fails():
    driver = _Driver()
    node = _Node(
        {
            "exposure.settle_frames_after_set": 0,
            "camera.default_exposure_us": 30000.0,
        }
    )
    node._format_controller = _FormatController(
        [
            {"success": False, "reason": "write failed"},
            {"success": True, "applied_exposure_us": 30000.0},
        ]
    )
    handler = ExposureHandler(node=node, camera_driver=driver)

    response = handler.manual_set_exposure_callback(_Request(12000.0), _Response())

    assert response.success is True
    assert node._format_controller.calls == [12000.0, 30000.0]
    assert "restored configured start exposure" in response.status_message
    assert "30000.0 us" in response.status_message


def test_exposure_handler_clamps_to_camera_minimum_for_live_write():
    driver = _Driver()
    node = _Node(
        {
            "exposure.settle_frames_after_set": 0,
            "camera.min_exposure_us": 53.0,
            "camera.max_exposure_us": 814000.0,
        }
    )
    node._format_controller = _FormatController(
        [{"success": True, "applied_exposure_us": 53.0}]
    )
    handler = ExposureHandler(node=node, camera_driver=driver)

    response = handler.manual_set_exposure_callback(_Request(30.0), _Response())

    assert response.success is True
    assert node._format_controller.calls == [53.0]
    assert "clamped" in response.status_message.lower()
    assert "30.0 us" in response.status_message
    assert "53.0 us" in response.status_message


def test_exposure_handler_reports_error_when_target_and_fallback_fail():
    driver = _Driver()
    node = _Node(
        {
            "exposure.settle_frames_after_set": 0,
            "camera.default_exposure_us": 30000.0,
        }
    )
    node._format_controller = _FormatController(
        [
            {"success": False, "reason": "target mismatch"},
            {"success": False, "reason": "fallback mismatch"},
        ]
    )
    handler = ExposureHandler(node=node, camera_driver=driver)

    response = handler.manual_set_exposure_callback(_Request(12000.0), _Response())

    assert response.success is False
    assert "fallback" in response.status_message.lower()
