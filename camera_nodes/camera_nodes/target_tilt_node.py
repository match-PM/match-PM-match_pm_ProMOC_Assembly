"""ROS 2 action server for camera-based planar-target tilt estimation."""

from __future__ import annotations

import math
import threading
import time

from cv_bridge import CvBridge
from promoc_assembly_interfaces.action import EstimateTargetTilt
from promoc_assembly_interfaces.srv import (
    EstimateTargetTilt as EstimateTargetTiltService,
    GetOperationStatus,
    GetPosition,
    MoveAbsolute,
    Stop,
)
import rclpy
from rclpy.action import ActionClient, ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image

from .algorithms.target_tilt import (
    RoiTiltEstimator,
    TiltEstimate,
    TiltEstimatorConfig,
    TiltStatus,
    make_grid_rois,
)
from .algorithms.tilt_evaluation import export_evaluation
from .algorithms.tilt_roi_selection import make_overlapping_rois, validate_bbox


class _Cancelled(Exception):
    pass


class _HardwareTimeout(Exception):
    pass


class _ImageTimeout(Exception):
    pass


class TargetTiltActionNode(Node):
    """Run one cancellable focus-stack scan at a time."""

    def __init__(self) -> None:
        super().__init__("target_tilt_estimator")
        self._declare_parameters()
        self._bridge = CvBridge()
        self._cb_group = ReentrantCallbackGroup()
        self._goal_lock = threading.Lock()
        self._goal_reserved = False
        self._frame_condition = threading.Condition()
        self._capture_after_ns = 0
        self._capture_limit = 0
        self._captured_frames: list[tuple[object, str]] = []
        self._captured_stamps: set[int] = set()
        self._last_camera_info = None

        image_topic = str(self.get_parameter("image_topic").value)
        camera_info_topic = str(self.get_parameter("camera_info_topic").value)
        axis_prefix = str(self.get_parameter("axis_service_prefix").value).rstrip("/")
        self._move_client = self.create_client(
            MoveAbsolute,
            f"{axis_prefix}/move_absolute",
            callback_group=self._cb_group,
        )
        self._status_client = self.create_client(
            GetOperationStatus,
            f"{axis_prefix}/get_operation_status",
            callback_group=self._cb_group,
        )
        self._position_client = self.create_client(
            GetPosition,
            f"{axis_prefix}/get_position",
            callback_group=self._cb_group,
        )
        self._stop_client = self.create_client(
            Stop,
            f"{axis_prefix}/stop",
            callback_group=self._cb_group,
        )
        self._image_sub = self.create_subscription(
            Image,
            image_topic,
            self._image_callback,
            10,
            callback_group=self._cb_group,
        )
        self._camera_info_sub = self.create_subscription(
            CameraInfo,
            camera_info_topic,
            self._camera_info_callback,
            10,
            callback_group=self._cb_group,
        )
        self._diagnostic_publisher = self.create_publisher(
            Image,
            str(self.get_parameter("diagnostic_image_topic").value),
            1,
        )
        self._action_server = ActionServer(
            self,
            EstimateTargetTilt,
            "estimate_target_tilt",
            execute_callback=self._execute,
            goal_callback=self._goal_callback,
            cancel_callback=self._cancel_callback,
            callback_group=self._cb_group,
        )
        self._action_client = ActionClient(
            self,
            EstimateTargetTilt,
            "estimate_target_tilt",
            callback_group=self._cb_group,
        )
        self._service = self.create_service(
            EstimateTargetTiltService,
            "estimate_target_tilt_service",
            self._service_callback,
            callback_group=self._cb_group,
        )
        self.get_logger().info(
            "EstimateTargetTilt action and rqt service ready; "
            f"image='{image_topic}', axis='{axis_prefix}'"
        )

    def _declare_parameters(self) -> None:
        defaults = {
            "image_topic": "image_raw",
            "camera_info_topic": "camera_info",
            # This is the canonical focus-stage interface present in this repository.
            "axis_service_prefix": "/promoc/linear_axis/lts300_x_axis",
            "object_um_per_pixel": 0.8,
            "roi_rows": 7,
            "roi_cols": 7,
            "roi_width_fraction": 0.10,
            "roi_height_fraction": 0.10,
            "roi_margin_fraction": 0.08,
            "use_integral_image": True,
            "settle_time_s": 0.15,
            "axis_timeout_s": 30.0,
            "image_timeout_s": 2.0,
            "axis_position_tolerance_mm": 0.01,
            "min_contrast": 0.015,
            "max_black_fraction": 0.98,
            "max_saturated_fraction": 0.98,
            "min_gradient_energy": 1.0e-5,
            "max_frame_cv": 0.35,
            "min_peak_prominence": 0.03,
            "min_peak_curvature": 1.0e-6,
            "min_fit_r2": 0.40,
            "min_valid_rois": 10,
            "min_span_fraction": 0.50,
            "min_quadrants": 4,
            "max_design_condition": 100.0,
            "repeatability_x_deg": 0.002,
            "repeatability_y_deg": 0.002,
            "tolerance_x_deg": 0.05,
            "tolerance_y_deg": 0.05,
            "peak_half_window": 2,
            "focus_metric": "tenengrad",
            # ROS 2 Humble cannot infer the type of an empty array default.
            # The empty-string sentinel is filtered before metrics are used.
            "evaluation_focus_metrics": [""],
            "peak_fit_method": "quadratic",
            "surface_weighted": False,
            "surface_robust": True,
            "huber_k": 1.345,
            "max_peak_uncertainty_um": 100.0,
            "weight_sigma_floor_um": 0.5,
            "weight_sigma_ceiling_um": 100.0,
            "robust_outlier_weight_threshold": 0.25,
            "bootstrap_iterations": 0,
            "bootstrap_seed": 1729,
            "reference_surface_path": "",
            "evaluation_enabled": False,
            "evaluation_output_directory": "tilt_evaluation",
            "evaluation_export_all_focus_curves": False,
            "service_wait_timeout_s": 900.0,
            "roi_selection_mode": "auto_texture",
            "manual_target_bbox": [0.0, 0.0, 1.0, 1.0],
            "candidate_roi_width_fraction": 0.08,
            "candidate_roi_height_fraction": 0.08,
            "candidate_step_x_fraction": 0.06,
            "candidate_step_y_fraction": 0.06,
            "minimum_structured_pixel_fraction": 0.01,
            "structure_mad_multiplier": 3.0,
            "structure_energy_quantile": 0.90,
            "analysis_max_dimension_px": 2048,
            "sparse_contrast_quantile": 0.999,
            "sparse_energy_quantile": 0.995,
            "minimum_gradient_snr": 6.0,
            "minimum_connected_edge_pixels": 6,
            "minimum_connected_edge_span_fraction": 0.12,
            "support_closing_radius": 1,
            "minimum_target_coverage_fraction": 0.05,
            "minimum_baseline_x_mm": 0.25,
            "minimum_baseline_y_mm": 0.25,
            "minimum_spatial_bins_x": 3,
            "minimum_spatial_bins_y": 3,
            "minimum_selected_rois": 10,
            "maximum_selected_rois": 30,
            "minimum_quality_weight": 0.05,
            "maximum_quality_weight": 20.0,
            "maximum_standardized_residual": 3.5,
            "diagnostic_image_enabled": False,
            "diagnostic_image_topic": "target_tilt/roi_diagnostics",
            "diagnostic_image_max_dimension": 1600,
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value)

    def _service_callback(self, request, response):
        """Forward an rqt-friendly service call to the canonical action path."""
        goal = EstimateTargetTilt.Goal()
        for name in (
            "center_z_mm", "half_range_mm", "step_mm", "frames_per_position",
            "fit_field_curvature", "return_to_center",
        ):
            setattr(goal, name, getattr(request, name))
        timeout = float(self.get_parameter("service_wait_timeout_s").value)
        deadline = time.monotonic() + timeout
        if not self._action_client.wait_for_server(timeout_sec=min(timeout, 2.0)):
            response.accepted = False
            response.status = int(TiltStatus.HARDWARE_TIMEOUT)
            response.status_message = "EstimateTargetTilt action server unavailable"
            return response
        send_future = self._action_client.send_goal_async(goal)
        if not self._wait_future(send_future, deadline):
            response.accepted = False
            response.status = int(TiltStatus.HARDWARE_TIMEOUT)
            response.status_message = "timed out while submitting action goal"
            return response
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            response.accepted = False
            response.status = int(TiltStatus.FIT_UNSTABLE)
            response.status_message = "goal rejected; scan active or request invalid"
            return response
        response.accepted = True
        result_future = goal_handle.get_result_async()
        if not self._wait_future(result_future, deadline):
            goal_handle.cancel_goal_async()
            response.status = int(TiltStatus.HARDWARE_TIMEOUT)
            response.status_message = "service wait timeout; cancellation requested"
            return response
        action_result = result_future.result().result
        for name in EstimateTargetTiltService.Response.get_fields_and_field_types():
            if name != "accepted" and hasattr(action_result, name):
                setattr(response, name, getattr(action_result, name))
        return response

    @staticmethod
    def _wait_future(future, deadline):
        while rclpy.ok() and not future.done():
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.01)
        return future.done()

    def _goal_callback(self, request) -> GoalResponse:
        if (
            not math.isfinite(request.center_z_mm)
            or not math.isfinite(request.half_range_mm)
            or not math.isfinite(request.step_mm)
            or request.half_range_mm <= 0.0
            or request.step_mm <= 0.0
            or request.step_mm > 2.0 * request.half_range_mm
            or request.frames_per_position < 1
        ):
            self.get_logger().warning("Rejected invalid EstimateTargetTilt goal")
            return GoalResponse.REJECT
        count = len(
            self._scan_positions(
                request.center_z_mm,
                request.half_range_mm,
                request.step_mm,
            )
        )
        if count < 3 or count > 1000 or request.frames_per_position > 100:
            self.get_logger().warning("Rejected unsafe EstimateTargetTilt scan size")
            return GoalResponse.REJECT
        with self._goal_lock:
            if self._goal_reserved:
                self.get_logger().warning("Rejected EstimateTargetTilt goal: scan already active")
                return GoalResponse.REJECT
            self._goal_reserved = True
        return GoalResponse.ACCEPT

    @staticmethod
    def _cancel_callback(_goal_handle) -> CancelResponse:
        return CancelResponse.ACCEPT

    def _image_callback(self, msg: Image) -> None:
        stamp_ns = int(msg.header.stamp.sec) * 1_000_000_000 + int(msg.header.stamp.nanosec)
        with self._frame_condition:
            if (
                self._capture_limit <= 0
                or stamp_ns <= self._capture_after_ns
                or stamp_ns in self._captured_stamps
                # Only one full-resolution frame may wait while one is processed.
                or bool(self._captured_frames)
            ):
                return
            try:
                array = self._bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
            except Exception as exc:
                self.get_logger().warning(f"Rejected camera frame: {exc}")
                return
            self._captured_frames.append((array, str(msg.encoding)))
            self._captured_stamps.add(stamp_ns)
            self._frame_condition.notify_all()

    def _camera_info_callback(self, msg: CameraInfo) -> None:
        # CameraInfo is deliberately advisory. Object scale comes from the profile.
        self._last_camera_info = msg

    def _execute(self, goal_handle):
        goal = goal_handle.request
        result = None; estimator = None; terminal_state = "succeed"
        try:
            self._wait_for_axis_services(goal_handle)
            estimator = self._make_estimator()
            positions = self._scan_positions(
                goal.center_z_mm,
                goal.half_range_mm,
                goal.step_mm,
            )
            for index, z_mm in enumerate(positions):
                self._check_cancel(goal_handle)
                self._feedback(goal_handle, "moving", index, len(positions), z_mm, 0, estimator)
                self._move_and_wait(z_mm, goal_handle)
                self._feedback(goal_handle, "settling", index, len(positions), z_mm, 0, estimator)
                self._cancellable_sleep(float(self.get_parameter("settle_time_s").value), goal_handle)
                self._feedback(goal_handle, "acquiring", index, len(positions), z_mm, 0, estimator)
                requested_frames = int(goal.frames_per_position)
                frames = self._capture_frames(
                    requested_frames,
                    goal_handle,
                    lambda acquired: self._feedback(
                        goal_handle,
                        "acquiring",
                        index,
                        len(positions),
                        z_mm,
                        acquired,
                        estimator,
                    ),
                )
                estimator.add_position(z_mm, frames)
                self._feedback(
                    goal_handle,
                    "acquiring",
                    index,
                    len(positions),
                    z_mm,
                    requested_frames,
                    estimator,
                )

            self._check_cancel(goal_handle)
            self._feedback(goal_handle, "fitting", len(positions), len(positions), positions[-1], 0, estimator)
            result = estimator.solve(
                quadratic_surface=bool(goal.fit_field_curvature),
                peak_half_window=int(self.get_parameter("peak_half_window").value),
            )
            self.get_logger().info(
                "Tilt ROI counts: "
                f"candidates={result.candidate_roi_count}, "
                f"focus_valid={result.focus_valid_roi_count}, "
                f"selected={result.selected_roi_count}, "
                f"surface_inliers={result.surface_inlier_count}, "
                f"rejected_focus={result.roi_rejected_focus}, "
                f"rejected_spatial={result.roi_rejected_spatial}, "
                f"rejected_surface={result.roi_rejected_surface}"
            )
        except _Cancelled:
            self._stop_axis()
            result = TiltEstimate(TiltStatus.CANCELLED, "scan cancelled by client")
            terminal_state = "canceled"
        except _ImageTimeout as exc:
            result = TiltEstimate(TiltStatus.IMAGE_TIMEOUT, str(exc))
            terminal_state = "abort"
        except _HardwareTimeout as exc:
            self._stop_axis()
            result = TiltEstimate(TiltStatus.HARDWARE_TIMEOUT, str(exc))
            terminal_state = "abort"
        except (ValueError, RuntimeError) as exc:
            self.get_logger().error(f"Tilt scan failed: {exc}")
            result = TiltEstimate(TiltStatus.FIT_UNSTABLE, str(exc))
            terminal_state = "abort"
        except Exception as exc:
            self.get_logger().error(f"Unexpected tilt scan failure: {exc}")
            result = TiltEstimate(TiltStatus.FIT_UNSTABLE, str(exc))
            terminal_state = "abort"
        finally:
            with self._frame_condition:
                self._capture_limit = 0
                self._captured_frames.clear()
                self._captured_stamps.clear()
            if goal.return_to_center:
                try:
                    if estimator is not None:
                        self._feedback(goal_handle, "returning", 0, 0, goal.center_z_mm, 0, estimator)
                    self._move_and_wait(float(goal.center_z_mm), goal_handle, allow_cancel=False)
                except _HardwareTimeout as exc:
                    self.get_logger().error(f"Mandatory return-to-center failed: {exc}")
                    if result is None or terminal_state == "succeed":
                        result = TiltEstimate(TiltStatus.HARDWARE_TIMEOUT, f"return-to-center failed: {exc}")
                        terminal_state = "abort"
                    else:
                        result.status_message += f"; return-to-center failed: {exc}"

        result=result or TiltEstimate(TiltStatus.FIT_UNSTABLE,"unknown failure")
        # Diagnostics deliberately run only after the hardware cleanup above.
        if estimator is not None:
            self._publish_diagnostics_after_cleanup(estimator,result)
            self._export_evaluation_after_cleanup(estimator,result,goal)
        try:
            if terminal_state == "canceled": goal_handle.canceled()
            elif terminal_state == "abort": goal_handle.abort()
            else: goal_handle.succeed()
            return self._to_action_result(result)
        finally:
            with self._goal_lock:
                self._goal_reserved = False

    def _publish_diagnostics_after_cleanup(self,estimator,result):
        if not bool(self.get_parameter("diagnostic_image_enabled").value): return
        try:
            diagnostic=estimator.diagnostic_image(result,int(self.get_parameter("diagnostic_image_max_dimension").value))
            message=self._bridge.cv2_to_imgmsg(diagnostic,encoding="bgr8")
            message.header.stamp=self.get_clock().now().to_msg(); message.header.frame_id="target_tilt_diagnostics"
            self._diagnostic_publisher.publish(message)
        except Exception as exc:
            self.get_logger().error(f"Diagnostic image failed after hardware cleanup: {exc}")
            result.status_message+=f"; diagnostic image failed: {exc}"

    def _export_evaluation_after_cleanup(self,estimator,result,goal):
        if not bool(self.get_parameter("evaluation_enabled").value): return
        try:
            metric_results={}
            for metric in self.get_parameter("evaluation_focus_metrics").value:
                if str(metric).strip():
                    metric_results[str(metric)]=estimator.solve_metric(str(metric),quadratic_surface=bool(goal.fit_field_curvature),peak_half_window=int(self.get_parameter("peak_half_window").value))
            evaluation_directory=export_evaluation(
                str(self.get_parameter("evaluation_output_directory").value),result,
                metric_results=metric_results,
                metadata={"center_z_mm":float(goal.center_z_mm),"half_range_mm":float(goal.half_range_mm),"step_mm":float(goal.step_mm),"frames_per_position":int(goal.frames_per_position),"object_um_per_pixel":float(self.get_parameter("object_um_per_pixel").value),"image_shape":list(estimator.image_signature[0]) if estimator.image_signature else []},
                export_all_focus_curves=bool(self.get_parameter("evaluation_export_all_focus_curves").value),
            )
            result.status_message+=f"; evaluation={evaluation_directory}"; result.evaluation_directory=evaluation_directory
        except Exception as exc:
            self.get_logger().error(f"Evaluation export failed after hardware cleanup: {exc}")
            result.status_message+=f"; evaluation export failed: {exc}"

    def _make_estimator(self) -> RoiTiltEstimator:
        def value(name):
            return self.get_parameter(name).value

        selection_mode = str(value("roi_selection_mode"))
        manual_bbox = validate_bbox(value("manual_target_bbox"))
        if selection_mode == "fixed_grid":
            rois = make_grid_rois(
                int(value("roi_rows")),
                int(value("roi_cols")),
                roi_width_fraction=float(value("roi_width_fraction")),
                roi_height_fraction=float(value("roi_height_fraction")),
                margin_fraction=float(value("roi_margin_fraction")),
            )
        else:
            candidate_bbox = manual_bbox if selection_mode == "manual_bbox" else (0.0, 0.0, 1.0, 1.0)
            rois, _ = make_overlapping_rois(
                float(value("candidate_roi_width_fraction")),
                float(value("candidate_roi_height_fraction")),
                float(value("candidate_step_x_fraction")),
                float(value("candidate_step_y_fraction")),
                bbox=candidate_bbox,
            )
        config = TiltEstimatorConfig(
            object_um_per_pixel=float(value("object_um_per_pixel")),
            use_integral_image=bool(value("use_integral_image")),
            focus_metric=str(value("focus_metric")),
            evaluation_focus_metrics=tuple(
                str(item).strip()
                for item in value("evaluation_focus_metrics")
                if str(item).strip()
            ),
            peak_fit_method=str(value("peak_fit_method")),
            surface_weighted=bool(value("surface_weighted")),
            surface_robust=bool(value("surface_robust")),
            huber_k=float(value("huber_k")),
            min_contrast=float(value("min_contrast")),
            max_black_fraction=float(value("max_black_fraction")),
            max_saturated_fraction=float(value("max_saturated_fraction")),
            min_gradient_energy=float(value("min_gradient_energy")),
            max_frame_cv=float(value("max_frame_cv")),
            min_peak_prominence=float(value("min_peak_prominence")),
            min_peak_curvature=float(value("min_peak_curvature")),
            min_fit_r2=float(value("min_fit_r2")),
            max_peak_uncertainty_um=float(value("max_peak_uncertainty_um")),
            weight_sigma_floor_um=float(value("weight_sigma_floor_um")),
            weight_sigma_ceiling_um=float(value("weight_sigma_ceiling_um")),
            robust_outlier_weight_threshold=float(value("robust_outlier_weight_threshold")),
            min_valid_rois=int(value("min_valid_rois")),
            min_span_fraction=float(value("min_span_fraction")),
            min_quadrants=int(value("min_quadrants")),
            max_design_condition=float(value("max_design_condition")),
            repeatability_x_deg=float(value("repeatability_x_deg")),
            repeatability_y_deg=float(value("repeatability_y_deg")),
            tolerance_x_deg=float(value("tolerance_x_deg")),
            tolerance_y_deg=float(value("tolerance_y_deg")),
            retain_frame_scores=bool(value("evaluation_enabled")),
            bootstrap_iterations=int(value("bootstrap_iterations")),
            bootstrap_seed=int(value("bootstrap_seed")),
            reference_surface_path=str(value("reference_surface_path")),
            roi_selection_mode=selection_mode,
            manual_target_bbox=manual_bbox,
            minimum_structured_pixel_fraction=float(value("minimum_structured_pixel_fraction")),
            structure_mad_multiplier=float(value("structure_mad_multiplier")),
            structure_energy_quantile=float(value("structure_energy_quantile")),
            analysis_max_dimension_px=int(value("analysis_max_dimension_px")),
            sparse_contrast_quantile=float(value("sparse_contrast_quantile")),
            sparse_energy_quantile=float(value("sparse_energy_quantile")),
            minimum_gradient_snr=float(value("minimum_gradient_snr")),
            minimum_connected_edge_pixels=int(value("minimum_connected_edge_pixels")),
            minimum_connected_edge_span_fraction=float(value("minimum_connected_edge_span_fraction")),
            support_closing_radius=int(value("support_closing_radius")),
            minimum_target_coverage_fraction=float(value("minimum_target_coverage_fraction")),
            minimum_baseline_x_mm=float(value("minimum_baseline_x_mm")),
            minimum_baseline_y_mm=float(value("minimum_baseline_y_mm")),
            minimum_spatial_bins_x=int(value("minimum_spatial_bins_x")),
            minimum_spatial_bins_y=int(value("minimum_spatial_bins_y")),
            minimum_selected_rois=int(value("minimum_selected_rois")),
            maximum_selected_rois=int(value("maximum_selected_rois")),
            minimum_quality_weight=float(value("minimum_quality_weight")),
            maximum_quality_weight=float(value("maximum_quality_weight")),
            maximum_standardized_residual=float(value("maximum_standardized_residual")),
        )
        return RoiTiltEstimator(rois, config)

    @staticmethod
    def _scan_positions(center: float, half_range: float, step: float) -> list[float]:
        count = int(math.floor(2.0 * half_range / step + 1.0e-9)) + 1
        start = center - half_range
        positions = [start + index * step for index in range(count)]
        if positions[-1] < center + half_range - step * 1.0e-6:
            positions.append(center + half_range)
        return positions

    def _wait_for_axis_services(self, goal_handle) -> None:
        timeout = float(self.get_parameter("axis_timeout_s").value)
        deadline = time.monotonic() + timeout
        for name, client in (
            ("move_absolute", self._move_client),
            ("get_operation_status", self._status_client),
            ("get_position", self._position_client),
        ):
            while not client.service_is_ready():
                self._check_cancel(goal_handle)
                remaining = deadline - time.monotonic()
                if remaining <= 0.0:
                    raise _HardwareTimeout(f"axis service '{name}' unavailable")
                client.wait_for_service(timeout_sec=min(0.2, remaining))

    def _future_result(self, future, deadline: float, goal_handle, *, allow_cancel: bool = True):
        while time.monotonic() < deadline:
            if allow_cancel:
                self._check_cancel(goal_handle)
            if future.done():
                try:
                    return future.result()
                except Exception as exc:
                    raise _HardwareTimeout(f"axis service call failed: {exc}") from exc
            time.sleep(0.01)
        raise _HardwareTimeout("axis service response timed out")

    def _move_and_wait(self, target_mm: float, goal_handle, *, allow_cancel: bool = True) -> None:
        timeout = float(self.get_parameter("axis_timeout_s").value)
        deadline = time.monotonic() + timeout
        request = MoveAbsolute.Request()
        request.axis_position = float(target_mm)
        response = self._future_result(
            self._move_client.call_async(request), deadline, goal_handle, allow_cancel=allow_cancel
        )
        if response is None or not response.success:
            raise _HardwareTimeout(
                f"axis rejected target {target_mm:.6f} mm: "
                f"{getattr(response, 'status_message', 'no response')}"
            )
        while time.monotonic() < deadline:
            if allow_cancel:
                self._check_cancel(goal_handle)
            status = self._future_result(
                self._status_client.call_async(GetOperationStatus.Request()),
                min(deadline, time.monotonic() + 1.0),
                goal_handle,
                allow_cancel=allow_cancel,
            )
            if status and status.operation_status in {"error", "emergency_stop"}:
                raise _HardwareTimeout(f"axis entered {status.operation_status}: {status.status_message}")
            if status and status.operation_status == "idle":
                position = self._future_result(
                    self._position_client.call_async(GetPosition.Request()),
                    min(deadline, time.monotonic() + 1.0),
                    goal_handle,
                    allow_cancel=allow_cancel,
                )
                tolerance = float(self.get_parameter("axis_position_tolerance_mm").value)
                if position and position.success and abs(position.axis_position - target_mm) <= tolerance:
                    return
            time.sleep(0.03)
        raise _HardwareTimeout(f"axis did not reach {target_mm:.6f} mm")

    def _capture_frames(self, count: int, goal_handle, feedback_callback):
        """Yield post-settle frames while retaining at most one queued frame."""
        after_ns = int(self.get_clock().now().nanoseconds)
        timeout = float(self.get_parameter("image_timeout_s").value)
        with self._frame_condition:
            self._capture_after_ns = after_ns
            self._capture_limit = count
            self._captured_frames = []
            self._captured_stamps = set()
        acquired = 0
        try:
            while acquired < count:
                deadline = time.monotonic() + timeout
                with self._frame_condition:
                    while not self._captured_frames:
                        self._check_cancel(goal_handle)
                        remaining = deadline - time.monotonic()
                        if remaining <= 0.0:
                            raise _ImageTimeout(
                                f"received {acquired}/{count} fresh, uniquely "
                                "timestamped frames"
                            )
                        self._frame_condition.wait(timeout=min(0.05, remaining))
                    frame = self._captured_frames.pop(0)
                acquired += 1
                feedback_callback(acquired)
                yield frame
        finally:
            with self._frame_condition:
                self._capture_limit = 0
                self._captured_frames.clear()

    @staticmethod
    def _check_cancel(goal_handle) -> None:
        if goal_handle.is_cancel_requested:
            raise _Cancelled()

    def _cancellable_sleep(self, seconds: float, goal_handle) -> None:
        deadline = time.monotonic() + max(0.0, seconds)
        while True:
            self._check_cancel(goal_handle)
            # Re-read the clock once and check the remainder before sleeping.
            # A second monotonic() call inside sleep's argument could cross the
            # deadline and sporadically pass a tiny negative value to sleep().
            remaining = deadline - time.monotonic()
            if remaining <= 0.0:
                return
            time.sleep(min(0.02, remaining))

    def _stop_axis(self) -> None:
        if not self._stop_client.service_is_ready():
            return
        try:
            future = self._stop_client.call_async(Stop.Request())
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and not future.done():
                time.sleep(0.01)
            response = future.result() if future.done() else None
            if response is None or not response.success:
                self.get_logger().error(
                    "Axis stop was not confirmed after cancellation"
                )
        except Exception as exc:
            self.get_logger().error(f"Could not stop axis after cancellation: {exc}")

    def _return_after_abort(self, goal, goal_handle) -> None:
        if not goal.return_to_center:
            return
        try:
            self._move_and_wait(float(goal.center_z_mm), goal_handle, allow_cancel=False)
        except _HardwareTimeout as exc:
            self.get_logger().error(f"Return-to-center after abort failed: {exc}")

    @staticmethod
    def _feedback(goal_handle, phase, z_index, z_count, z_mm, frames, estimator) -> None:
        feedback = EstimateTargetTilt.Feedback()
        feedback.phase = str(phase)
        feedback.z_index = int(z_index)
        feedback.z_count = int(z_count)
        feedback.current_z_mm = float(z_mm)
        feedback.frames_acquired = int(frames)
        feedback.preliminary_valid_rois = int(estimator.preliminary_valid_rois())
        goal_handle.publish_feedback(feedback)

    @staticmethod
    def _to_action_result(estimate: TiltEstimate):
        result = EstimateTargetTilt.Result()
        result.status = int(estimate.status)
        result.status_message = str(estimate.status_message)
        for name in (
            "tilt_x_deg",
            "tilt_y_deg",
            "uncertainty_x_deg",
            "uncertainty_y_deg",
            "detection_limit_x_deg",
            "detection_limit_y_deg",
            "center_focus_z_mm",
            "surface_rms_um",
            "x_span_fraction",
            "y_span_fraction",
            "surface_mae_um",
            "surface_median_abs_um",
            "surface_max_abs_um",
            "mean_peak_uncertainty_um",
            "median_peak_uncertainty_um",
            "target_coverage_fraction",
            "baseline_x_mm",
            "baseline_y_mm",
            "design_condition_number",
        ):
            setattr(result, name, float(getattr(estimate, name)))
        result.roi_total = int(estimate.roi_total)
        result.roi_valid = int(estimate.roi_valid)
        result.roi_surface_inliers = int(estimate.roi_surface_inliers)
        result.roi_rejected_focus = int(estimate.roi_rejected_focus)
        result.roi_rejected_spatial = int(estimate.roi_rejected_spatial)
        result.roi_rejected_surface = int(estimate.roi_rejected_surface)
        result.roi_robust_outliers = int(estimate.roi_robust_outliers)
        result.target_bbox_normalized = [
            float(value) for value in estimate.target_bbox_normalized
        ]
        result.candidate_roi_count = int(estimate.candidate_roi_count)
        result.structurally_valid_candidate_count = int(
            estimate.structurally_valid_candidate_count
        )
        result.focus_valid_roi_count = int(estimate.focus_valid_roi_count)
        result.selected_roi_count = int(estimate.selected_roi_count)
        result.surface_inlier_count = int(estimate.surface_inlier_count)
        result.decision_x = str(estimate.decision_x)
        result.decision_y = str(estimate.decision_y)
        result.evaluation_directory = str(getattr(estimate, "evaluation_directory", ""))
        result.tilt_x_detectable = bool(estimate.tilt_x_detectable)
        result.tilt_y_detectable = bool(estimate.tilt_y_detectable)
        result.within_tolerance_x = bool(estimate.within_tolerance_x)
        result.within_tolerance_y = bool(estimate.within_tolerance_y)
        result.resolution_limited_x = bool(estimate.resolution_limited_x)
        result.resolution_limited_y = bool(estimate.resolution_limited_y)
        return result


def main(args=None) -> None:
    rclpy.init(args=args)
    node = TargetTiltActionNode()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()
