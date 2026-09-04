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
