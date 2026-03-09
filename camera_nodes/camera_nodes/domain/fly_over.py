"""Fly-over target detection for autofocus handler."""

from __future__ import annotations

from dataclasses import dataclass
import time

import numpy as np

from promoc_assembly_interfaces.srv import (
    GetOperationStatus,
    GetVelocityParameters,
    MoveAbsolute,
)
from promoc_core.promoc_exceptions import ServiceError

from ..services.clients.axis_velocity import temporary_velocity
from ..services.clients.parameter_access import ParameterAccessor


@dataclass(frozen=True)
class FlyOverResult:
    """Result of fly-over target detection."""

    peak_start: float | None
    peak_end: float | None
    max_stddev: float


class FlyOverDetector:
    """Fast scan over focus range to detect target window."""

    def __init__(
        self,
        node,
        get_latest_cv_image,
        get_center_roi,
        wait_for_axis_idle,
        get_position,
    ):
        self._node = node
        self._get_latest_cv_image = get_latest_cv_image
        self._get_center_roi = get_center_roi
        self._wait_for_axis_idle = wait_for_axis_idle
        self._get_position = get_position
        self.params = ParameterAccessor(node)

    def _param_raw(self, name: str, default=None):
        return self.params.raw(name, default)

    def _param_float(self, name: str, default: float) -> float:
        return self.params.as_float(name, default)

    def _param_int(self, name: str, default: int) -> int:
        return self.params.as_int(name, default)

    def _param_bool(self, name: str, default: bool = False) -> bool:
        return self.params.as_bool(name, default)

    def _estimate_frame_period_s(self, timeout_s: float = 0.8) -> float | None:
        """Estimate camera frame period from image timestamps."""
        start = time.time()
        first_ts = None
        while time.time() - start < timeout_s:
            _, ts = self._get_latest_cv_image()
            if ts is None:
                time.sleep(0.01)
                continue
            if first_ts is None:
                first_ts = ts
            elif ts > first_ts:
                return max(1e-4, float(ts - first_ts) / 1_000_000_000.0)
            time.sleep(0.01)
        return None

    @staticmethod
    def _robust_mad_sigma(values: np.ndarray) -> float:
        """Estimate noise sigma via MAD (robust against peaks/outliers)."""
        if values.size == 0:
            return 0.0
        median = float(np.median(values))
        mad = float(np.median(np.abs(values - median)))
        sigma = 1.4826 * mad
        if sigma <= 0:
            sigma = float(np.std(values))
        return max(1e-9, sigma)

    @staticmethod
    def _median_smooth_1d(values: np.ndarray, window: int) -> np.ndarray:
        """Apply 1D median smoothing without scipy dependency."""
        if values.size < 3:
            return values.copy()
        win = int(max(1, window))
        if win % 2 == 0:
            win += 1
        if win <= 1:
            return values.copy()
        win = min(win, values.size if values.size % 2 == 1 else values.size - 1)
        if win <= 1:
            return values.copy()

        half = win // 2
        padded = np.pad(values, (half, half), mode="edge")
        smoothed = np.empty_like(values, dtype=np.float64)
        for i in range(values.size):
            smoothed[i] = float(np.median(padded[i : i + win]))
        return smoothed

    @staticmethod
    def _select_component_bounds(
        mask: np.ndarray, center_index: int
    ) -> tuple[int, int] | None:
        """Select connected True segment nearest to center_index."""
        indices = np.flatnonzero(mask)
        if indices.size == 0:
            return None

        splits = np.where(np.diff(indices) > 1)[0]
        starts = np.r_[indices[0], indices[splits + 1]]
        ends = np.r_[indices[splits], indices[-1]]

        for start, end in zip(starts, ends):
            if start <= center_index <= end:
                return int(start), int(end)

        def _distance_to_segment(start: int, end: int) -> int:
            if center_index < start:
                return int(start - center_index)
            return int(center_index - end)

        best = min(
            zip(starts, ends),
            key=lambda seg: _distance_to_segment(int(seg[0]), int(seg[1])),
        )
        return int(best[0]), int(best[1])

    def _collect_scan_data(
        self,
        start_pos: float,
        end_pos: float,
        clients,
        roi_size: int,
        full_scan: bool,
        effective_real_speed: float,
        poll_s: float,
    ) -> list[tuple[float, float]]:
        """Move across range and collect (position, stddev) samples."""
        clients["move"].call(MoveAbsolute.Request(axis_position=float(end_pos)))

        scan_data = []
        scan_start_time = time.time()
        scan_start_pos = float(start_pos)
        end_tolerance = 0.1
        last_pos = None
        last_pos_time = time.time()
        last_log_time = time.time()
        last_image_ts = None

        while True:
            status = clients["status"].call(GetOperationStatus.Request())
            if status and status.operation_status in ["error", "emergency_stop"]:
                raise ServiceError("Axis error during fly-over")

            current_pos = self._get_position(clients)
            if current_pos >= 0:
                if last_pos is None or abs(current_pos - last_pos) > 1e-4:
                    last_pos = current_pos
                    last_pos_time = time.time()

            use_estimate = False
            if current_pos < 0 or (time.time() - last_pos_time > 1.0):
                use_estimate = True
                elapsed = time.time() - scan_start_time
                current_pos = max(
                    start_pos,
                    min(end_pos, scan_start_pos + (effective_real_speed * elapsed)),
                )

            cv_image, image_ts = self._get_latest_cv_image()
            if (
                cv_image is not None
                and image_ts is not None
                and image_ts != last_image_ts
            ):
                last_image_ts = image_ts
                green = cv_image[:, :, 1] if len(cv_image.shape) == 3 else cv_image
                roi = self._get_center_roi(green, roi_size)
                stddev = float(np.std(roi)) if roi.size > 0 else 0.0
                scan_data.append((current_pos, stddev))

                if time.time() - last_log_time >= 0.1:
                    action_tag = "EST" if use_estimate else "REAL"
                    self._node.get_logger().info(
                        f"Fly-Over [{action_tag}]: x={current_pos:.2f}mm std={stddev:.2f}"
                    )
                    last_log_time = time.time()

            if status and status.operation_status == "idle":
                final_pos = self._get_position(clients)
                if final_pos >= 0 and abs(final_pos - end_pos) <= end_tolerance:
                    break
                if full_scan:
                    break
                break

            time.sleep(poll_s)

        return scan_data

    def _analyze_peak(
        self,
        scan_data: list[tuple[float, float]],
        start_pos: float,
        end_pos: float,
        peak_ratio: float,
        margin: float,
        backtrack: float,
        guard: float = 0.0,
        min_window_width: float = 0.0,
        threshold: float = 0.0,
    ) -> FlyOverResult:
        """Analyze collected fly-over data and determine peak window."""
        if not scan_data:
            self._node.get_logger().warn("Fly-Over finished with no data.")
            return FlyOverResult(None, None, 0.0)

        scan_data.sort(key=lambda x: x[0])
        positions = np.array([p for p, _ in scan_data], dtype=np.float64)
        std_values_raw = np.array([s for _, s in scan_data], dtype=np.float64)

        smooth_window = self._param_int("autofocus.fly_over.smooth_window_samples", 5)
        baseline_percentile = self._param_float(
            "autofocus.fly_over.baseline_percentile", 20.0
        )
        baseline_percentile = min(50.0, max(0.0, baseline_percentile))
        snr_threshold = self._param_float("autofocus.fly_over.snr_threshold", 3.0)
        snr_threshold = max(0.5, snr_threshold)

        std_values_smooth = self._median_smooth_1d(std_values_raw, smooth_window)
        std_values_eval = np.maximum(std_values_smooth, std_values_raw)

        smooth_peak_index = int(np.argmax(std_values_smooth))
        raw_peak_index = int(np.argmax(std_values_raw))
        smooth_peak_value = float(std_values_smooth[smooth_peak_index])
        raw_peak_value = float(std_values_raw[raw_peak_index])

        if raw_peak_value >= smooth_peak_value:
            peak_index = raw_peak_index
            peak_source = "raw"
        else:
            peak_index = smooth_peak_index
            peak_source = "smooth"

        max_stddev_pos = float(positions[peak_index])
        max_stddev = float(std_values_eval[peak_index])

        baseline_stddev = float(np.percentile(std_values_eval, baseline_percentile))
        dynamic_threshold = (
            baseline_stddev + (max_stddev - baseline_stddev) * peak_ratio
        )
        dynamic_threshold = min(max_stddev, max(0.0, dynamic_threshold))

        noise_sigma = self._robust_mad_sigma(std_values_raw - std_values_smooth)
        signal = np.maximum(0.0, std_values_eval - baseline_stddev)
        snr_mask = signal >= (snr_threshold * noise_sigma)
        ratio_mask = std_values_eval >= dynamic_threshold
        valid_mask = np.logical_and(snr_mask, ratio_mask)

        if threshold > 0:
            if max_stddev >= threshold:
                valid_mask = np.logical_and(valid_mask, std_values_eval >= threshold)
            else:
                self._node.get_logger().warn(
                    f"Ignoring absolute stddev threshold={threshold:.2f} because peak is only {max_stddev:.2f}."
                )

        if not np.any(valid_mask):
            valid_mask = ratio_mask
        if not np.any(valid_mask):
            valid_mask = snr_mask
        if not np.any(valid_mask):
            self._node.get_logger().warn(
                f"No point in fly-over exceeded robust criteria (ratio={dynamic_threshold:.2f}, snr={snr_threshold:.2f})."
            )
            return FlyOverResult(None, None, max_stddev)

        segment_bounds = self._select_component_bounds(valid_mask, peak_index)
        if segment_bounds is None:
            self._node.get_logger().warn(
                "No connected valid segment around fly-over peak."
            )
            return FlyOverResult(None, None, max_stddev)

        seg_start, seg_end = segment_bounds
        peak_window_min = float(positions[seg_start])
        peak_window_max = float(positions[seg_end])

        peak_window_min_m = peak_window_min - max(margin, backtrack) - max(0.0, guard)
        peak_window_max_m = peak_window_max + margin + max(0.0, guard)

        # Safety net against local maxima lock-in:
        # enforce a minimum coarse search width around the detected peak center.
        enforced_min_width = max(0.0, float(min_window_width))
        current_width = float(peak_window_max_m - peak_window_min_m)
        if enforced_min_width > 0.0 and current_width < enforced_min_width:
            half = 0.5 * enforced_min_width
            peak_window_min_m = min(peak_window_min_m, max_stddev_pos - half)
            peak_window_max_m = max(peak_window_max_m, max_stddev_pos + half)

        self._node.get_logger().info(
            f"Fly-Over: Peak at {max_stddev_pos:.2f}mm (std={max_stddev:.2f}, source={peak_source}, "
            f"raw_max={raw_peak_value:.2f}@{positions[raw_peak_index]:.2f}mm, "
            f"smooth_max={smooth_peak_value:.2f}@{positions[smooth_peak_index]:.2f}mm). "
            f"Window points={int(np.count_nonzero(valid_mask))} "
            f"(ratio_thr={dynamic_threshold:.2f}, baseline={baseline_stddev:.2f}, "
            f"noise_sigma={noise_sigma:.3f}, snr_thr={snr_threshold:.2f}). "
            f"Auto-Window: {peak_window_min_m:.2f}-{peak_window_max_m:.2f}mm "
            f"(margin={margin}mm, guard={guard}mm, min_width={enforced_min_width}mm)"
        )

        peak_start = max(start_pos, peak_window_min_m)
        peak_end = min(end_pos, peak_window_max_m)
        return FlyOverResult(peak_start, peak_end, max_stddev)

    def detect(
        self,
        start_pos: float,
        end_pos: float,
        clients,
        focus_profile: dict | None = None,
    ) -> FlyOverResult:
        """Run fly-over scan and return detected peak window."""
        roi_size = self._param_int("autofocus.fly_over.roi_size", 512)
        base_poll_s = self._param_float("autofocus.fly_over.detection_poll_s", 0.05)
        max_sample_step_mm = float(
            (focus_profile or {}).get(
                "max_sample_step_mm",
                self._param_float("autofocus.fly_over.max_sample_step_mm", 0.1),
            )
        )

        peak_ratio = self._param_float("autofocus.fly_over.peak_window_ratio", 0.5)
        if peak_ratio <= 0.0:
            peak_ratio = 0.5
        peak_ratio = min(0.95, max(0.05, peak_ratio))

        margin = self._param_float("autofocus.fly_over.peak_window_margin_mm", 8.0)
        backtrack = self._param_float("autofocus.fly_over.backtrack_mm", 8.0)
        guard = self._param_float("autofocus.fly_over.peak_window_guard_mm", 0.0)
        min_window_width = self._param_float(
            "autofocus.fly_over.min_peak_window_width_mm", 0.0
        )
        full_scan = self._param_bool("autofocus.fly_over.full_scan_for_peak", True)
        threshold = self._param_float(
            "autofocus.fly_over.detection_stddev_threshold", 0.0
        )

        vel_backup = clients["get_vel"].call(GetVelocityParameters.Request())
        if not vel_backup or not vel_backup.success:
            raise ServiceError("Failed to read velocity parameters")

        target_scan_speed = float(
            (focus_profile or {}).get(
                "scan_speed_mm_s",
                self._param_float("autofocus.fly_over.scan_speed_fast", 5.0),
            )
        )
        axis_speed_scale = float((focus_profile or {}).get("axis_speed_scale", 1.0))
        if axis_speed_scale <= 0:
            axis_speed_scale = 1.0
        cmd_scan_speed = max(0.01, target_scan_speed / axis_speed_scale)
        if vel_backup.max_velocity > 0 and cmd_scan_speed > vel_backup.max_velocity:
            cmd_scan_speed = float(vel_backup.max_velocity)
        effective_real_speed = max(0.01, cmd_scan_speed * axis_speed_scale)

        clients["move"].call(MoveAbsolute.Request(axis_position=float(start_pos)))
        self._wait_for_axis_idle(clients)

        frame_period_s = self._estimate_frame_period_s(timeout_s=0.8)
        if frame_period_s is not None and max_sample_step_mm > 0:
            speed_cap = max_sample_step_mm / frame_period_s
            if speed_cap > 0 and effective_real_speed > speed_cap:
                self._node.get_logger().warn(
                    f"Fly-Over speed capped by frame rate: {effective_real_speed:.2f} -> {speed_cap:.2f} mm/s "
                    f"(frame_period={frame_period_s:.3f}s, max_step={max_sample_step_mm:.3f}mm)"
                )
                effective_real_speed = speed_cap
                cmd_scan_speed = max(0.01, effective_real_speed / axis_speed_scale)
                if (
                    vel_backup.max_velocity > 0
                    and cmd_scan_speed > vel_backup.max_velocity
                ):
                    cmd_scan_speed = float(vel_backup.max_velocity)
                    effective_real_speed = max(0.01, cmd_scan_speed * axis_speed_scale)

        poll_s = min(
            base_poll_s,
            max(0.005, max_sample_step_mm / max(effective_real_speed, 1e-6)),
        )
        self._node.get_logger().info(
            f"Fly-Over Params: ratio={peak_ratio:.2f}, margin={margin:.2f}mm, backtrack={backtrack:.2f}mm, "
            f"guard={guard:.2f}mm, min_width={min_window_width:.2f}mm, "
            f"target_speed={target_scan_speed:.2f}mm/s cmd_speed={cmd_scan_speed:.2f}mm/s "
            f"est_real_speed={effective_real_speed:.2f}mm/s axis_scale={axis_speed_scale:.3f} poll={poll_s:.3f}s"
        )

        with temporary_velocity(clients, cmd_scan_speed, backup=vel_backup):
            scan_data = self._collect_scan_data(
                start_pos=float(start_pos),
                end_pos=float(end_pos),
                clients=clients,
                roi_size=roi_size,
                full_scan=full_scan,
                effective_real_speed=effective_real_speed,
                poll_s=poll_s,
            )

        return self._analyze_peak(
            scan_data=scan_data,
            start_pos=float(start_pos),
            end_pos=float(end_pos),
            peak_ratio=float(peak_ratio),
            margin=float(margin),
            backtrack=float(backtrack),
            guard=float(guard),
            min_window_width=float(min_window_width),
            threshold=float(threshold),
        )
