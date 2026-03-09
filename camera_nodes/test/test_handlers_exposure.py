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

from camera_nodes.services.handlers.exposure import ExposureHandler  # noqa: E402


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
    handler = ExposureHandler(node=node, camera_driver=driver)
    response = handler.manual_set_exposure_callback(_Request(2500.0), _Response())

    assert response.success is True
    assert driver.calls == [2500.0]


def test_exposure_handler_marks_error_for_invalid_request():
    driver = _Driver()
    node = _Node({"exposure.settle_frames_after_set": 0})
    handler = ExposureHandler(node=node, camera_driver=driver)
    response = handler.manual_set_exposure_callback(_Request(0.0), _Response())

    assert response.success is False
    assert "positive" in response.status_message.lower()
