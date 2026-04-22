"""Unit tests for callback parameter helper methods."""

from __future__ import annotations

from pathlib import Path
import sys
import types

import pytest


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camera_nodes", ROOT / "promoc_core"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

if "cv2" not in sys.modules:
    sys.modules["cv2"] = types.SimpleNamespace()

from camera_nodes.services.base import CallbackBase  # noqa: E402


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


def _base(params: dict) -> CallbackBase:
    return CallbackBase(_Node(params), camera_driver=object())


def test_param_helpers_missing_and_none_defaults():
    base = _base({"foo.none": None})

    assert base._param_raw("foo.missing", 1) == 1
    assert base._param_raw("foo.none", 2) == 2
    assert base._param_float("foo.missing", 1.5) == pytest.approx(1.5)
    assert base._param_int("foo.missing", 3) == 3
    assert base._param_str("foo.missing", "abc") == "abc"
    assert base._param_bool("foo.missing", True) is True


def test_param_helpers_cast_and_fallback_behavior():
    base = _base(
        {
            "num.float": "2.5",
            "num.int": "7",
            "text": 42,
            "flag.true_text": "false",
            "invalid.float": "x",
            "invalid.int": "x",
        }
    )

    assert base._param_float("num.float", 0.0) == pytest.approx(2.5)
    assert base._param_int("num.int", 0) == 7
    assert base._param_str("text", "") == "42"
    # Keep legacy bool semantics (bool('false') -> True).
    assert base._param_bool("flag.true_text", False) is True
    assert base._param_float("invalid.float", 9.5) == pytest.approx(9.5)
    assert base._param_int("invalid.int", 11) == 11


def test_wait_for_new_image_requires_strictly_new_timestamp():
    base = _base({})
    samples = iter(
        [
            ("img_old", 5),
            ("img_old", 5),
            ("img_new", 6),
            ("img_new", 6),
        ]
    )

    base._get_latest_cv_image = lambda: next(samples)  # type: ignore[method-assign]
    img, ts = base._wait_for_new_image(last_timestamp=5, timeout=0.05)
    assert img == "img_new"
    assert ts == 6

