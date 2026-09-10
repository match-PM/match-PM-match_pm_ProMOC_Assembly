"""Smoke tests for exposure handler wiring."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camera_nodes", ROOT / "promoc_core"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

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


class _AutoExposureRequest:
    def __init__(self, **overrides):
        self.roi_x = 0
        self.roi_y = 0
        self.roi_width = 0
        self.roi_height = 0
        self.target_level_fraction = 0.0
        self.tolerance_fraction = 0.0
        self.max_iterations = 0
        self.frames_per_iteration = 0
        for name, value in overrides.items():
            setattr(self, name, value)


class _AutoExposureResponse(_Response):
    def __init__(self):
        super().__init__()
        self.exposure_time = 0.0
        self.iterations = 0
        self.measured_level_fraction = 0.0
        self.saturated_fraction = 0.0
        self.native_max_value = 0.0


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


def test_exposure_handler_reports_failure_after_restoring_configured_default():
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

    assert response.success is False
    assert node._format_controller.calls == [12000.0, 30000.0]
    assert "restored configured start exposure" in response.status_message
    assert "write failed" in response.status_message


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


def test_auto_exposure_resolves_native_12_bit_range_from_pixel_format():
    image = np.full((8, 8), 3071, dtype=np.uint16)

    level, saturated, native_max = ExposureHandler._measure_level(
        [image],
        None,
        pixel_format="BayerRG12",
        percentile=95.0,
        saturation_threshold_fraction=0.98,
    )

    assert native_max == 4095.0
    assert level == 3071.0 / 4095.0
    assert saturated == 0.0


def test_auto_exposure_detects_left_aligned_12_bit_values_in_uint16():
    image = np.full((8, 8), 3071 << 4, dtype=np.uint16)

    level, saturated, native_max = ExposureHandler._measure_level(
        [image],
        None,
        pixel_format="BayerRG12",
        percentile=95.0,
        saturation_threshold_fraction=0.98,
    )

    assert native_max == float(4095 << 4)
    assert level == float(3071 << 4) / float(4095 << 4)
    assert saturated == 0.0


def test_auto_exposure_bayer_roi_uses_only_rggb_green_sensels():
    image = np.zeros((4, 4), dtype=np.uint16)
    image[0::2, 0::2] = 4095  # red
    image[1::2, 1::2] = 4095  # blue
    image[0::2, 1::2] = 2048  # green 1
    image[1::2, 0::2] = 2048  # green 2

    values = ExposureHandler._analysis_values(
        image,
        None,
        pixel_format="BayerRG12",
    )

    assert values.size == 8
    assert np.all(values == 2048)


def test_auto_exposure_converges_after_two_stable_raw_measurements(monkeypatch):
    node = _Node(
        {
            "auto_exposure.stable_iterations": 2,
            "auto_exposure.frames_per_iteration": 1,
            "auto_exposure.max_iterations": 4,
            "auto_exposure.settle_frames_after_set": 0,
            "camera.min_exposure_us": 53.0,
            "camera.max_exposure_us": 814000.0,
        }
    )
    handler = ExposureHandler(node=node, camera_driver=_Driver())
    frame = np.full((16, 16), 2867, dtype=np.uint16)
    timestamps = iter((1, 2))

    monkeypatch.setattr(handler, "_capture_state", lambda: ("BayerRG12", 5000.0))
    monkeypatch.setattr(handler, "_get_latest_image_timestamp_ns", lambda: 0)
    monkeypatch.setattr(
        handler,
        "_collect_raw_frames",
        lambda _count, _timestamp, _timeout: ([frame], next(timestamps)),
    )

    response = handler.auto_exposure_callback(
        _AutoExposureRequest(),
        _AutoExposureResponse(),
    )

    assert response.success is True
    assert response.exposure_time == 5000.0
    assert response.iterations == 2
    assert response.native_max_value == 4095.0
    assert abs(response.measured_level_fraction - 0.70) < 0.01
    assert response.white_level == 2867.0
    assert response.black_level == 2867.0
    assert response.p95 == 2867.0
    assert response.p99_9 == 2867.0
    assert response.intensity_method == "p95_fallback"
    assert response.clipping_detected is False


def test_auto_exposure_adjusts_exposure_and_uses_applied_readback(monkeypatch):
    node = _Node(
        {
            "auto_exposure.stable_iterations": 1,
            "auto_exposure.frames_per_iteration": 1,
            "auto_exposure.max_iterations": 3,
            "auto_exposure.settle_frames_after_set": 0,
            "camera.min_exposure_us": 53.0,
            "camera.max_exposure_us": 814000.0,
        }
    )
    handler = ExposureHandler(node=node, camera_driver=_Driver())
    dark = np.full((16, 16), 1024, dtype=np.uint16)
    target = np.full((16, 16), 2867, dtype=np.uint16)
    frames = iter((dark, target))
    writes = []

    monkeypatch.setattr(handler, "_capture_state", lambda: ("BayerRG12", 1000.0))
    monkeypatch.setattr(handler, "_get_latest_image_timestamp_ns", lambda: 0)
    monkeypatch.setattr(
        handler,
        "_collect_raw_frames",
        lambda _count, timestamp, _timeout: ([next(frames)], timestamp + 1),
    )
    monkeypatch.setattr(
        handler,
        "_set_exposure_us",
        lambda requested: writes.append(float(requested))
        or {"success": True, "applied_exposure_us": float(requested)},
    )
    monkeypatch.setattr(
        handler,
        "_discard_raw_frames",
        lambda _count, timestamp, _timeout: timestamp,
    )

    response = handler.auto_exposure_callback(
        _AutoExposureRequest(),
        _AutoExposureResponse(),
    )

    assert response.success is True
    assert response.iterations == 2
    assert writes
    assert writes[0] > 1000.0
    assert response.exposure_time == writes[0]
