"""ROS binding for StartMeasurement; shares the camera node's exclusive lock."""
from dataclasses import asdict, fields
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import time
import uuid

import cv2
import numpy as np
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from promoc_assembly_interfaces.action import StartMeasurement
from promoc_assembly_interfaces.srv import GetPosition, GetOperationStatus, MoveAbsolute, Stop, MeasurementLease

from .measurement_engine import MeasurementEngine, MeasurementError, FrameTimeout, Cancelled
from .measurement_plan import Condition
from .intensity import aggregate_intensity, measure_intensity
from .measurement_processing import ProcessingStateError, verify_processing_state


AXIS = "/promoc/linear_axis/lts300_x_axis"
AXIS_READ_TIMEOUT_S = 10.0
CAMERA_READBACK_RETRIES = 2
CAMERA_READBACK_RETRY_DELAY_S = 0.1


def node_parameter_snapshot(node):
    """Return declared node parameters on ROS 2 versions without list_parameters()."""
    parameters = node.get_parameters_by_prefix("")
    return {
        name: value.value if hasattr(value, "value") else value
        for name, value in parameters.items()
    }


def condition_from_message(msg):
    return Condition(**{f.name: getattr(msg, f.name) for f in fields(Condition)})


class MeasurementIO:
    def __init__(self, node, canceled):
        self.node, self.canceled = node, canceled
        self.token = ""
        self.lease_failed = False
        self.lease_timer = None
        self.axis_epoch = ""
        self.last_move = None
        self.clients = {name: node.create_client(kind, f"{AXIS}/{name}", callback_group=node.cb_group)
                        for name, kind in (("get_position", GetPosition), ("get_operation_status", GetOperationStatus),
                                           ("move_absolute", MoveAbsolute), ("stop", Stop),
                                           ("measurement_lease", MeasurementLease))}

    def check(self):
        if self.canceled():
            raise Cancelled()
        if self.lease_failed:
            raise MeasurementError("LEASE_LOST", "Axis reservation heartbeat failed")

    def call(self, name, request, timeout=3.0, check=True):
        client = self.clients[name]
        if not client.wait_for_service(timeout_sec=0.5):
            raise MeasurementError("SERVICE_UNAVAILABLE", name)
        future = client.call_async(request)
        deadline = time.monotonic()+timeout
        while not future.done():
            if check:
                self.check()
            if time.monotonic() >= deadline:
                # A timed-out motion may still execute: caller stops, never retries it.
                raise MeasurementError("SERVICE_TIMEOUT", name)
            time.sleep(0.01)
        response = future.result()
        if response is None or not response.success:
            raise MeasurementError("SERVICE_FAILED", f"{name}: {getattr(response, 'status_message', '')}")
        return response

    def acquire(self, token):
        response = self.call("measurement_lease", MeasurementLease.Request(command="acquire", token=token))
        self.token, self.axis_epoch = token, response.axis_epoch
        self.lease_timer = self.node.create_timer(5.0, self.heartbeat, callback_group=self.node.cb_group)

    def heartbeat(self):
        try:
            response = self.call("measurement_lease", MeasurementLease.Request(command="renew", token=self.token), check=False)
            if response.axis_epoch != self.axis_epoch:
                self.lease_failed = True
        except Exception:
            self.lease_failed = True

    def release(self):
        if self.lease_timer:
            self.node.destroy_timer(self.lease_timer)
        try:
            if self.token:
                # Never clear a latched emergency stop during cleanup.
                status = self.call("get_operation_status", GetOperationStatus.Request(), check=False).operation_status
                if status not in ("idle", "error", "emergency_stop"):
                    self.call("stop", Stop.Request(), check=False)
                self.call("measurement_lease", MeasurementLease.Request(command="release", token=self.token), check=False)
        finally:
            for client in self.clients.values():
                self.node.destroy_client(client)

    def position(self):
        status = self.call(
            "get_operation_status",
            GetOperationStatus.Request(),
            timeout=AXIS_READ_TIMEOUT_S,
        ).operation_status
        if status != "idle":
            raise MeasurementError("AXIS_NOT_IDLE", f"Axis reports {status}")
        return float(
            self.call(
                "get_position",
                GetPosition.Request(require_fresh=True),
                timeout=AXIS_READ_TIMEOUT_S,
            ).axis_position
        )

    def move(self, position, timeout, tolerance):
        self.check()
        self.call("move_absolute", MoveAbsolute.Request(axis_position=float(position), measurement_token=self.token))
        deadline = time.monotonic()+timeout
        stable = 0
        while time.monotonic() < deadline:
            self.check()
            status = self.call(
                "get_operation_status",
                GetOperationStatus.Request(),
                timeout=AXIS_READ_TIMEOUT_S,
            ).operation_status
            if status in ("error", "emergency_stop"):
                raise MeasurementError("AXIS_ERROR", status)
            if status == "idle":
                actual = self.position()
                stable = stable+1 if abs(actual-position) <= tolerance else 0
                if stable >= 3:
                    return actual
            else:
                stable = 0
            time.sleep(0.05)
        raise MeasurementError("MOVE_TIMEOUT", "Fresh position/idle confirmation failed")

    def latest_timestamp(self):
        return self.node.mtf_handler._get_latest_image_timestamp_ns()

    def frame(self, last_timestamp, timeout):
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            self.check()
            snapshot = getattr(self.node, "measurement_image_snapshot", None)
            if snapshot:
                msg, receipt_ns, receipt_monotonic_ns = snapshot
                timestamp = self.node.mtf_handler._msg_timestamp_ns(msg)
                if timestamp > last_timestamp:
                    image = self.node.bridge.imgmsg_to_cv2(msg, "passthrough").copy()
                    if msg.encoding != self.encoding or list(image.shape) != self.image_shape:
                        raise MeasurementError("STREAM_CHANGED", "Raw encoding/geometry changed")
                    return {"image": image, "source_timestamp_ns": timestamp,
                            "received_utc_ns": receipt_ns, "received_monotonic_ns": receipt_monotonic_ns,
                            "source_clock": "ROS_image_header_driver_defined", "encoding": msg.encoding}
            time.sleep(0.005)
        raise FrameTimeout()

    def state(self):
        self.check()
        state = self.node._format_controller.read_capture_state()
        if not state:
            raise MeasurementError("READBACK_UNAVAILABLE", "Camera parameter readback unavailable")
        values = dict(state["values"])
        unsupported = set(state.get("unsupported_keys", ()))
        required = {"pixel_format", "exposure_time", "gain", "bin_h", "bin_v", "exposure_auto", "gain_auto",
                    "width", "height", "offset_x", "offset_y"}
        available = set(state.get("available_keys", values))
        initially_missing = required-available
        for retry in range(CAMERA_READBACK_RETRIES):
            missing = required-available
            if not missing:
                break
            # Retry each absent value separately. The camera driver occasionally
            # returns an incomplete response for one parameter group; no cached or
            # configured value is substituted here, only fresh driver readback.
            for key in sorted(missing):
                supplement = self.node._format_controller.read_capture_state(
                    required_keys=(key,),
                    query_groups=((key,),),
                )
                if not supplement:
                    continue
                supplement_values = dict(supplement.get("values", {}))
                unsupported.update(supplement.get("unsupported_keys", ()))
                supplement_available = set(
                    supplement.get("available_keys", supplement_values)
                )
                if key in supplement_available and key in supplement_values:
                    values[key] = supplement_values[key]
                    available.add(key)
            if required-available and retry+1 < CAMERA_READBACK_RETRIES:
                time.sleep(CAMERA_READBACK_RETRY_DELAY_S)
        missing = required-available
        if missing:
            raise MeasurementError("READBACK_MISSING", f"Required keys missing: {missing}")
        if initially_missing:
            recovered = initially_missing & available
            if recovered:
                self.node.get_logger().warning(
                    "Recovered transient camera readback for: "
                    + ", ".join(sorted(recovered))
                )
        if not all(math.isfinite(float(values[k])) for k in ("exposure_time", "gain", "width", "height")):
            raise MeasurementError("READBACK_INVALID", "Nonfinite camera readback")
        for key, expected in getattr(self, "scientific_baseline", {}).items():
            if key == "exposure_time" or values.get(key) == expected:
                continue
            initial_actual = values.get(key)
            confirmed_actual = initial_actual
            recovered = False
            for retry in range(CAMERA_READBACK_RETRIES):
                supplement = self.node._format_controller.read_capture_state(
                    required_keys=(key,),
                    query_groups=((key,),),
                )
                if supplement:
                    supplement_values = dict(supplement.get("values", {}))
                    supplement_available = set(
                        supplement.get("available_keys", supplement_values)
                    )
                    if key in supplement_available and key in supplement_values:
                        confirmed_actual = supplement_values[key]
                        values[key] = confirmed_actual
                        available.add(key)
                        if confirmed_actual == expected:
                            recovered = True
                            break
                if retry+1 < CAMERA_READBACK_RETRIES:
                    time.sleep(CAMERA_READBACK_RETRY_DELAY_S)
            if recovered:
                self.node.get_logger().warning(
                    f"Recovered transient camera readback for changed {key}: "
                    f"{initial_actual!r} -> {confirmed_actual!r}"
                )
                continue
            raise MeasurementError(
                "CAMERA_CHANGED",
                f"Scientific setting {key} changed: expected {expected!r}, "
                f"confirmed readback {confirmed_actual!r}",
            )
        return {"values": values, "identity": {"camera_node_epoch": self.node.measurement_epoch,
                "axis_epoch": self.axis_epoch, "configured_guid": self.node._param_str("camera.device_id"),
                "profile": self.node._param_str("camera.profile_id")},
                "unsupported_keys": sorted(unsupported),
                "readback_source": "ROS_driver_parameter_services", "read_at_utc_ns": time.time_ns()}

    def preflight(self, condition):
        self.c = condition
        state = self.state()
        if state["identity"]["profile"] != condition.camera_profile:
            raise MeasurementError("CAMERA_PROFILE", "Launched camera profile differs from condition")
        if state["identity"]["configured_guid"].split("-")[-1] != condition.camera_serial:
            raise MeasurementError("CAMERA_IDENTITY", "Configured GUID differs from operator-confirmed camera serial")
        values = state["values"]
        unsupported = set(state.get("unsupported_keys", ()))
        self.pixel_format = str(values["pixel_format"])
        if not (self.pixel_format.startswith("Mono") or self.pixel_format.startswith("BayerRG")):
            raise MeasurementError("RAW_REQUIRED", "Expected Mono or Bayer RGGB scientific raw")
        if values["bin_h"] != 1 or values["bin_v"] != 1 or abs(float(values["gain"])-condition.expected_gain) > 1e-6:
            raise MeasurementError("CAPTURE_SETTINGS", "Binning/gain mismatch; configure before starting")
        try:
            accepted_unsupported = verify_processing_state(
                values, unsupported, self.pixel_format
            )
        except ProcessingStateError as exc:
            raise MeasurementError(exc.code, str(exc)) from exc
        if accepted_unsupported:
            self.node.get_logger().warning(
                "Scientific processing features verified unsupported by the camera driver: "
                + ", ".join(accepted_unsupported)
            )
        snapshot = getattr(self.node, "measurement_image_snapshot", None)
        if not snapshot:
            raise MeasurementError("NO_IMAGE", "Camera has no image")
        msg = snapshot[0]
        image = self.node.bridge.imgmsg_to_cv2(msg, "passthrough")
        self.encoding, self.image_shape = msg.encoding, list(image.shape)
        if image.ndim != 2 or not (msg.encoding.startswith("mono") or msg.encoding.startswith("bayer_rggb")):
            raise MeasurementError("RAW_REQUIRED", "Live image must be Mono or RGGB raw")
        if [int(values["height"]),int(values["width"])] != self.image_shape:
            raise MeasurementError("STREAM_GEOMETRY", "Readback size differs from live raw image")
        if self.pixel_format.startswith("Bayer") and (int(values["offset_x"])%2 or int(values["offset_y"])%2):
            raise MeasurementError("BAYER_ORIGIN", "RGGB workflow requires even sensor offsets")
        self.scientific_baseline = values.copy()
        if condition.roi_x+condition.roi_width > image.shape[1] or condition.roi_y+condition.roi_height > image.shape[0]:
            raise MeasurementError("ROI_BOUNDS", "ROI does not fit current raw image")
        self.position()
        self.frame(self.latest_timestamp(), condition.frame_timeout_s)
        result = {"camera": state, "camera_serial_source": "configured_guid_and_operator_confirmation",
                  "homed_source": "operator_confirmation", "roi": [condition.roi_x, condition.roi_y,
                  condition.roi_width, condition.roi_height], "image_shape": self.image_shape,
                  "encoding": self.encoding, "python_version": platform.python_version(),
                  "numpy_version": np.__version__, "opencv_version": getattr(cv2, "__version__", "unknown"),
                  "node_parameters": node_parameter_snapshot(self.node)}
        try:
            repo = Path(__file__).resolve().parents[2]
            def git(*args):
                return subprocess.check_output(["git", "-C", str(repo), *args], timeout=5, stderr=subprocess.DEVNULL).decode()
            diff = git("diff", "HEAD", "--", ".")
            result["git_commit"] = git("rev-parse", "HEAD").strip()
            result["git_status"] = git("status", "--short")
            result["git_diff"] = diff
            result["runtime_source_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in Path(__file__).parent.glob("measurement*.py")}
        except (OSError, subprocess.SubprocessError):
            result["git_commit"] = None
        return result

    def set_exposure(self, target):
        self.check()
        outcome = self.node.exposure_handler._set_exposure_us(float(target))
        if outcome.get("used_fallback"):
            raise MeasurementError("EXPOSURE_WRITE", "Exposure write fell back")
        actual = float(self.state()["values"]["exposure_time"])
        if abs(actual-target) > max(1.0, target*0.002):
            raise MeasurementError("EXPOSURE_READBACK", "Exposure readback outside tolerance")

    def levels(self, images, condition):
        roi = (condition.roi_x, condition.roi_y, condition.roi_width, condition.roi_height)
        result = aggregate_intensity([
            measure_intensity(
                image,
                roi,
                pixel_format=self.pixel_format,
                max_saturated_fraction=condition.max_saturated_fraction,
            )
            for image in images
        ])
        # Legacy aliases keep the state machine and older manifests readable.
        result["bright_fraction"] = result["white_level_norm"]
        result["dark_fraction"] = result["black_level_norm"]
        result["saturated_fraction"] = result["saturation_fraction"]
        return result

    def focus_score(self, image, condition):
        x,y,w,h = condition.roi_x,condition.roi_y,condition.roi_width,condition.roi_height
        crop = image[y:y+h,x:x+w].astype(np.float64)
        if self.pixel_format.startswith("Bayer"):
            planes = [crop[(0-y)%2::2,(1-x)%2::2], crop[(1-y)%2::2,(0-x)%2::2]]
        else:
            planes = [crop]
        return float(np.mean([np.mean(cv2.Sobel(p, cv2.CV_64F,1,0,ksize=3)**2 +
                                     cv2.Sobel(p, cv2.CV_64F,0,1,ksize=3)**2) for p in planes]))

    def analysis_config(self):
        config = self.node.mtf_handler._build_mtf_config(
            self.node.pixel_size_um, self.node._param_float("mtf_min_edge_angle",2.0),
            self.node._param_float("mtf_max_edge_angle",11.0), False, self.encoding)
        config.capture_pixel_format = self.pixel_format
        config.capture_exposure_us = float(self.state()["values"]["exposure_time"])
        config.capture_gain = self.c.expected_gain
        config.source_encoding = self.encoding
        return asdict(config)

    def analyze_mtf_roi_frame(self, image, condition, analysis_config, edge_geometry=None):
        """Use the same square/four-edge core as /measure_mtf_roi."""
        return self.node.mtf_handler.analyze_mtf_roi_frame(
            image,
            (
                condition.roi_x,
                condition.roi_y,
                condition.roi_width,
                condition.roi_height,
            ),
            analysis_config,
            edge_geometry,
        )


class MeasurementAction:
    def __init__(self, node):
        self.node = node
        node.measurement_epoch = uuid.uuid4().hex
        self.server = ActionServer(node, StartMeasurement, "/promoc/camera/start_measurement",
            execute_callback=self.execute, goal_callback=self.goal,
            cancel_callback=lambda goal: CancelResponse.ACCEPT, callback_group=node.cb_group)

    def goal(self, request):
        try:
            condition_from_message(request.condition).validate()
            if not request.setup_confirmed:
                raise ValueError("Physical setup must be confirmed")
        except (ValueError, TypeError) as exc:
            self.node.get_logger().error(f"Measurement goal rejected: {exc}")
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT if self.node.measurement_lock.acquire(blocking=False) else GoalResponse.REJECT

    def execute(self, goal):
        condition = condition_from_message(goal.request.condition)
        engine = None
        try:
            def feedback(phase, index, completed):
                goal.publish_feedback(StartMeasurement.Feedback(phase=phase, current_measurement=index,
                    completed_measurements=completed, measurement_count=condition.measurement_count,
                    status_message=f"{completed}/{condition.measurement_count}: {phase}"))
            canceled = lambda: goal.is_cancel_requested
            io = MeasurementIO(self.node, canceled)
            engine = MeasurementEngine(condition, io, feedback, canceled)
            data = engine.run(goal.request.plan_source, goal.request.resume_run_id)
            goal.succeed()
        except Exception as exc:
            code = getattr(exc, "code", "MEASUREMENT_FAILED")
            data = engine.result(False, code, str(exc)) if engine else {
                "success": False, "error_code": code, "status_message": str(exc)}
            if goal.is_cancel_requested:
                goal.canceled()
            else:
                goal.abort()
            self.node.get_logger().error(f"Measurement stopped [{code}]: {exc}")
        finally:
            self.node.measurement_lock.release()
        return StartMeasurement.Result(**data)
