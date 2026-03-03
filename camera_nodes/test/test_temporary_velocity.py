"""Unit tests for temporary linear-axis velocity context manager."""

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

srv_mod = types.ModuleType("promoc_assembly_interfaces.srv")


class _SrvType:
    class Request:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)


srv_mod.GetVelocityParameters = _SrvType
srv_mod.SetVelocityParameters = _SrvType
sys.modules["promoc_assembly_interfaces.srv"] = srv_mod
if "promoc_assembly_interfaces" not in sys.modules:
    pkg_mod = types.ModuleType("promoc_assembly_interfaces")
    pkg_mod.srv = srv_mod
    sys.modules["promoc_assembly_interfaces"] = pkg_mod

from camera_nodes.handlers.axis_helpers import temporary_velocity  # noqa: E402
from promoc_core.promoc_exceptions import ServiceError  # noqa: E402


class _VelocityResponse:
    def __init__(self, success=True, min_velocity=0.1, acceleration=1.0, max_velocity=5.0):
        self.success = success
        self.min_velocity = min_velocity
        self.acceleration = acceleration
        self.max_velocity = max_velocity


class _GetClient:
    def __init__(self, response):
        self._response = response

    def call(self, _request):
        return self._response


class _SetClient:
    def __init__(self):
        self.calls = []

    def call(self, request):
        self.calls.append(request)
        return None


def test_temporary_velocity_sets_and_restores():
    set_client = _SetClient()
    clients = {
        "get_vel": _GetClient(_VelocityResponse(success=True, max_velocity=4.0)),
        "set_vel": set_client,
    }

    with temporary_velocity(clients, max_velocity=1.5):
        assert len(set_client.calls) == 1
        assert float(set_client.calls[0].max_velocity) == pytest.approx(1.5)

    assert len(set_client.calls) == 2
    assert float(set_client.calls[1].max_velocity) == pytest.approx(4.0)


def test_temporary_velocity_raises_when_backup_unavailable():
    clients = {
        "get_vel": _GetClient(_VelocityResponse(success=False)),
        "set_vel": _SetClient(),
    }

    with pytest.raises(ServiceError):
        with temporary_velocity(clients, max_velocity=1.0):
            pass

