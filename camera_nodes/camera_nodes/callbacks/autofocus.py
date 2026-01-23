"""Autofocus callbacks with fly-over detection and refinement.

Process:
    1. Fly-Over: Fast scan over entire range → Peak detection via stddev
    2. Range Reduction: To 80-90% of max-stddev region
    3. Coarse Scan: 0.5mm steps in reduced range
    4. Fine Refinement: Depending on mode

Modes (refinement_mode):
    0 = Standard (iterative refinement)
    1 = HillClimbing (fast, early termination)
    2 = Parabolic (parabolic interpolation)

Separate Service:
    autofocus_comparison_callback: Runs all 3 modes sequentially
"""

import csv
from datetime import datetime
from pathlib import Path
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
    Autofocus,
    ParabolicAutofocus,
    IterativeParabolicAutofocus,
    GoldenSectionAutofocus,
    AdaptiveHillClimbingAutofocus,
    HillClimbingAutofocus,
    AutofocusConfig,
    Phase,
)
from .base import CallbackBase


# Konstanten
COARSE_STEP_MM = 0.5  # Fixer Coarse-Schritt
PEAK_WINDOW_RATIO = 0.85  # 85% des max stddev als Schwelle für Peak-Window
FLY_OVER_SPEED = 10.0  # mm/s für schnellen Fly-Over


class AutofocusCallbacks(CallbackBase):
    """Callbacks for autofocus with fly-over detection."""

    def autofocus_callback(self, request, response):
        """Autofocus with fly-over detection and refinement.
        
        Process:
            1. Fly-over across entire range
            2. Peak detection (80-90% max stddev)
            3. Coarse scan (0.5mm)
            4. Fine refinement based on mode
        
        Args:
            request.refinement_mode:
                0 = Standard (Golden Search)
                1 = HillClimbing (Adaptive)  
                2 = Parabolic (Iterative)
        """
        mode = getattr(request, 'refinement_mode', 0)
        start_time = time.time()
        
        self._node.get_logger().info(
            f'Autofocus: range {request.start_position}-{request.end_position}mm, mode={mode}'
        )

        try:
            # Validierung
            if request.start_position >= request.end_position:
                raise ConfigurationError('start_position must be < end_position')

            # Service Clients erstellen
            clients = self._get_all_axis_clients()
            
            # ══════════════════════════════════════════════════════════════
            # PHASE 1: Fly-Over Detection
            # ══════════════════════════════════════════════════════════════
            self._node.get_logger().info('Phase 1: Fly-Over Detection...')
            
            peak_start, peak_end, max_stddev = self._fly_over_detection(
                request.start_position, 
                request.end_position,
                clients
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
                mode, peak_start, peak_end, request, response, clients, start_time
            )

        except ConfigurationError as e:
            response.success = False
            response.message = f'WARNING: {str(e)}'
            self._node.get_logger().warn(response.message)

        except ServiceError as e:
            response.success = False
            response.message = f'WARNING: {str(e)}'
            self._node.get_logger().error(response.message)

        except ImageProcessingError as e:
            response.success = False
            response.message = f'WARNING: {str(e)}'
            self._node.get_logger().warn(response.message)

        except Exception as e:
            response.success = False
            response.message = f'ERROR: Autofocus failed: {str(e)}'
            self._node.get_logger().error(response.message)

        return response

    # ==========================================================================
    # AXIS CLIENT MANAGEMENT
    # ==========================================================================
    
    # ... (existing client methods skipped) ...

    def _get_all_axis_clients(self):
        """Creates all service clients for the linear axis."""
        x_axis_name = self._node.get_parameter('z_axis_node_name').value
        
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

    def _fly_over_detection(self, start_pos: float, end_pos: float, clients) -> tuple:
        """Fast fly-over scan for target detection.
        
        Returns:
            (peak_start, peak_end, max_stddev) or (None, None, 0) if no target
        """
        # Parameters
        roi_size = int(self._node.get_parameter('autofocus.fly_over.roi_size').value or 512)
        poll_s = float(self._node.get_parameter('autofocus.fly_over.detection_poll_s').value or 0.05)
        # Robust defaults: 50% threshold, 8mm margin, slower scan
        peak_ratio = float(self._node.get_parameter('autofocus.fly_over.peak_window_ratio').value or 0.5)
        # Force clamp to 0.5 if higher (override launch file old defaults)
        if peak_ratio > 0.5:
             self._node.get_logger().warn(f'Overriding configured peak_ratio {peak_ratio} -> 0.5')
             peak_ratio = 0.5

        margin = float(self._node.get_parameter('autofocus.fly_over.peak_window_margin_mm').value or 8.0)
        backtrack = float(self._node.get_parameter('autofocus.fly_over.backtrack_mm').value or 8.0)
        full_scan = bool(self._node.get_parameter('autofocus.fly_over.full_scan_for_peak').value)
        threshold = float(self._node.get_parameter('autofocus.fly_over.detection_stddev_threshold').value or 15.0)
        
        self._node.get_logger().info(
            f'Fly-Over Params: ratio={peak_ratio}, margin={margin}mm, backtrack={backtrack}mm, speed={scan_speed if "scan_speed" in locals() else "?"}'
        ) # scan_speed is defined later in try block, moving log call down in next step if needed or just accept simplistic log here.
        # Actually scan_speed is defined inside try block. I'll just log the params I have here.

        
        # Backup velocity
        vel_backup = clients['get_vel'].call(GetVelocityParameters.Request())
        if not vel_backup or not vel_backup.success:
            raise ServiceError('Failed to read velocity parameters')
        
        try:
            # Set fast scan velocity
            scan_speed = float(
                self._node.get_parameter('autofocus.fly_over.scan_speed_fast').value or 5.0
            )
            # Clamp to hardware max
            if vel_backup.max_velocity > 0 and scan_speed > vel_backup.max_velocity:
                scan_speed = float(vel_backup.max_velocity)

            vel_req = SetVelocityParameters.Request()
            vel_req.min_velocity = vel_backup.min_velocity
            vel_req.acceleration = vel_backup.acceleration
            vel_req.max_velocity = float(scan_speed)
            clients['set_vel'].call(vel_req)
            
            # Move to start
            clients['move'].call(MoveAbsolute.Request(axis_position=float(start_pos)))
            self._wait_for_axis_idle(clients)
            
            # Start fly-over scan
            clients['move'].call(MoveAbsolute.Request(axis_position=float(end_pos)))
            
            # State tracking
            scan_data = [] # List of (pos, stddev)
            
            scan_start_time = time.time()
            scan_start_pos = float(start_pos)
            end_tolerance = 0.1
            
            last_pos = None
            last_pos_time = time.time()
            last_log_time = time.time()
            
            # State tracking
            scan_data = [] # List of (pos, stddev)
            
            scan_start_time = time.time()
            scan_start_pos = float(start_pos)
            end_tolerance = 0.1
            
            last_pos = None
            last_pos_time = time.time()
            last_log_time = time.time()
            
            while True:
                # 1. Get Status (Sync) - Needed for loop termination
                status = clients['status'].call(GetOperationStatus.Request())
                if status and status.operation_status in ['error', 'emergency_stop']:
                    raise ServiceError('Axis error during fly-over')

                # 2. Get Position (Hybrid: Topic -> Service -> Estimate)
                current_pos = self._get_position(clients)
                
                # Update estimation reference
                if current_pos >= 0:
                    last_pos = current_pos
                    last_pos_time = time.time()
                
                # Fallback to estimation if position stale or missing
                use_estimate = False
                if current_pos < 0 or (time.time() - last_pos_time > 1.0):
                    use_estimate = True
                    elapsed = time.time() - scan_start_time
                    current_pos = max(start_pos, min(end_pos, scan_start_pos + (scan_speed * elapsed)))

                # 3. Process Image
                stddev = 0.0
                cv_image = self._get_latest_cv_image()
                if cv_image is not None:
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
            
            # Find global max
            best_sample = max(scan_data, key=lambda x: x[1])
            max_stddev_pos = best_sample[0]
            max_stddev = best_sample[1]
            
            # ABSOLUTE THRESHOLD logic: Everything > 2.5 is part of the peak area
            ABS_THRESHOLD = 2.5
            valid_points = [p for p, s in scan_data if s >= ABS_THRESHOLD]
            
            if not valid_points:
                 self._node.get_logger().warn(f'No point in fly-over exceeded threshold {ABS_THRESHOLD}.')
                 return None, None, max_stddev
            
            peak_window_min = min(valid_points)
            peak_window_max = max(valid_points)

            self._node.get_logger().info(
                f'Fly-Over: Peak at {max_stddev_pos:.2f}mm (std={max_stddev:.1f}). '
                f'Found {len(valid_points)} points >= {ABS_THRESHOLD}. '
                f'Auto-Window: {peak_window_min:.2f}-{peak_window_max:.2f}mm'
            )

            # Use absolute window without extra margins
            peak_start = max(start_pos, peak_window_min)
            peak_end = min(end_pos, peak_window_max)

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
                         request, response, clients, start_time: float):
        """Runs a single refinement mode."""
        
        self._node.get_logger().info(
            f'Phase 2: Coarse + Fine in {peak_start:.1f}-{peak_end:.1f}mm, mode={mode}'
        )
        
        # Erstelle Config mit reduzierter Range und fixem Coarse-Step
        config = AutofocusConfig(
            start_mm=float(peak_start),
            end_mm=float(peak_end),
            step_mm=COARSE_STEP_MM,
            use_sift_weighting=bool(getattr(request, 'use_sift_weighting', False))
        )
        
        # Wähle Algorithmus (Updated to new optimized classes)
        if mode == 1:
            af = AdaptiveHillClimbingAutofocus(config)
            mode_name = "AdaptiveHillClimbing"
        elif mode == 2:
            af = IterativeParabolicAutofocus(config)
            mode_name = "IterativeParabolic"
        else:
            af = GoldenSectionAutofocus(config)
            mode_name = "GoldenSection"
        
        # Run autofocus algorithm
        best_position, best_score, measurements = self._run_autofocus_loop(af, clients)
        
        # Move to best position
        if best_position is not None:
            clients['move'].call(MoveAbsolute.Request(axis_position=float(best_position)))
            self._wait_for_axis_idle(clients)
        
        duration = time.time() - start_time
        response.success = best_position is not None
        response.message = f'{mode_name}: pos={best_position:.3f}mm, score={best_score:.0f}'
        response.best_focus_position = float(best_position or 0)
        response.best_focus_value = float(best_score)
        response.total_measurements_taken = measurements
        response.duration_seconds = duration
        
        return response

    def _run_autofocus_loop(self, af, clients) -> tuple:
        """Runs the autofocus state machine.
        
        Returns:
            (best_position, best_score, measurements)
        """
        current_pos = float(af.start())
        clients['move'].call(MoveAbsolute.Request(axis_position=current_pos))
        self._wait_for_axis_idle(clients)
        time.sleep(0.1) # Settling time for stability
        
        best_position = None
        best_score = 0.0
        measurements = 0
        
        for _ in range(500):
            cv_image = self._get_latest_cv_image()
            if cv_image is None:
                time.sleep(0.1)
                cv_image = self._get_latest_cv_image()
            if cv_image is None:
                raise ImageProcessingError('No image available')
            
            result = af.process_image(current_pos, cv_image)
            best_score = result.best_score
            measurements += 1

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
            time.sleep(0.1) # Settling time for stability
            current_pos = next_pos
        
        return best_position, best_score, measurements

    def _run_comparison(self, peak_start: float, peak_end: float,
                        request, response, clients, start_time: float):
        """Runs all 3 modes sequentially and compares results."""
        
        self._node.get_logger().info('Comparison Test: Running all 3 modes...')
        
        results = {}
        
        for mode, name in [(0, 'standard'), (1, 'hillclimbing'), (2, 'parabolic')]:
            self._node.get_logger().info(f'--- Running {name.upper()} ---')
            
            config = AutofocusConfig(
                start_mm=float(peak_start),
                end_mm=float(peak_end),
                step_mm=COARSE_STEP_MM,
                use_sift_weighting=bool(getattr(request, 'use_sift_weighting', False))
            )
            
            if mode == 1:
                af = AdaptiveHillClimbingAutofocus(config)
            elif mode == 2:
                af = IterativeParabolicAutofocus(config)
            else:
                af = GoldenSectionAutofocus(config)
            
            mode_start = time.time()
            best_pos, best_score, measurements = self._run_autofocus_loop(af, clients)
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
        response.message = (
            f'Comparison: Best={best_algo} at {best["position"]:.3f}mm '
            f'(score={best["score"]:.0f}). CSV: {csv_path}'
        )
        response.best_focus_position = float(best['position'])
        response.best_focus_value = float(best['score'])
        response.total_measurements_taken = total_measurements
        response.duration_seconds = duration
        
        self._node.get_logger().info(f'Comparison results saved to {csv_path}')
        
        return response

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

        try:
            # Validierung
            if request.start_position >= request.end_position:
                raise ConfigurationError('start_position must be < end_position')

            # Service Clients
            clients = self._get_all_axis_clients()
            
            # Fly-Over Detection
            self._node.get_logger().info('Phase 1: Fly-Over Detection...')
            peak_start, peak_end, max_stddev = self._fly_over_detection(
                request.start_position, 
                request.end_position,
                clients
            )
            
            if peak_start is None or peak_end is None:
                raise ImageProcessingError('No target detected during fly-over')
            
            self._node.get_logger().info(
                f'Peak: {peak_start:.1f}-{peak_end:.1f}mm (max_stddev={max_stddev:.1f})'
            )
            
            # Run comparison
            return self._run_comparison(
                peak_start, peak_end, request, response, clients, start_time
            )

        except ConfigurationError as e:
            response.success = False
            response.message = f'WARNING: {str(e)}'
            self._node.get_logger().warn(response.message)

        except ServiceError as e:
            response.success = False
            response.message = f'WARNING: {str(e)}'
            self._node.get_logger().error(response.message)

        except ImageProcessingError as e:
            response.success = False
            response.message = f'WARNING: {str(e)}'
            self._node.get_logger().warn(response.message)

        except Exception as e:
            response.success = False
            response.message = f'ERROR: Comparison failed: {str(e)}'
            self._node.get_logger().error(response.message)

        return response

