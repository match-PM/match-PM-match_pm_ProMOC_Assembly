"""Validate/list plans offline or execute one confirmed condition via an Action."""
from dataclasses import asdict
import argparse
import json
from pathlib import Path
import time

import yaml

from .measurement_plan import Condition, load_plan


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--condition")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--validate", action="store_true", help="No ROS connection or hardware commands")
    parser.add_argument("--set", action="append", default=[], metavar="FIELD=VALUE")
    parser.add_argument("--resume", default="", metavar="RUN_ID")
    parser.add_argument("--confirm-setup", action="store_true", help="Confirm physical setup, camera serial, homing and safe travel")
    parser.add_argument("--simulate", action="store_true", help="Synthetic data only, separate -simulation campaign")
    args = parser.parse_args(argv)
    try:
        if args.list:
            plan, _ = load_plan(args.plan)
            for c in plan["conditions"]:
                print(f"{c['condition_id']}: {c.get('experiment_id','')} | "
                      f"{c.get('objective_id','')} | {c.get('component_id','')} | {c.get('target_position','')}")
            return 0
        if not args.condition:
            parser.error("--condition is required unless --list is used")
        overrides = {}
        for assignment in args.set:
            name, value = assignment.split("=",1)
            overrides[name] = yaml.safe_load(value)
        condition, source = load_plan(args.plan, args.condition, overrides)
        if args.resume:
            # Resume uses the stored pixel ROI, never a new interactive selection.
            resume_path = Path(condition.output_root)/condition.campaign_id/"runs"/args.resume
            if Path(args.resume).name != args.resume:
                raise ValueError("--resume accepts a run basename, not a path")
            saved = yaml.safe_load((resume_path/"resolved_condition.yaml").read_text())
            if condition.roi_width == condition.roi_height == 0:
                for key in ("roi_x", "roi_y", "roi_width", "roi_height"):
                    setattr(condition, key, saved[key])
            if condition.fingerprint() != saved["condition_hash"]:
                raise ValueError("Resume config differs from stored run")
        print(yaml.safe_dump(asdict(condition), sort_keys=False))
        if args.validate:
            print("Plan valid. Physical setup, raw stream/readbacks and ROI geometry require runtime preflight.")
            return 0
        if args.simulate:
            if args.resume:
                raise ValueError("Simulation CLI uses fresh runs; resume is covered by deterministic tests")
            from .measurement_simulation import run_simulation
            print(json.dumps(run_simulation(condition, source), indent=2))
            return 0
        if not args.confirm_setup:
            raise ValueError("Inspect the setup card and use --confirm-setup only after physical checks")
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.error(str(exc))

    # Import ROS only for an actual run; --validate works on a normal Python host.
    import rclpy
    from rclpy.action import ActionClient
    from rclpy.node import Node
    from promoc_assembly_interfaces.action import StartMeasurement
    from promoc_assembly_interfaces.msg import MeasurementCondition
    from promoc_assembly_interfaces.srv import GetRoiCoordinates

    rclpy.init()
    node = Node("measurement_runner")
    goal = None
    try:
        if not condition.roi_width and not args.resume:
            client = node.create_client(GetRoiCoordinates, "/promoc/camera/get_roi_coordinates")
            if not client.wait_for_service(timeout_sec=5):
                raise RuntimeError("ROI service unavailable")
            future = client.call_async(GetRoiCoordinates.Request(
                window_name="Select search ROI around the COMPLETE cube face (all 4 edges)"
            ))
            rclpy.spin_until_future_complete(node, future, timeout_sec=300)
            response = future.result() if future.done() else None
            if response is None or not response.success:
                raise RuntimeError("ROI selection failed or timed out")
            for key in ("roi_x", "roi_y", "roi_width", "roi_height"):
                setattr(condition, key, getattr(response, key))
        condition.validate()
        client = ActionClient(node, StartMeasurement, "/promoc/camera/start_measurement")
        if not client.wait_for_server(timeout_sec=5):
            raise RuntimeError("StartMeasurement action unavailable")
        payload = asdict(condition)
        for key, value in payload.items():
            if Condition.__dataclass_fields__[key].type == "float":
                payload[key] = float(value)
        request = StartMeasurement.Goal(condition=MeasurementCondition(**payload), plan_source=source,
                                       resume_run_id=args.resume, setup_confirmed=True)
        sent = client.send_goal_async(request, feedback_callback=lambda msg: print(msg.feedback.status_message, flush=True))
        rclpy.spin_until_future_complete(node, sent, timeout_sec=10)
        if not sent.done():
            raise RuntimeError("Goal acceptance timeout: check server state; DO NOT blindly submit again")
        goal = sent.result()
        if not goal.accepted:
            raise RuntimeError("Goal rejected; inspect server log and active operation")
        future = goal.get_result_async()
        try:
            while not future.done():
                rclpy.spin_once(node, timeout_sec=0.2)
        except KeyboardInterrupt:
            print("Cancellation requested; waiting for controlled shutdown…", flush=True)
            cancel = goal.cancel_goal_async()
            deadline = time.monotonic()+45
            while not future.done() and time.monotonic() < deadline:
                rclpy.spin_once(node, timeout_sec=0.2)
            if not future.done():
                raise RuntimeError("Cancellation unconfirmed: use axis stop/emergency_stop and inspect server")
        result = future.result().result
        print(result)
        if not result.success:
            raise RuntimeError(f"{result.error_code}: {result.status_message}; data: {result.output_directory}")
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
