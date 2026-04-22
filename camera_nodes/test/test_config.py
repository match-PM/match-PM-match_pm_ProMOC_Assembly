"""Unit tests for camera config."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
path_str = str(ROOT / "camera_nodes")
if path_str not in sys.path:
    sys.path.insert(0, path_str)

from camera_nodes.config import (  # noqa: E402
    declare_camera_parameters,
    load_camera_runtime_config,
)


class _Param:
    def __init__(self, value):
        self.value = value


class _Node:
    def __init__(self):
        self._params = {}
        self.warnings = []

    def declare_parameter(self, name, default):
        self._params.setdefault(name, default)

    def has_parameter(self, name):
        return name in self._params

    def get_parameter(self, name):
        return _Param(self._params[name])

    def get_logger(self):
        return self

    def warning(self, message):
        self.warnings.append(message)


def test_declare_and_load_runtime_config():
    node = _Node()
    declare_camera_parameters(node)

    # Override a couple of values to verify typed parsing.
    node._params["use_simulator"] = True
    node._params["x_axis_node_name"] = "lts300_z_axis"
    node._params["pixel_size_um"] = 3.45
<<<<<<< HEAD
=======
    node._params["mtf.profile"] = "debug"
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0

    cfg = load_camera_runtime_config(node)
    assert cfg.core.use_simulator is True
    assert cfg.core.x_axis_node_name == "lts300_z_axis"
    assert cfg.core.pixel_size_um == 3.45
<<<<<<< HEAD
    assert cfg.exposure.frame_timeout_s == 1.0


def test_mtf_parameters_removed():
    node = _Node()
    declare_camera_parameters(node)
    assert "mtf.profile" not in node._params
=======
    assert cfg.mtf.profile == "debug"


def test_deprecated_parameter_removed():
    node = _Node()
    declare_camera_parameters(node)
    assert "mtf_csv_path" not in node._params
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
