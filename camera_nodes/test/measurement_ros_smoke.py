"""Run explicitly with the built ROS environment; no discovery or hardware.

This is separate from the legacy pytest suites which intentionally stub ROS.
"""
from dataclasses import asdict
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace

from rclpy.serialization import serialize_message, deserialize_message
from rclpy.action import GoalResponse
from promoc_assembly_interfaces.msg import MeasurementCondition
from promoc_assembly_interfaces.action import StartMeasurement
from promoc_assembly_interfaces.srv import MoveAbsolute, GetPosition, MeasurementLease

from camera_nodes.measurement_plan import load_plan
from camera_nodes.measurement_simulation import SimulatedIO
from camera_nodes import measurement_runtime as runtime


def main():
    repo = Path(__file__).resolve().parents[2]
    parameter_node = SimpleNamespace(
        get_parameters_by_prefix=lambda prefix: {
            "plain": 42,
            "wrapped": SimpleNamespace(value="ok"),
        }
    )
    assert runtime.node_parameter_snapshot(parameter_node) == {
        "plain": 42,
        "wrapped": "ok",
    }
    position_io = runtime.MeasurementIO.__new__(runtime.MeasurementIO)
    position_calls = []
    def fake_axis_call(name, request, timeout=3.0, check=True):
        position_calls.append((name, timeout))
        if name == "get_operation_status":
            return SimpleNamespace(success=True, operation_status="idle")
        return SimpleNamespace(success=True, axis_position=12.5)
    position_io.call = fake_axis_call
    assert position_io.position() == 12.5
    assert position_calls == [
        ("get_operation_status", runtime.AXIS_READ_TIMEOUT_S),
        ("get_position", runtime.AXIS_READ_TIMEOUT_S),
    ]
    required_values = {
        "pixel_format": "Mono8", "exposure_time": 6000.0,
        "bin_h": 1, "bin_v": 1, "exposure_auto": "Off",
        "gain_auto": "Off", "width": 1920, "height": 1200,
        "offset_x": 0, "offset_y": 0, "gamma": 0.0,
    }
    readback_calls = []
    class TransientReadback:
        def read_capture_state(self, **kwargs):
            readback_calls.append(kwargs)
            if not kwargs:
                return {"values": required_values, "available_keys": required_values}
            key = kwargs["required_keys"][0]
            assert kwargs == {"required_keys": (key,), "query_groups": ((key,),)}
            expected = {"gain": 1.0, "gamma": 1.0}[key]
            return {"values": {key: expected}, "available_keys": {key}}
    warnings = []
    state_io = runtime.MeasurementIO.__new__(runtime.MeasurementIO)
    state_io.check = lambda: None
    state_io.axis_epoch = "axis-test"
    state_io.scientific_baseline = {"gamma": 1.0}
    state_io.node = SimpleNamespace(
        _format_controller=TransientReadback(),
        measurement_epoch="camera-test",
        _param_str=lambda name: {
            "camera.device_id": "ids-4110071724",
            "camera.profile_id": "test-profile",
        }[name],
        get_logger=lambda: SimpleNamespace(warning=warnings.append),
    )
    recovered_state = state_io.state()
    assert recovered_state["values"]["gain"] == 1.0
    assert readback_calls[1] == {
        "required_keys": ("gain",), "query_groups": (("gain",),)
    }
    assert readback_calls[2] == {
        "required_keys": ("gamma",), "query_groups": (("gamma",),)
    }
    assert warnings == [
        "Recovered transient camera readback for: gain",
        "Recovered transient camera readback for changed gamma: 0.0 -> 1.0",
    ]
    condition, source = load_plan(repo/"promoc_bringup/config/measurement_plans/pilot_simulation.yaml", "pilot-2x2")
    with tempfile.TemporaryDirectory(prefix="measurement_ros_smoke_") as directory:
        condition.output_root = directory
        msg = MeasurementCondition(**asdict(condition))
        decoded = deserialize_message(serialize_message(msg), MeasurementCondition)
        assert runtime.condition_from_message(decoded).fingerprint() == condition.fingerprint()
        assert MoveAbsolute.Request(axis_position=2.0,measurement_token="test").measurement_token == "test"
        assert GetPosition.Request(require_fresh=True).require_fresh
        assert MeasurementLease.Request(command="acquire",token="test").token == "test"
        logger = SimpleNamespace(error=print)
        node = SimpleNamespace(measurement_lock=threading.Lock(),get_logger=lambda:logger)
        action = runtime.MeasurementAction.__new__(runtime.MeasurementAction)
        action.node = node
        request = StartMeasurement.Goal(condition=msg, plan_source=source, setup_confirmed=True)
        assert action.goal(request) == GoalResponse.ACCEPT
        assert action.goal(request) == GoalResponse.REJECT
        phases, states = [], []
        goal = SimpleNamespace(request=request,is_cancel_requested=False,
            publish_feedback=lambda f: phases.append(f.phase), succeed=lambda:states.append("success"),
            abort=lambda:states.append("abort"), canceled=lambda:states.append("cancel"))
        original = runtime.MeasurementIO
        try:
            runtime.MeasurementIO = lambda node,canceled: SimulatedIO(condition)
            result = action.execute(goal)
        finally:
            runtime.MeasurementIO = original
        assert result.success and result.captured_frames == 4
        assert states == ["success"] and phases[-1] == "COMPLETE"
        assert not node.measurement_lock.locked()
        assert deserialize_message(serialize_message(result),StartMeasurement.Result).success
    print("ROS typed-message roundtrip + action goal/execution/exclusion smoke passed (no hardware)")


if __name__ == "__main__":
    main()
