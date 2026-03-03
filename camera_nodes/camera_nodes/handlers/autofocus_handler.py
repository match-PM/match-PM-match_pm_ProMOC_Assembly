"""Autofocus handler with fly-over detection and refinement.

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
import time

import cv2

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
from .focus_profile import FocusProfileBuilder
from .fly_over import FlyOverDetector
from promoc_core.error_handling import handle_service_errors

# Build algorithm lookup from centralized list
_ALGO_LOOKUP = {mode: (name, cls) for mode, name, cls in AUTOFOCUS_ALGORITHMS}


# Constants
COARSE_STEP_MM = 0.5  # Fixed coarse step size
FOURSTEP_APPROACH_OFFSET_MM = 0.5
FOURSTEP_SETTLE_S = 0.3
AUTOFOCUS_MAX_STEPS_DEFAULT = 500
AUTOFOCUS_NEW_IMAGE_TIMEOUT_S = 2.0


class AutofocusHandler(CallbackBase):
    """Handler for autofocus with fly-over detection."""

    def _build_focus_profile(self, request) -> dict:
        """Build objective-aware autofocus profile for fly-over and refinement."""
        return FocusProfileBuilder(self._node).build(request).as_dict()

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
            
        x_axis_name = self._param_str('x_axis_node_name', 'lts300_x_axis')
        
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
        """Fast fly-over scan for target detection."""
        detector = FlyOverDetector(
            node=self._node,
            get_latest_cv_image=self._get_latest_cv_image,
            get_center_roi=self._get_center_roi,
            wait_for_axis_idle=self._wait_for_axis_idle,
            get_position=self._get_position,
        )
        result = detector.detect(
            start_pos=float(start_pos),
            end_pos=float(end_pos),
            clients=clients,
            focus_profile=focus_profile,
        )
        return result.peak_start, result.peak_end, result.max_stddev

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
        refinement_samples = self._param_int('autofocus.refinement_samples', 51)
        refinement_shrink_factor = self._param_float('autofocus.refinement_shrink_factor', 0.35)
        coarse_step = float((focus_profile or {}).get('coarse_step_mm', COARSE_STEP_MM))
        min_step = float((focus_profile or {}).get('min_step_mm', self._param_float('autofocus.min_step_mm', 0.01)))

        config = AutofocusConfig(
            start_mm=range_start,
            end_mm=range_end,
            step_mm=coarse_step,
            refinement_samples=refinement_samples,
            min_step_mm=min_step,
            shrink_factor=refinement_shrink_factor,
            use_sift_weighting=bool(
                self._param_bool('autofocus.fly_over.use_sift_weighting', False)
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
                pre_pos = float(best_position) - FOURSTEP_APPROACH_OFFSET_MM
                # Clamp to requested range
                pre_pos = max(float(request.start_position), min(float(request.end_position), pre_pos))
                target_pos = max(float(request.start_position), min(float(request.end_position), target_pos))
                clients['move'].call(MoveAbsolute.Request(axis_position=pre_pos))
                self._wait_for_axis_idle(clients)
            clients['move'].call(MoveAbsolute.Request(axis_position=target_pos))
            self._wait_for_axis_idle(clients)

            # FourStep: measure once at the parabolic peak position
            if mode_name == 'fourstep':
                time.sleep(FOURSTEP_SETTLE_S)
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
                                pre_pos = float(best_position) - FOURSTEP_APPROACH_OFFSET_MM
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

        # Export measurement series for autofocus result inspection
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
        
        max_steps = AUTOFOCUS_MAX_STEPS_DEFAULT
        try:
            step_size = getattr(af, '_scan_step', af.config.step_mm)
            if step_size and af.config.end_mm > af.config.start_mm:
                max_steps = max(max_steps, int((af.config.end_mm - af.config.start_mm) / float(step_size)) + 5)
        except Exception:
            pass

        last_timestamp = 0
        
        for _ in range(max_steps):
            # Wait ensuring we get a NEW image frame
            cv_image, ts = self._wait_for_new_image(last_timestamp, timeout=AUTOFOCUS_NEW_IMAGE_TIMEOUT_S)
            
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
        
        refinement_samples = self._param_int('autofocus.refinement_samples', 51)
        refinement_shrink_factor = self._param_float('autofocus.refinement_shrink_factor', 0.35)
        coarse_step = float((focus_profile or {}).get('coarse_step_mm', COARSE_STEP_MM))
        min_step = float((focus_profile or {}).get('min_step_mm', self._param_float('autofocus.min_step_mm', 0.01)))
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
                    self._param_bool('autofocus.fly_over.use_sift_weighting', False)
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

