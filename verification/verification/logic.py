import time
import csv
from datetime import datetime
from pathlib import Path
import numpy as np
import cv2

from promoc_assembly_interfaces.srv import (
    MoveAbsolute,
    GetPosition,
    GetOperationStatus,
    # MeasureMTF, # Not used directly
    SetVelocityParameters,
    GetVelocityParameters,
    JogAxis,
    Stop
)
from promoc_assembly_interfaces.msg import LinearAxisInfo

from .algorithms import (
    AutofocusConfig,
    AUTOFOCUS_ALGORITHMS,
    MTFAnalyzer,
    MTFConfig
)
from .algorithms.image_metrics import ImageMetrics
from camera_nodes.algorithms.roi_detection import RoiDetector
from .algorithms.statistics import calculate_uncertainty_budget
from ament_index_python.packages import get_package_share_directory
import yaml
import os

class VerificationLogic:
    """
    Business logic for the Verification Pipeline.
    
    Handles control flow between hardware (axes, camera) and algorithms 
    (autofocus, MTF analysis).
    """
    def __init__(self, node, clients, system_config=None):
        self.node = node
        self.clients = clients
        self.log = node.get_logger()
        self.system_config = system_config or {}
        self.camera_calibration = self._load_calibration_data()

    def _get_timestamp(self):
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _check_services(self):
        """Checks if all critical services are available."""
        timeout_sec = 2.0
        for name, client in self.clients.items():
            if not client.wait_for_service(timeout_sec=timeout_sec):
                self.log.error(f"Service {name} unavailable after {timeout_sec}s")
                raise RuntimeError(f"Service {name} unavailable")

    def _wait_for_axis_idle(self):
        """Waits until the axis is idle with improved error handling."""
        timeout = 30.0
        start = time.time()
        while time.time() - start < timeout:
            if not self.clients['status'].wait_for_service(timeout_sec=1.0):
                 raise RuntimeError("Status service lost connection")
                 
            resp = self.clients['status'].call(GetOperationStatus.Request())
            if resp and resp.operation_status == 'idle':
                return
            if resp and resp.operation_status in ['error', 'emergency_stop']:
                raise RuntimeError(f'Axis error: {resp.status_message}')
            time.sleep(0.05)
        raise RuntimeError("Timeout waiting for axis idle")

    def _get_latest_image(self):
        """Retrieves and converts the latest image from the orchestrator node."""
        if hasattr(self.node, 'latest_image_msg') and self.node.latest_image_msg:
             from cv_bridge import CvBridge
             bridge = CvBridge()
             try:
                 return bridge.imgmsg_to_cv2(self.node.latest_image_msg, desired_encoding='mono8')
             except Exception:
                 # Try bgr8 and convert
                 img = bridge.imgmsg_to_cv2(self.node.latest_image_msg, desired_encoding='bgr8')
                 return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return None

    def _load_calibration_data(self):
        """Load camera calibration data if configured."""
        try:
            cam_config = self.system_config.get('camera', {})
            calib_file = cam_config.get('calibration_file')
            
            if not calib_file:
                return None
                
            # Resolve package:// URI
            if calib_file.startswith('package://'):
                parts = calib_file.replace('package://', '').split('/', 1)
                pkg_name = parts[0]
                rel_path = parts[1]
                try:
                    pkg_path = get_package_share_directory(pkg_name)
                    full_path = Path(pkg_path) / rel_path
                    
                    # --- Dev Environment Fallback ---
                    # If package is not installed (source build), try to infer path from current file loc
                    if not full_path.exists():
                        # Assumption: we are in <workspace>/src/.../verification/verification/logic.py
                        # We want to find <workspace>/<pkg_name>/<rel_path>
                        # Go up 4 levels: logic.py -> verification -> verification -> src -> workspace? 
                        # This is fragile but helpful for local dev without install.
                        repo_root = Path(__file__).parent.parent.parent.parent
                        potential_path = repo_root / pkg_name / rel_path
                        if potential_path.exists():
                             full_path = potential_path
                             self.log.info(f"Found config in source tree: {full_path}")
                except Exception:
                     # Fallback to absolute check if it looks like one
                     full_path = Path(calib_file)
            else:
                full_path = Path(calib_file)
                
            if not full_path.exists():
                self.log.warn(f"Calibration file not found: {full_path}")
                return None

                
            self.log.info(f"Loading calibration from: {full_path}")
            with open(full_path, 'r') as f:
                calib_data = yaml.safe_load(f)
            
            # Smart parsing: Handle both standard ROS calibration file (camera_matrix at root)
            # and nested config file (camera_info key)
            if 'camera_info' in calib_data:
                # Nested structure
                matrix_data = calib_data['camera_info']['camera_matrix']['data']
                dist_data = calib_data['camera_info']['distortion_coefficients']['data']
            else:
                # Flat structure (standard from camera_calibration_parsers?)
                # Or standard YAML output which usually has camera_matrix at top
                if 'camera_matrix' in calib_data:
                     matrix_data = calib_data['camera_matrix']['data']
                     dist_data = calib_data['distortion_coefficients']['data']
                else:
                    self.log.warn("Invalid calibration file format: missing camera_matrix")
                    return None

            # Parse OpenCV matrices
            camera_matrix = np.array(matrix_data).reshape(3, 3)
            dist_coeffs = np.array(dist_data)
            
            return {
                'camera_matrix': camera_matrix,
                'dist_coeffs': dist_coeffs
            }
            
        except Exception as e:
            self.log.error(f"Failed to load calibration data: {e}")
            return None

    def _run_autofocus_loop(self, af):
        """Runs the autofocus state machine locally."""
        current_pos = float(af.start())
        self.clients['move'].call(MoveAbsolute.Request(axis_position=current_pos))
        self._wait_for_axis_idle()
        time.sleep(0.2) # Settling time
        
        best_position = None
        best_score = 0.0
        measurements = 0
        
        for _ in range(500):
            img = self._get_latest_image()
            if img is None:
                time.sleep(0.1)
                img = self._get_latest_image()
            if img is None:
                self.log.error("No image available for AF loop")
                break
            
            result = af.process_image(current_pos, img)
            best_score = result.best_score
            measurements += 1

            if result.finished:
                best_position = result.best_position_mm
                break
            
            if result.next_position_mm is None:
                break
            
            next_pos = float(result.next_position_mm)
            self.clients['move'].call(MoveAbsolute.Request(axis_position=next_pos))
            self._wait_for_axis_idle()
            time.sleep(0.1)
            current_pos = next_pos
        
        return best_position, best_score, measurements

    def run_autofocus_verification(self, config):
        """
        Runs autofocus comparison verification.
        config: dict with keys 'start_pos', 'end_pos', 'step_size', 'repetitions'
        """
        results = []
        
        start_pos = config.get('start_pos', 0.0)
        end_pos = config.get('end_pos', 10.0)
        step_size = config.get('step_size', 0.5)
        repetitions = config.get('repetitions', 3)
        
        algorithms = AUTOFOCUS_ALGORITHMS.copy()
        # Always include exhaustive for ground truth in the first run if possible, 
        # or maybe we should make it optional via config? 
        # For now, let's assume we want to test all defined algorithms.
        # Check if exhaustive is too slow? User can decide via logic, but here we run all.
        
        reference_pos = None

        # 2. Test Candidates (include exhaustive again)
        candidates = algorithms
        
        # Define start point strategies
        range_span = end_pos - start_pos
        mid_point = start_pos + range_span / 2.0
        
        exhaustive_runs = {0, max(0, repetitions // 2), max(0, repetitions - 1)}

        for rep in range(repetitions):
            rep_idx = rep + 1
            start_strategies = []
            if reference_pos:
                start_strategies = [
                    ('optimum', reference_pos),
                    ('offset_neg', max(start_pos, reference_pos - 1.0)),
                    ('offset_pos', min(end_pos, reference_pos + 1.0))
                ]
            else:
                # Fallback if no ref: Start, Middle, End
                start_strategies = [
                    ('start', start_pos),
                    ('middle', mid_point),
                    ('end', end_pos)
                ]
            
            for strat_name, strat_pos in start_strategies:
                self.log.info(f"--- AF Verification Rep {rep_idx} (Start: {strat_name}) ---")
                
                # Move to start position first
                self.clients['move'].call(MoveAbsolute.Request(axis_position=strat_pos))
                self._wait_for_axis_idle()
                
                if rep in exhaustive_runs:
                    exhaustive_first = [a for a in candidates if a[1] == 'exhaustive']
                    other_algos = [a for a in candidates if a[1] != 'exhaustive']
                    run_list = exhaustive_first + other_algos
                else:
                    run_list = [a for a in candidates if a[1] != 'exhaustive']

                for _, name, algo_cls in run_list:
                    algo_config = AutofocusConfig(start_mm=start_pos, end_mm=end_pos, step_mm=step_size)
                    af = algo_cls(algo_config)
                    
                    start_t = time.time()
                    best_pos, best_score, count = self._run_autofocus_loop(af)
                    duration = time.time() - start_t
                    
                    dev = 0.0
                    success = False
                    if best_pos is not None:
                        if reference_pos:
                            dev = best_pos - reference_pos
                            success = abs(dev) < 0.02 
                        else:
                            success = True
                    
                    res = {
                        'algorithm': name,
                        'repetition': rep_idx,
                        'start_strategy': strat_name,
                        'start_pos_mm': strat_pos,
                        'focus_position_mm': best_pos,
                        'focus_score': best_score,
                        'duration_s': duration,
                        'measurements': count,
                        'deviation_from_ref_mm': dev,
                        'success': success
                    }
                    results.append(res)
                    self.log.info(f"{name} ({strat_name}): Pos={best_pos} Dev={dev:.4f}mm Success={success}")

        return results, reference_pos

    def run_mtf_verification(self, repetitions=10):
        """
        Runs MTF verification with multiple repetitions for statistical relevance.
        repetitions: Number of measurements to take
        """
        if repetitions < 1: repetitions = 1
        
        mtf_results = []
        
        self.log.info(f"Starting MTF Measurement Series (N={repetitions})...")
        
        for i in range(repetitions):
            img = self._get_latest_image()
            if img is None:
                self.log.error(f"No image for MTF measurement {i+1}")
                continue
                
            # Prepare Analyzer with calibration if available
            pixel_size = self.system_config.get('camera', {}).get('pixel_size_um', 2.40)
            
            calib_args = {}
            if self.camera_calibration:
                calib_args['camera_matrix'] = self.camera_calibration['camera_matrix']
                calib_args['dist_coeffs'] = self.camera_calibration['dist_coeffs']
            
            config = MTFConfig(pixel_size_um=pixel_size)
            analyzer = MTFAnalyzer(config, **calib_args)
            
            # ROI: Center for now
            h, w = img.shape[:2]
            # TODO: Better ROI detection or use fixed center crop
            # We assume a slanted edge is roughly in the center
            
            # Using compute_mtf which handles full image or ROI
            # Let's crop center 50% to avoid noise from edges
            cy, cx = h // 2, w // 2
            crop_h, crop_w = h // 2, w // 2
            
            # Pass full image with ROI to analyzer
            # analyzer.compute_mtf will undistort full image if calibration is present, then extract ROI
            roi_rect = (cx-crop_w//2, cy-crop_h//2, cx+crop_w//2, cy+crop_h//2)
            
            res = analyzer.compute_mtf(img, roi=roi_rect)
            
            if res.valid:
                mtf_results.append({
                    'mtf50': res.mtf50,
                    'mtf20': res.mtf20,
                    'mtf10': res.mtf10,
                    'valid': True
                })
            else:
                 self.log.warn(f"MTF Measurement {i+1} failed: {res.error_msg}")
            
            time.sleep(0.5) # Small pause between captures
            
        # Calculate Statistics
        if not mtf_results:
            return {'valid': False, 'error': 'All measurements failed'}
            
        mtf50_vals = [r['mtf50'] for r in mtf_results]
        mtf50_mean = float(np.mean(mtf50_vals))
        mtf50_std = float(np.std(mtf50_vals))
        
        stats = {
            'valid': True,
            'mtf50_mean': mtf50_mean,
            'mtf50_std': mtf50_std,
            'n_samples': len(mtf_results),
            'raw_data': mtf_results
        }
        
        # Calculate Uncertainty Budget
        try:
            sys_conf = self.system_config
            cam_conf = sys_conf.get('camera', {})
            axis_conf = sys_conf.get('axis', {})
            defaults = sys_conf.get('defaults', {})
            
            ub = calculate_uncertainty_budget(
                mtf_value=mtf50_mean,
                pixel_size_um=cam_conf.get('pixel_size_um', 2.4),
                pixel_size_uncertainty_um=cam_conf.get('pixel_size_uncertainty_um', 0.05),
                distortion_correction_applied=bool(self.camera_calibration),
                distortion_max_percent=5.0, # Could also come from config
                axis_repeatability_mm=axis_conf.get('repeatability_mm', 0.002),
                algorithm_uncertainty_percent=defaults.get('mtf_algorithm_uncertainty_percent', 1.5),
                statistical_uncertainty=mtf50_std
            )
            stats['uncertainty_budget'] = ub
            self.log.info(f"Uncertainty: {ub['U95']:.3f} lp/mm (k=2, {ub['relative_uncertainty_percent']:.1f}%)")
            
        except Exception as e:
            self.log.error(f"Error calculating uncertainty budget: {e}")
            stats['uncertainty_error'] = str(e)
        
        self.log.info(f"MTF Stats: Mean={stats['mtf50_mean']:.3f} +/- {stats['mtf50_std']:.3f} lp/mm")
        return stats

    def run_correlation_verification(self, start_pos, end_pos, step_size, settle_time=0.5):
        """
        Runs a scan to verify relationship between Autofocus Peak (Tenengrad) and MTF Peak.
        
        Args:
            start_pos: Start Z position (mm)
            end_pos: End Z position (mm)
            step_size: Step size (mm)
            settle_time: Settle time in seconds
            
        Returns:
            dict: {
                'peak_shift': float,
                'max_af_pos': float,
                'max_mtf_pos': float,
                'data': list of dicts {pos, tenengrad, mtf, angle},
                'success': bool
            }
        """
        self.log.info(f"Starting Correlation Scan: {start_pos}-{end_pos}mm (step={step_size}mm)")
        
        # Move to start
        self._move_axis(start_pos)
        self._wait_for_axis_idle()
        
        positions = np.arange(start_pos, end_pos + step_size, step_size)
        results = []
        
        bridge = None # Lazy init if needed or just use cv2 directly? 
        # Orchestrator gives us self.node which has self.latest_image_msg
        # BUT logic.py doesn't have direct access to self.node.latest_image_msg unless we ask for it or updated node
        # VerificationOrchestrator passed 'self' as 'node' to VerificationLogic? Yes: VerificationLogic(self, ...)
        # BUT VerificationOrchestrator has the image subscription.
        # Let's add a helper to get image from node.
        
        from cv_bridge import CvBridge
        cv_bridge = CvBridge()
        
        for pos in positions:
            self.log.info(f"Scanning Z={pos:.2f}...")
            self._move_axis(float(pos))
            self._wait_for_axis_idle()
            time.sleep(settle_time)
            
            # Get Image
            img_msg = self.node.latest_image_msg
            if img_msg is None:
                self.log.warn(f"No image available at {pos}")
                continue
                
            try:
                cv_img = cv_bridge.imgmsg_to_cv2(img_msg, desired_encoding='bgr8')
            except Exception as e:
                self.log.error(f"CV conversion failed: {e}")
                continue
            
            # Calculate Metrics
            tenengrad = ImageMetrics.calculate_tenengrad(cv_img)
            mtf_score, angle = ImageMetrics.calculate_mtf_proxy(cv_img)
            
            results.append({
                'pos': float(pos),
                'tenengrad': tenengrad,
                'mtf': mtf_score,
                'angle': angle
            })
            self.log.info(f"  -> Ten={tenengrad:.1f}, MTF={mtf_score:.2f}")

        if not results:
            self.log.error("Correlation Scan produced no results.")
            return {'success': False, 'message': 'No data collected'}

        # Analyze
        from scipy.signal import find_peaks
        # Simple max search for robustness if curves are noisy but generally correct
        # Ideally we might fit a parabola, but let's stick to argmax for now
        
        best_af = max(results, key=lambda x: x['tenengrad'])
        best_mtf = max(results, key=lambda x: x['mtf'])
        
        peak_shift = best_af['pos'] - best_mtf['pos']
        
        return {
            'success': True,
            'peak_shift': peak_shift,
            'max_af_pos': best_af['pos'],
            'max_mtf_pos': best_mtf['pos'],
            'data': results
        }

    def _move_axis(self, position_mm):
        req = MoveAbsolute.Request()
        req.axis_position = float(position_mm)
        future = self.clients['move'].call_async(req)
        # We need to spin? logic runs in a thread in orchestrator?
        # Orchestrator calls logic methods in a separate thread `verification_thread`.
        # BUT self.clients are created with callback_group=ReentrantCallbackGroup in Orchestrator.
        # We can block on the future result with a short timeout loop?
        # Or simpler: The Orchestrator calls this in a dedicated thread. 
        # rclpy.spin_until_future_complete cannot be called easily if we are not the main thread or executor issues.
        # But wait, self.clients['move'].call(req) is SYNC call!
        # The Orchestrator defined clients using .create_client.
        # Usually .call() is synchronous and blocks.
        # Let's check how other methods do it.
        # helper _run_autofocus_loop uses: self.clients['move'].call(MoveAbsolute.Request(...))
        # So yes, we can use synchronous call.
        
        try:
            res = self.clients['move'].call(req)
            if not res or not res.success:
                raise RuntimeError(f"Move to {position_mm} failed")
        except Exception as e:
            self.log.error(f"Move service call failed: {e}")
            raise


