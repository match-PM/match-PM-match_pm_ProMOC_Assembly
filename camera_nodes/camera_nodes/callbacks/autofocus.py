"""Autofocus callbacks with fly-over detection and refinement.

Process:
    1. Fly-Over: Fast scan over entire range → Peak detection via stddev
    2. Range Reduction: To 80-90% of max-stddev region
    3. Coarse Scan: 0.5mm steps in reduced range
    4. Fine Refinement: Depending on mode

Modes (focus_mode):
    0 = Standard (iterative refinement)
    1 = HillClimbing (fast, early termination)
    2 = Parabolic (parabolic interpolation)

Separate Service:
    autofocus_comparison_callback: Runs all 3 modes sequentially
"""

import csv
from datetime import datetime
import json
import re
import time

import cv2
import numpy as np

from promoc_assembly_interfaces.srv import (
    GetOperationStatus,
    GetPosition,
    GetVelocityParameters,
    SetVelocityParameters,
    JogAxis,
    MoveAbsolute,
    Stop,
)
from promoc_core.promoc_exceptions import (
    ConfigurationError,
    ImageProcessingError,
    ServiceError,
)

from ..algorithms import (
    AutofocusConfig,
    AUTOFOCUS_ALGORITHMS,
)
from .base import CallbackBase

# Build algorithm lookup from centralized list
_ALGO_LOOKUP = {mode: (name, cls) for mode, name, cls in AUTOFOCUS_ALGORITHMS}


# Constants
COARSE_STEP_MM = 0.5  # Fixed coarse step size
PEAK_WINDOW_RATIO = 0.85  # 85% of max stddev as threshold for peak window
FLY_OVER_SPEED = 10.0  # mm/s for fast fly-over scan
from promoc_core.error_handling import handle_service_errors


class AutofocusCallbacks(CallbackBase):
    """Callbacks for autofocus with fly-over detection."""

    @staticmethod
    def _parse_objective_magnification_x(objective: str) -> float | None:
        """Extract numeric magnification from objective string (e.g. '6x', '4.5 X')."""
        text = str(objective or '').strip().lower()
        if not text:
            return None
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*x', text)
        if not match:
            match = re.search(r'(\d+(?:[.,]\d+)?)', text)
        if not match:
            return None
        try:
            return float(match.group(1).replace(',', '.'))
        except ValueError:
            return None

    @staticmethod
    def _normalize_profile_values(values: dict) -> dict:
        """Keep only numeric autofocus profile keys."""
        if not isinstance(values, dict):
            return {}
        out = {}
        for key in (
            'scan_speed_mm_s',
            'coarse_step_mm',
            'min_step_mm',
            'settle_s',
            'max_sample_step_mm',
            'axis_speed_scale',
        ):
            if key not in values:
                continue
            try:
                out[key] = float(values[key])
            except (TypeError, ValueError):
                continue
        return out

    @staticmethod
    def _magnification_tokens(mag_x: float | None) -> list[str]:
        """Generate possible magnification keys for profile lookup."""
        if mag_x is None or mag_x <= 0:
            return []
        tokens = []
        rounded = int(round(mag_x))
        if abs(mag_x - rounded) < 1e-3:
            tokens.append(f'{rounded}x')
        text = f'{mag_x:g}x'
        if text not in tokens:
            tokens.append(text)
        return tokens

    def _get_profile_overrides(self, mag_x: float | None, beamsplitter: bool) -> tuple[dict, str]:
        """Load optional autofocus profile overrides from JSON parameter."""
        raw = str(self._node.get_parameter('autofocus.profile_table_json').value or '').strip()
        if not raw:
            return {}, 'heuristic'
        try:
            table = json.loads(raw)
        except Exception as exc:
            self._node.get_logger().warn(f'Invalid autofocus.profile_table_json: {exc}')
            return {}, 'heuristic'
        if not isinstance(table, dict):
            return {}, 'heuristic'

        profiles = table.get('profiles', table)
        if not isinstance(profiles, dict):
            return {}, 'heuristic'

        merged = self._normalize_profile_values(table.get('default', {}))
        source = 'default'
        bs_key = 'bs1' if beamsplitter else 'bs0'

        mag_keys = self._magnification_tokens(mag_x)
        for key in mag_keys:
            if key in profiles:
                merged.update(self._normalize_profile_values(profiles[key]))
                source = key

        if bs_key in profiles:
            merged.update(self._normalize_profile_values(profiles[bs_key]))
            source = bs_key

        for key in mag_keys:
            combo = f'{key}_{bs_key}'
            if combo in profiles:
                merged.update(self._normalize_profile_values(profiles[combo]))
                source = combo

        return merged, source

    def _build_focus_profile(self, request) -> dict:
        """Build objective-aware autofocus profile for fly-over and refinement."""
        objective = str(self._node.get_parameter('measurement_conditions.camera_objective').value or '').strip()

        req_mag = float(getattr(request, 'objective_magnification_x', 0.0) or 0.0)
        beamsplitter = bool(getattr(request, 'use_beamsplitter', False))
        mag_x = req_mag if req_mag > 0 else self._parse_objective_magnification_x(objective)

        base_scan_speed = float(self._node.get_parameter('autofocus.fly_over.scan_speed_fast').value or FLY_OVER_SPEED)
        base_coarse_step = float(self._node.get_parameter('autofocus.fly_over.step_size_coarse').value or COARSE_STEP_MM)
        base_min_step = float(self._node.get_parameter('autofocus.min_step_mm').value or 0.01)
        base_settle_s = float(self._node.get_parameter('autofocus.fly_over.settle_fine_s').value or 0.1)
        base_max_sample_step = float(self._node.get_parameter('autofocus.fly_over.max_sample_step_mm').value or 0.1)
        base_axis_speed_scale = float(
            self._node.get_parameter('autofocus.fly_over.axis_speed_scale_default').value or 1.0
        )

        high_mag_threshold = float(self._node.get_parameter('autofocus.fly_over.high_mag_threshold_x').value or 4.0)
        very_high_mag_threshold = float(
            self._node.get_parameter('autofocus.fly_over.very_high_mag_threshold_x').value or 6.0
        )
        high_mag_scan_speed = float(self._node.get_parameter('autofocus.fly_over.scan_speed_high_mag').value or 2.0)
        very_high_mag_scan_speed = float(
            self._node.get_parameter('autofocus.fly_over.scan_speed_very_high_mag').value or 1.0
        )
        high_mag_coarse_step = float(self._node.get_parameter('autofocus.fly_over.coarse_step_high_mag_mm').value or 0.1)
        very_high_mag_coarse_step = float(
            self._node.get_parameter('autofocus.fly_over.coarse_step_very_high_mag_mm').value or 0.05
        )
        high_mag_min_step = float(self._node.get_parameter('autofocus.fly_over.min_step_high_mag_mm').value or 0.005)
        high_mag_settle_s = float(self._node.get_parameter('autofocus.fly_over.settle_high_mag_s').value or 0.2)
        very_high_mag_settle_s = float(self._node.get_parameter('autofocus.fly_over.settle_very_high_mag_s').value or 0.25)

        scan_speed = base_scan_speed
        coarse_step = base_coarse_step
        min_step = base_min_step
        settle_s = base_settle_s
        max_sample_step_mm = base_max_sample_step
        axis_speed_scale = max(1e-3, base_axis_speed_scale)

        if mag_x is not None:
            if mag_x >= very_high_mag_threshold:
                scan_speed = min(scan_speed, very_high_mag_scan_speed)
                coarse_step = min(coarse_step, very_high_mag_coarse_step)
                min_step = min(min_step, high_mag_min_step)
                settle_s = max(settle_s, very_high_mag_settle_s)
            elif mag_x >= high_mag_threshold:
                scan_speed = min(scan_speed, high_mag_scan_speed)
                coarse_step = min(coarse_step, high_mag_coarse_step)
                min_step = min(min_step, high_mag_min_step)
                settle_s = max(settle_s, high_mag_settle_s)

        profile_overrides, profile_source = self._get_profile_overrides(mag_x, beamsplitter)
        if 'scan_speed_mm_s' in profile_overrides and profile_overrides['scan_speed_mm_s'] > 0:
            scan_speed = profile_overrides['scan_speed_mm_s']
        if 'coarse_step_mm' in profile_overrides and profile_overrides['coarse_step_mm'] > 0:
            coarse_step = profile_overrides['coarse_step_mm']
        if 'min_step_mm' in profile_overrides and profile_overrides['min_step_mm'] > 0:
            min_step = profile_overrides['min_step_mm']
        if 'settle_s' in profile_overrides and profile_overrides['settle_s'] >= 0:
            settle_s = profile_overrides['settle_s']
        if 'max_sample_step_mm' in profile_overrides and profile_overrides['max_sample_step_mm'] > 0:
            max_sample_step_mm = profile_overrides['max_sample_step_mm']
        if 'axis_speed_scale' in profile_overrides and profile_overrides['axis_speed_scale'] > 0:
            axis_speed_scale = profile_overrides['axis_speed_scale']

        return {
            'objective': objective or 'unknown',
            'magnification_x': mag_x,
            'beamsplitter': beamsplitter,
            'profile_source': profile_source,
            'scan_speed_mm_s': max(0.01, float(scan_speed)),
            'coarse_step_mm': max(0.001, float(coarse_step)),
            'min_step_mm': max(0.001, float(min_step)),
            'settle_s': max(0.0, float(settle_s)),
            'max_sample_step_mm': max(0.005, float(max_sample_step_mm)),
            'axis_speed_scale': max(1e-3, float(axis_speed_scale)),
        }

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
        padded = np.pad(values, (half, half), mode='edge')
        smoothed = np.empty_like(values, dtype=np.float64)
        for i in range(values.size):
            smoothed[i] = float(np.median(padded[i:i + win]))
        return smoothed

    @staticmethod
    def _select_component_bounds(mask: np.ndarray, center_index: int) -> tuple[int, int] | None:
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
            key=lambda seg: _distance_to_segment(int(seg[0]), int(seg[1]))
        )
        return int(best[0]), int(best[1])

    @handle_service_errors()
    def autofocus_callback(self, request, response):
        """Autofocus with fly-over detection and refinement.
        
        Process:
            1. Fly-over across entire range
            2. Peak detection (80-90% max stddev)
            3. Coarse scan (0.5mm)
            4. Fine refinement based on mode
        
        Args:
            request.focus_mode:
                0 = Standard (Golden Section)
                1 = HillClimbing (Adaptive, fast)  
                2 = Parabolic (Iterative, precise)
                3 = Fibonacci (efficient search)
                4 = Exhaustive (brute-force, maximum precision reference)
        """
        mode = getattr(request, 'focus_mode', getattr(request, 'refinement_mode', 0))
        start_time = time.time()
        focus_profile = self._build_focus_profile(request)
        
        self._node.get_logger().info(
            f'Autofocus: range {request.start_position}-{request.end_position}mm, mode={mode}'
        )
        mag_label = (
            f'{focus_profile["magnification_x"]:.2f}x'
            if focus_profile["magnification_x"] is not None else 'unknown'
        )
        self._node.get_logger().info(
            f'Objective profile: objective="{focus_profile["objective"]}" '
            f'mag={mag_label} beamsplitter={focus_profile["beamsplitter"]} '
            f'profile={focus_profile["profile_source"]} '
            f'scan_speed={focus_profile["scan_speed_mm_s"]:.2f}mm/s '
            f'axis_scale={focus_profile["axis_speed_scale"]:.3f} '
            f'max_sample_step={focus_profile["max_sample_step_mm"]:.3f}mm '
            f'coarse_step={focus_profile["coarse_step_mm"]:.3f}mm min_step={focus_profile["min_step_mm"]:.3f}mm '
            f'settle={focus_profile["settle_s"]:.2f}s'
        )

        # Validierung
        if request.start_position >= request.end_position:
            raise ConfigurationError('start_position must be < end_position')

        # Service Clients erstellen
        clients = self._get_all_axis_clients()

        # ══════════════════════════════════════════════════════════════
        # PHASE 1: Fly-Over Detection (or skip if requested)
        # ══════════════════════════════════════════════════════════════
        skip_flyover = getattr(request, 'skip_flyover', False)
        
        if skip_flyover:
            self._node.get_logger().info('Skipping fly-over, using full range.')
            peak_start = float(request.start_position)
            peak_end = float(request.end_position)
        else:
            self._node.get_logger().info('Phase 1: Fly-Over Detection...')
            
            peak_start, peak_end, max_stddev = self._fly_over_detection(
                request.start_position, 
                request.end_position,
                clients,
                focus_profile
            )
            
            if peak_start is None or peak_end is None:
                raise ImageProcessingError('No target detected during fly-over')
            
            self._node.get_logger().info(
                f'Peak detected: {peak_start:.1f}-{peak_end:.1f}mm (max_stddev={max_stddev:.1f})'
            )
        
        # ══════════════════════════════════════════════════════════════
        # PHASE 2-4: Refinement nach Modus
        # ══════════════════════════════════════════════════════════════
        return self._run_single_mode(
            mode, peak_start, peak_end, request, response, clients, start_time, focus_profile
        )

    # ==========================================================================
    # AXIS CLIENT MANAGEMENT
    # ==========================================================================
    
    # ... (existing client methods skipped) ...

    def _get_all_axis_clients(self):
        """Creates or returns cached service clients for the linear axis."""
        # Return cached clients if available
        if hasattr(self, '_cached_axis_clients') and self._cached_axis_clients:
            return self._cached_axis_clients
            
        x_axis_name = self._node.get_parameter('x_axis_node_name').value
        
        clients = {
            'move': self._node.create_client(MoveAbsolute, f'/{x_axis_name}/move_absolute'),
            'jog': self._node.create_client(JogAxis, f'/{x_axis_name}/jog_axis'),
            'status': self._node.create_client(GetOperationStatus, f'/{x_axis_name}/get_operation_status'),
            'position': self._node.create_client(GetPosition, f'/{x_axis_name}/get_position'),
            'stop': self._node.create_client(Stop, f'/{x_axis_name}/stop'),
            'get_vel': self._node.create_client(GetVelocityParameters, f'/{x_axis_name}/get_velocity_parameters'),
            'set_vel': self._node.create_client(SetVelocityParameters, f'/{x_axis_name}/set_velocity_parameters'),
        }
        
        for name, client in clients.items():
            if not client.wait_for_service(timeout_sec=2.0):
                raise ServiceError(f'Linear axis {name} service not available')
        
        # Cache the clients to prevent resource leaks
        self._cached_axis_clients = clients
        return clients

    def _wait_for_axis_idle(self, clients):
        """Waits until the axis is idle."""
        while True:
            resp = clients['status'].call(GetOperationStatus.Request())
            if resp and resp.operation_status == 'idle':
                return
            if resp and resp.operation_status in ['error', 'emergency_stop']:
                raise ServiceError(f'Axis error: {resp.status_message}')
            time.sleep(0.05)

    def _get_position(self, clients) -> float:
        """Reads current position."""
        # Fast path: Use cached position from topic if available
        if hasattr(self._node, 'current_axis_position') and self._node.current_axis_position >= 0:
            return float(self._node.current_axis_position)

        # Fallback: Service call (blocking)
        resp = clients['position'].call(GetPosition.Request())
        if resp and resp.success:
            return float(resp.axis_position)
        return -1.0

    # ==========================================================================
    # FLY-OVER DETECTION
    # ==========================================================================

    def _fly_over_detection(self, start_pos: float, end_pos: float, clients, focus_profile: dict | None = None) -> tuple:
        """Fast fly-over scan for target detection.
        
        Returns:
            (peak_start, peak_end, max_stddev) or (None, None, 0) if no target
        """
        # Parameters
        roi_size = int(self._node.get_parameter('autofocus.fly_over.roi_size').value or 512)
        base_poll_s = float(self._node.get_parameter('autofocus.fly_over.detection_poll_s').value or 0.05)
        max_sample_step_mm = float(
            (focus_profile or {}).get(
                'max_sample_step_mm',
                self._node.get_parameter('autofocus.fly_over.max_sample_step_mm').value or 0.1
            )
        )
        # Robust defaults: 50% threshold, generous margin
        peak_ratio = float(self._node.get_parameter('autofocus.fly_over.peak_window_ratio').value or 0.5)
        if peak_ratio <= 0.0:
            peak_ratio = 0.5
        peak_ratio = min(0.95, max(0.05, peak_ratio))

        margin = float(self._node.get_parameter('autofocus.fly_over.peak_window_margin_mm').value or 8.0)
        backtrack = float(self._node.get_parameter('autofocus.fly_over.backtrack_mm').value or 8.0)
        full_scan = bool(self._node.get_parameter('autofocus.fly_over.full_scan_for_peak').value)
        threshold = float(self._node.get_parameter('autofocus.fly_over.detection_stddev_threshold').value or 0.0)
        
        # Backup velocity
        vel_backup = clients['get_vel'].call(GetVelocityParameters.Request())
        if not vel_backup or not vel_backup.success:
            raise ServiceError('Failed to read velocity parameters')
        
        try:
            # Set target real scan velocity (objective/profile aware)
            target_scan_speed = float(
                (focus_profile or {}).get(
                    'scan_speed_mm_s',
                    self._node.get_parameter('autofocus.fly_over.scan_speed_fast').value or 5.0
                )
            )
            axis_speed_scale = float((focus_profile or {}).get('axis_speed_scale', 1.0))
            if axis_speed_scale <= 0:
                axis_speed_scale = 1.0
            cmd_scan_speed = max(0.01, target_scan_speed / axis_speed_scale)
            if vel_backup.max_velocity > 0 and cmd_scan_speed > vel_backup.max_velocity:
                cmd_scan_speed = float(vel_backup.max_velocity)
            effective_real_speed = max(0.01, cmd_scan_speed * axis_speed_scale)

            # Move to start
            clients['move'].call(MoveAbsolute.Request(axis_position=float(start_pos)))
            self._wait_for_axis_idle(clients)

            frame_period_s = self._estimate_frame_period_s(timeout_s=0.8)
            if frame_period_s is not None and max_sample_step_mm > 0:
                speed_cap = max_sample_step_mm / frame_period_s
                if speed_cap > 0 and effective_real_speed > speed_cap:
                    self._node.get_logger().warn(
                        f'Fly-Over speed capped by frame rate: {effective_real_speed:.2f} -> {speed_cap:.2f} mm/s '
                        f'(frame_period={frame_period_s:.3f}s, max_step={max_sample_step_mm:.3f}mm)'
                    )
                    effective_real_speed = speed_cap
                    cmd_scan_speed = max(0.01, effective_real_speed / axis_speed_scale)
                    if vel_backup.max_velocity > 0 and cmd_scan_speed > vel_backup.max_velocity:
                        cmd_scan_speed = float(vel_backup.max_velocity)
                        effective_real_speed = max(0.01, cmd_scan_speed * axis_speed_scale)

            poll_s = min(base_poll_s, max(0.005, max_sample_step_mm / max(effective_real_speed, 1e-6)))
            self._node.get_logger().info(
                f'Fly-Over Params: ratio={peak_ratio:.2f}, margin={margin:.2f}mm, backtrack={backtrack:.2f}mm, '
                f'target_speed={target_scan_speed:.2f}mm/s cmd_speed={cmd_scan_speed:.2f}mm/s '
                f'est_real_speed={effective_real_speed:.2f}mm/s axis_scale={axis_speed_scale:.3f} poll={poll_s:.3f}s'
            )

            vel_req = SetVelocityParameters.Request()
            vel_req.min_velocity = vel_backup.min_velocity
            vel_req.acceleration = vel_backup.acceleration
            vel_req.max_velocity = float(cmd_scan_speed)
            clients['set_vel'].call(vel_req)
            
            # Start fly-over scan
            clients['move'].call(MoveAbsolute.Request(axis_position=float(end_pos)))
            
            # State tracking
            scan_data = []  # List of (pos, stddev)
            scan_start_time = time.time()
            scan_start_pos = float(start_pos)
            end_tolerance = 0.1
            last_pos = None
            last_pos_time = time.time()
            last_log_time = time.time()
            last_image_ts = None
            
            while True:
                # 1. Get Status (Sync) - Needed for loop termination
                status = clients['status'].call(GetOperationStatus.Request())
                if status and status.operation_status in ['error', 'emergency_stop']:
                    raise ServiceError('Axis error during fly-over')

                # 2. Get Position (Hybrid: Topic -> Service -> Estimate)
                current_pos = self._get_position(clients)
                
                # Update estimation reference
                if current_pos >= 0:
                    if last_pos is None or abs(current_pos - last_pos) > 1e-4:
                        last_pos = current_pos
                        last_pos_time = time.time()
                
                # Fallback to estimation if position stale or missing
                use_estimate = False
                if current_pos < 0 or (time.time() - last_pos_time > 1.0):
                    use_estimate = True
                    elapsed = time.time() - scan_start_time
                    current_pos = max(start_pos, min(end_pos, scan_start_pos + (effective_real_speed * elapsed)))

                # 3. Process Image
                stddev = 0.0
                cv_image, image_ts = self._get_latest_cv_image()
                if cv_image is not None and image_ts is not None and image_ts != last_image_ts:
                    last_image_ts = image_ts
                    green = cv_image[:, :, 1] if len(cv_image.shape) == 3 else cv_image
                    roi = self._get_center_roi(green, roi_size)
                    stddev = float(np.std(roi)) if roi.size > 0 else 0.0
                    
                    # Store data
                    scan_data.append((current_pos, stddev))
                    
                    # Log every 0.1s (10Hz)
                    if time.time() - last_log_time >= 0.1:
                        action_tag = "EST" if use_estimate else "REAL"
                        self._node.get_logger().info(f'Fly-Over [{action_tag}]: x={current_pos:.2f}mm std={stddev:.2f}')
                        last_log_time = time.time()
                
                # 4. Termination Check
                if status and status.operation_status == 'idle':
                    final_pos = self._get_position(clients)
                    if final_pos >= 0 and abs(final_pos - end_pos) <= end_tolerance:
                        break # Reached end
                    if full_scan: 
                        break
                    break
                
                time.sleep(poll_s)
            
            # Result Processing (Post-Scan)
            if not scan_data:
                 self._node.get_logger().warn('Fly-Over finished with no data.')
                 return None, None, 0.0
            
            # Sort by position for robust window extraction.
            scan_data.sort(key=lambda x: x[0])
            positions = np.array([p for p, _ in scan_data], dtype=np.float64)
            std_values_raw = np.array([s for _, s in scan_data], dtype=np.float64)

            smooth_window = int(
                self._node.get_parameter('autofocus.fly_over.smooth_window_samples').value or 5
            )
            baseline_percentile = float(
                self._node.get_parameter('autofocus.fly_over.baseline_percentile').value or 20.0
            )
            baseline_percentile = min(50.0, max(0.0, baseline_percentile))
            snr_threshold = float(
                self._node.get_parameter('autofocus.fly_over.snr_threshold').value or 3.0
            )
            snr_threshold = max(0.5, snr_threshold)

            std_values_smooth = self._median_smooth_1d(std_values_raw, smooth_window)
            # Envelope preserves narrow true peaks that can be attenuated by median smoothing.
            std_values_eval = np.maximum(std_values_smooth, std_values_raw)

            smooth_peak_index = int(np.argmax(std_values_smooth))
            raw_peak_index = int(np.argmax(std_values_raw))
            smooth_peak_value = float(std_values_smooth[smooth_peak_index])
            raw_peak_value = float(std_values_raw[raw_peak_index])

            if raw_peak_value >= smooth_peak_value:
                peak_index = raw_peak_index
                peak_source = 'raw'
            else:
                peak_index = smooth_peak_index
                peak_source = 'smooth'

            max_stddev_pos = float(positions[peak_index])
            max_stddev = float(std_values_eval[peak_index])

            # Adaptive ratio threshold on evaluation curve.
            baseline_stddev = float(np.percentile(std_values_eval, baseline_percentile))
            dynamic_threshold = baseline_stddev + (max_stddev - baseline_stddev) * peak_ratio
            dynamic_threshold = min(max_stddev, max(0.0, dynamic_threshold))

            # Robust noise estimate from residuals (raw - smooth).
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
                        f'Ignoring absolute stddev threshold={threshold:.2f} '
                        f'because peak is only {max_stddev:.2f}.'
                    )

            if not np.any(valid_mask):
                valid_mask = ratio_mask
            if not np.any(valid_mask):
                valid_mask = snr_mask
            if not np.any(valid_mask):
                self._node.get_logger().warn(
                    f'No point in fly-over exceeded robust criteria '
                    f'(ratio={dynamic_threshold:.2f}, snr={snr_threshold:.2f}).'
                )
                return None, None, max_stddev

            segment_bounds = self._select_component_bounds(valid_mask, peak_index)
            if segment_bounds is None:
                self._node.get_logger().warn('No connected valid segment around fly-over peak.')
                return None, None, max_stddev

            seg_start, seg_end = segment_bounds
            peak_window_min = float(positions[seg_start])
            peak_window_max = float(positions[seg_end])

            # Apply margin (extra start-side backtrack for safe approach)
            peak_window_min_m = peak_window_min - max(margin, backtrack)
            peak_window_max_m = peak_window_max + margin

            self._node.get_logger().info(
                f'Fly-Over: Peak at {max_stddev_pos:.2f}mm (std={max_stddev:.2f}, source={peak_source}, '
                f'raw_max={raw_peak_value:.2f}@{positions[raw_peak_index]:.2f}mm, '
                f'smooth_max={smooth_peak_value:.2f}@{positions[smooth_peak_index]:.2f}mm). '
                f'Window points={int(np.count_nonzero(valid_mask))} '
                f'(ratio_thr={dynamic_threshold:.2f}, baseline={baseline_stddev:.2f}, '
                f'noise_sigma={noise_sigma:.3f}, snr_thr={snr_threshold:.2f}). '
                f'Auto-Window: {peak_window_min_m:.2f}-{peak_window_max_m:.2f}mm (margin={margin}mm)'
            )

            # Clamp scan window to physical limits
            peak_start = max(start_pos, peak_window_min_m)
            peak_end = min(end_pos, peak_window_max_m)

            return peak_start, peak_end, max_stddev
            
        finally:
            # Restore velocity
            restore_req = SetVelocityParameters.Request()
            restore_req.min_velocity = vel_backup.min_velocity
            restore_req.acceleration = vel_backup.acceleration
            restore_req.max_velocity = vel_backup.max_velocity
            clients['set_vel'].call(restore_req)

    # ==========================================================================
    # REFINEMENT MODES
    # ==========================================================================

    def _run_single_mode(self, mode: int, peak_start: float, peak_end: float,
                         request, response, clients, start_time: float, focus_profile: dict | None = None):
        """Runs a single refinement mode."""
        
        self._node.get_logger().info(
            f'Phase 2: Coarse + Fine in {peak_start:.1f}-{peak_end:.1f}mm, mode={mode}'
        )
        
        # Select algorithm based on mode (using centralized lookup)
        mode_name, algo_class = _ALGO_LOOKUP.get(mode, _ALGO_LOOKUP[0])

        # Use full requested range for exhaustive/twostage, otherwise peak window
        if mode_name in ['exhaustive', 'twostage']:
            range_start = float(request.start_position)
            range_end = float(request.end_position)
        else:
            range_start = float(peak_start)
            range_end = float(peak_end)

        # Erstelle Config mit reduzierter Range und fixem Coarse-Step
        refinement_samples = int(self._node.get_parameter('autofocus.refinement_samples').value or 51)
        refinement_shrink_factor = float(self._node.get_parameter('autofocus.refinement_shrink_factor').value or 0.35)
        coarse_step = float((focus_profile or {}).get('coarse_step_mm', COARSE_STEP_MM))
        min_step = float((focus_profile or {}).get('min_step_mm', self._node.get_parameter('autofocus.min_step_mm').value or 0.01))

        config = AutofocusConfig(
            start_mm=range_start,
            end_mm=range_end,
            step_mm=coarse_step,
            refinement_samples=refinement_samples,
            min_step_mm=min_step,
            shrink_factor=refinement_shrink_factor,
            use_sift_weighting=bool(
                self._node.get_parameter('autofocus.fly_over.use_sift_weighting').value
            )
        )
        af = algo_class(config)
        
        # Run autofocus algorithm
        save_best_image = bool(getattr(request, 'save_best_image', False))
        settle_s = float((focus_profile or {}).get('settle_s', 0.1))
        if save_best_image:
            best_position, best_score, measurements, best_image = self._run_autofocus_loop(
                af, clients, return_best_image=True, settle_s=settle_s
            )
        else:
            best_position, best_score, measurements = self._run_autofocus_loop(af, clients, settle_s=settle_s)
            best_image = None

        if mode_name == 'fourstep' and hasattr(af, 'parabolic_peak_mm'):
            peak_mm = getattr(af, 'parabolic_peak_mm', None)
            fit_points = getattr(af, 'parabolic_fit_points', [])
            if peak_mm is not None:
                self._node.get_logger().info(
                    f'FOURSTEP Parabolic Peak: {peak_mm:.6f}mm (fit_points={len(fit_points)}) '
                    f'final_best={best_position:.6f}mm'
                )
        
        # Move to best position (FourStep: approach from below to reduce backlash)
        if best_position is not None:
            target_pos = float(best_position)
            if mode_name == 'fourstep':
                offset = 0.5
                pre_pos = float(best_position) - offset
                # Clamp to requested range
                pre_pos = max(float(request.start_position), min(float(request.end_position), pre_pos))
                target_pos = max(float(request.start_position), min(float(request.end_position), target_pos))
                clients['move'].call(MoveAbsolute.Request(axis_position=pre_pos))
                self._wait_for_axis_idle(clients)
            clients['move'].call(MoveAbsolute.Request(axis_position=target_pos))
            self._wait_for_axis_idle(clients)

            # FourStep: measure once at the parabolic peak position
            if mode_name == 'fourstep':
                time.sleep(0.3)
                cv_image, _ = self._get_latest_cv_image()
                if cv_image is not None:
                    try:
                        prior_best_score = best_score
                        final_score = float(af._calculate_score(cv_image))
                        if final_score >= prior_best_score:
                            best_score = final_score
                            if save_best_image:
                                best_image = cv_image
                        else:
                            # Keep previous best and re-approach target position
                            if mode_name == 'fourstep':
                                offset = 0.5
                                pre_pos = float(best_position) - offset
                                pre_pos = max(float(request.start_position), min(float(request.end_position), pre_pos))
                                clients['move'].call(MoveAbsolute.Request(axis_position=pre_pos))
                                self._wait_for_axis_idle(clients)
                            clients['move'].call(MoveAbsolute.Request(axis_position=target_pos))
                            self._wait_for_axis_idle(clients)

                        self._node.get_logger().info(
                            f'FOURSTEP peak measurement: pos={target_pos:.3f}mm score={final_score:.0f} '
                            f'(kept_best={best_score:.0f})'
                        )
                    except Exception:
                        pass
        
        duration = time.time() - start_time
        response.success = best_position is not None
        response.status_message = f'{mode_name}: pos={best_position:.3f}mm, score={best_score:.0f}'
        response.best_focus_position = float(best_position or 0)
        response.best_focus_value = float(best_score)
        response.total_measurements_taken = measurements
        response.duration_seconds = duration
        response.best_image_path = ''
        response.measurement_positions = []
        response.measurement_scores = []

        if save_best_image and best_image is not None:
            out_prefix = f'autofocus_best_{mode_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            out_path = self._get_output_dir('autofocus_results')
            out_path.mkdir(parents=True, exist_ok=True)
            img_path = out_path / f'{out_prefix}.jpg'
            cv2.imwrite(str(img_path), best_image)
            response.best_image_path = str(img_path)
            self._node.get_logger().info(f'Saved best image: {img_path}')

        # Export measurement series for verification
        try:
            measurements = getattr(af, '_measurements', []) or []
            response.measurement_positions = [float(m.position_mm) for m in measurements]
            response.measurement_scores = [float(m.score) for m in measurements]
        except Exception:
            response.measurement_positions = []
            response.measurement_scores = []
        
        return response

    def _run_autofocus_loop(self, af, clients, return_best_image: bool = False, settle_s: float = 0.1) -> tuple:
        """Runs the autofocus state machine.
        
        Returns:
            (best_position, best_score, measurements) or
            (best_position, best_score, measurements, best_image)
        """
        current_pos = float(af.start())
        clients['move'].call(MoveAbsolute.Request(axis_position=current_pos))
        self._wait_for_axis_idle(clients)
        time.sleep(max(0.0, float(settle_s))) # Settling time for stability
        
        best_position = None
        best_score = 0.0
        best_image = None
        best_current_score = -1.0
        measurements = 0
        
        max_steps = 500
        try:
            step_size = getattr(af, '_scan_step', af.config.step_mm)
            if step_size and af.config.end_mm > af.config.start_mm:
                max_steps = max(max_steps, int((af.config.end_mm - af.config.start_mm) / float(step_size)) + 5)
        except Exception:
            pass

        last_timestamp = 0
        
        for _ in range(max_steps):
            # Wait ensuring we get a NEW image frame
            cv_image, ts = self._wait_for_new_image(last_timestamp, timeout=2.0)
            
            if cv_image is None:
                self._node.get_logger().error("Timeout waiting for new image in AF loop - Stream stalled?")
                raise ImageProcessingError('Autofocus failed: Camera stream stalled (no new images)')
            
            if ts is not None:
                last_timestamp = ts
            
            result = af.process_image(current_pos, cv_image)
            best_score = result.best_score
            measurements += 1

            if return_best_image and result.current_score is not None:
                if result.current_score > best_current_score:
                    best_current_score = result.current_score
                    best_image = cv_image.copy()

            phase = getattr(result, 'phase', None)
            phase_name = phase.name if phase is not None else 'UNKNOWN'
            self._node.get_logger().info(
                f'AF {phase_name}: pos={current_pos:.3f}mm score={result.current_score:.0f} '
                f'best={best_score:.0f}'
            )
            
            if result.finished:
                best_position = result.best_position_mm
                self._node.get_logger().info(
                    f'AF complete: best_pos={best_position:.3f}mm best_score={best_score:.0f} '
                    f'measurements={measurements}'
                )
                break
            
            if result.next_position_mm is None:
                break
            
            next_pos = float(result.next_position_mm)
            clients['move'].call(MoveAbsolute.Request(axis_position=next_pos))
            self._wait_for_axis_idle(clients)
            time.sleep(max(0.0, float(settle_s))) # Settling time for stability
            current_pos = next_pos
        
        if best_position is None and hasattr(af, '_best_measurement') and af._best_measurement:
            best_position = af._best_measurement.position_mm
            best_score = af._best_measurement.score

        if return_best_image:
            return best_position, best_score, measurements, best_image

        return best_position, best_score, measurements

    def _run_comparison(self, peak_start: float, peak_end: float,
                        request, response, clients, start_time: float, focus_profile: dict | None = None):
        """Runs all 5 modes sequentially and compares results."""
        
        self._node.get_logger().info('Comparison Test: Running all 5 modes...')
        
        results = {}
        
        refinement_samples = int(self._node.get_parameter('autofocus.refinement_samples').value or 51)
        refinement_shrink_factor = float(self._node.get_parameter('autofocus.refinement_shrink_factor').value or 0.35)
        coarse_step = float((focus_profile or {}).get('coarse_step_mm', COARSE_STEP_MM))
        min_step = float((focus_profile or {}).get('min_step_mm', self._node.get_parameter('autofocus.min_step_mm').value or 0.01))
        settle_s = float((focus_profile or {}).get('settle_s', 0.1))

        # Use centralized algorithm list
        for mode, name, algo_class in AUTOFOCUS_ALGORITHMS:
            self._node.get_logger().info(f'--- Running {name.upper()} (mode {mode}) ---')
            
            config = AutofocusConfig(
                start_mm=float(peak_start),
                end_mm=float(peak_end),
                step_mm=coarse_step,
                refinement_samples=refinement_samples,
                min_step_mm=min_step,
                shrink_factor=refinement_shrink_factor,
                use_sift_weighting=bool(
                    self._node.get_parameter('autofocus.fly_over.use_sift_weighting').value
                )
            )
            
            af = algo_class(config)
            
            mode_start = time.time()
            best_pos, best_score, measurements = self._run_autofocus_loop(af, clients, settle_s=settle_s)
            mode_duration = time.time() - mode_start
            
            results[name] = {
                'position': best_pos or 0,
                'score': best_score,
                'duration': mode_duration,
                'measurements': measurements,
            }
            
            self._node.get_logger().info(
                f'{name}: pos={best_pos:.3f}mm, score={best_score:.0f}, time={mode_duration:.1f}s'
            )
        
        # Export CSV
        output_dir = self._get_output_dir('autofocus_comparison')
        csv_path = output_dir / f'comparison_{self._get_timestamp()}.csv'
        
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['# Autofocus Comparison Test'])
            writer.writerow([f'# Range: {peak_start:.1f}-{peak_end:.1f}mm (after fly-over)'])
            writer.writerow([])
            writer.writerow(['algorithm', 'position_mm', 'score', 'duration_s', 'measurements'])
            for algo, data in results.items():
                writer.writerow([
                    algo,
                    f"{data['position']:.4f}",
                    f"{data['score']:.0f}",
                    f"{data['duration']:.2f}",
                    data['measurements']
                ])
        
        # Find best
        best_algo = max(results.keys(), key=lambda k: results[k]['score'])
        best = results[best_algo]
        
        # Move to best position
        if best['position'] > 0:
            clients['move'].call(MoveAbsolute.Request(axis_position=float(best['position'])))
            self._wait_for_axis_idle(clients)
        
        duration = time.time() - start_time
        total_measurements = sum(r['measurements'] for r in results.values())
        
        response.success = True
        response.status_message = (
            f'Comparison: Best={best_algo} at {best["position"]:.3f}mm '
            f'(score={best["score"]:.0f}). CSV: {csv_path}'
        )
        response.best_focus_position = float(best['position'])
        response.best_focus_value = float(best['score'])
        response.total_measurements_taken = total_measurements
        response.duration_seconds = duration
        
        self._node.get_logger().info(f'Comparison results saved to {csv_path}')
        
        return response

    @handle_service_errors()
    def autofocus_comparison_callback(self, request, response):
        """Separate service: Runs all 3 autofocus modes sequentially.
        
        Process:
            1. Fly-over detection (same as regular autofocus)
            2. Standard autofocus
            3. HillClimbing autofocus
            4. Parabolic autofocus
            5. Exports comparison CSV
        """
        start_time = time.time()
        
        self._node.get_logger().info(
            f'Comparison Test: range {request.start_position}-{request.end_position}mm'
        )

        # Validierung
        if request.start_position >= request.end_position:
            raise ConfigurationError('start_position must be < end_position')

        # Service Clients
        clients = self._get_all_axis_clients()
        focus_profile = self._build_focus_profile(request)

        # Fly-Over Detection
        self._node.get_logger().info('Phase 1: Fly-Over Detection...')
        peak_start, peak_end, max_stddev = self._fly_over_detection(
            request.start_position, 
            request.end_position,
            clients,
            focus_profile
        )
        
        if peak_start is None or peak_end is None:
            raise ImageProcessingError('No target detected during fly-over')
        
        self._node.get_logger().info(
            f'Peak: {peak_start:.1f}-{peak_end:.1f}mm (max_stddev={max_stddev:.1f})'
        )
        
        # Run comparison
        return self._run_comparison(
            peak_start, peak_end, request, response, clients, start_time, focus_profile
        )
