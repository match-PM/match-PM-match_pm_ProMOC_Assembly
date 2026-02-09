#!/usr/bin/env python3
"""
Scientific Verification Node.

This node hosts the verification services that were previously part of the camera node.
It acts as a client to the camera node (for autofocus) and performs its own analysis.
"""

from datetime import datetime
import json
from pathlib import Path
import time
import csv
from collections import defaultdict

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np

# Interactions
from promoc_assembly_interfaces.srv import (
    VerifyAutofocus,
    VerifyMTF,
    VerifyCorrelation,
    AutoFocus,
    MoveAbsolute,
    GetOperationStatus
)
from camera_nodes.algorithms.focus_metrics import tenengrad as tenengrad_metric


# Algorithms (imported from camera_nodes)
# Ensure camera_nodes is sourceable
try:
    from camera_nodes.algorithms import AUTOFOCUS_ALGORITHMS
    from camera_nodes.algorithms.mtf_analysis import MTFAnalyzer, MTFConfig
    from camera_nodes.algorithms.roi_detection import RoiDetector
    from camera_nodes.plotting import VerificationPlotter
except ImportError:
    # Fallback for dev environment or if paths are tricky
    import logging
    logging.warning("Could not import camera_nodes algorithms directly. Check PYTHONPATH.")
    raise

from promoc_core.promoc_exceptions import (
    ConfigurationError,
    ImageProcessingError,
    ServiceCallFailedError,
)
from promoc_core.error_handling import handle_service_errors


class ScientificVerificationNode(Node):
    """Node for scientific verification of camera algorithms."""

    def __init__(self):
        super().__init__('scientific_verification_node')
        
        self.cb_group = ReentrantCallbackGroup()
        self.bridge = CvBridge()
        self.latest_image_msg = None
        
        # Parameters
        self.declare_parameter('camera_topic', '/promoc/assembly_camera/stream0/image_raw')
        self.declare_parameter('autofocus_service', '/camera_node/autofocus')
        self.declare_parameter('axis_name', 'lts300_x_axis')
        self.declare_parameter('results_dir', str(Path.home() / 'Dokumente' / 'Messungen'))
        
        # Camera Params (mirrored from camera_node for analysis)
        self.declare_parameter('pixel_size_um', 2.40)
        # MTF debug / tuning parameters
        self.declare_parameter('mtf.debug_export_dir', '')
        self.declare_parameter('mtf.debug_export_prefix', 'mtf')
        self.declare_parameter('mtf.debug_export_csv', True)
        self.declare_parameter('mtf.debug_export_png', False)
        self.declare_parameter('mtf.profile', 'default')  # default | scientific | debug
        self.declare_parameter('mtf.lsf_window_mode', 'full')  # full | peak | none
        self.declare_parameter('mtf.lsf_peak_window_size', 0)  # samples; 0 = auto
        self.declare_parameter('mtf.derivative_mode', 'iso')  # diff | iso
        self.declare_parameter('mtf.apply_derivative_correction', True)
        self.declare_parameter('mtf.derivative_correction_max', 0.0)  # 0 disables cap
        self.declare_parameter('mtf.apply_angle_correction', True)
        self.declare_parameter('mtf.esf_smooth_mode', 'none')  # none | sg
        self.declare_parameter('mtf.esf_sg_window', 11)
        self.declare_parameter('mtf.esf_sg_poly', 2)
        self.declare_parameter('mtf.edge_validation_mode', 'warn')  # off | warn | fail
        self.declare_parameter('mtf.edge_validation_percentile', 90.0)
        self.declare_parameter('mtf.edge_validation_min_points', 50)
        self.declare_parameter('mtf.clip_to_nyquist', True)
        self.declare_parameter('mtf.export_dual_curves', False)
        self.declare_parameter('mtf.clip_max', 0.0)  # 0 disables clipping
        self.declare_parameter('mtf.warn_threshold', 1.05)
        
        # Verification Services (Server)
        self.verify_af_srv = self.create_service(
            VerifyAutofocus,
            '~/verify_autofocus',
            self.verify_autofocus_callback,
            callback_group=self.cb_group
        )
        self.verify_mtf_srv = self.create_service(
            VerifyMTF,
            '~/verify_mtf',
            self.verify_mtf_callback,
            callback_group=self.cb_group
        )
        self.verify_corr_srv = self.create_service(
            VerifyCorrelation,
            '~/verify_correlation',
            self.verify_correlation_callback,
            callback_group=self.cb_group
        )
        
        # Camera Subscription
        self.image_sub = self.create_subscription(
            Image,
            self.get_parameter('camera_topic').value,
            self.image_callback,
            10
        )
        
        # Autofocus Client
        self.af_client = self.create_client(
            AutoFocus, 
            self.get_parameter('autofocus_service').value,
            callback_group=self.cb_group
        )

        # Axis Clients (for correlation scan)
        axis_name = self.get_parameter('axis_name').value
        self.move_client = self.create_client(
            MoveAbsolute,
            f'/{axis_name}/move_absolute',
            callback_group=self.cb_group
        )
        self.status_client = self.create_client(
            GetOperationStatus,
            f'/{axis_name}/get_operation_status',
            callback_group=self.cb_group
        )
        
        self.get_logger().info('Scientific Verification Node initialized.')

    def image_callback(self, msg):
        self.latest_image_msg = msg

    def _get_latest_cv_image(self):
        if self.latest_image_msg is None:
            return None
        try:
            return self.bridge.imgmsg_to_cv2(self.latest_image_msg, 'bgr8')
        except Exception as e:
            self.get_logger().warn(f'Image conversion failed: {e}')
            return None

    def _get_output_dir(self, subdirectory: str = '', operator_name: str | None = None) -> Path:
        """Creates and returns the output directory."""
        username = (operator_name or '').strip()
        base_dir = Path(self.get_parameter('results_dir').value)
        
        if username:
            output_dir = base_dir / username / subdirectory
        else:
            output_dir = base_dir / subdirectory
        
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _get_timestamp(self) -> str:
        return datetime.now().strftime('%Y%m%d_%H%M%S')

    # =========================================================================
    # METADATA & IO HELPERS
    # =========================================================================

    def _get_measurement_metadata(self) -> dict:
        """Collects basic metadata."""
        return {
            'timestamp': datetime.now().isoformat(),
            'node': self.get_name(),
            'pixel_size_um': self.get_parameter('pixel_size_um').value,
        }

    def _write_csv_with_metadata(self, filepath: Path, metadata: dict, 
                                   fieldnames: list, rows: list) -> None:
        """Writes CSV file with scientific metadata header."""
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            f.write(f"# VERIFICATION_REPORT\n")
            for key, value in metadata.items():
                f.write(f"# {key}: {value}\n")
            f.write("#\n")
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _save_autofocus_results(self, run_dir, timestamp, results, measurement_points, metadata):
        """Saves all autofocus results to CSV, JSON and Plot."""
        csv_path = run_dir / f'autofocus_verification_{timestamp}.csv'
        fieldnames = ['timestamp', 'algorithm', 'focus_position_mm', 'focus_score',
                      'duration_s', 'measurements', 'deviation_from_ref_mm', 'repetition']
        self._write_csv_with_metadata(csv_path, metadata, fieldnames, results)

        if measurement_points:
            measurements_path = run_dir / f'autofocus_measurements_{timestamp}.json'
            with open(measurements_path, 'w', encoding='utf-8') as f:
                json.dump({'metadata': metadata, 'measurements': measurement_points}, f, indent=2)

            measurements_csv_path = run_dir / f'autofocus_measurements_{timestamp}.csv'
            measurement_fields = ['repetition', 'algorithm', 'index', 'position_mm', 'score']
            self._write_csv_with_metadata(measurements_csv_path, metadata, measurement_fields, measurement_points)

        try:
            plotter = VerificationPlotter(self.get_logger())
            plot_path = run_dir / f'autofocus_verification_{timestamp}.png'
            if plotter.plot_autofocus_verification(results, str(plot_path)):
                self.get_logger().info(f'Autofocus plot saved: {plot_path}')
        except Exception as e:
            self.get_logger().error(f"Plotting failed: {e}")

        return csv_path

    # =========================================================================
    # AUTOFOCUS VERIFICATION
    # =========================================================================

    @handle_service_errors()
    def verify_autofocus_callback(self, request, response):
        """Verification service: compares all autofocus algorithms."""
        start_time = time.time()
        
        if request.start_position >= request.end_position:
            raise ConfigurationError('start_position must be < end_position')
            
        repetitions = max(1, request.repetitions) if request.repetitions > 0 else 1
        
        self.get_logger().info(
            f'Autofocus Verification: range {request.start_position}-{request.end_position}mm, '
            f'repetitions={repetitions}'
        )

        if not self.af_client.wait_for_service(timeout_sec=2.0):
            raise ServiceCallFailedError('Autofocus service not available')

        metadata = self._get_measurement_metadata()
        metadata.update({
            'operator': request.operator_name or 'unknown',
            'notes': request.notes or '',
            'measurement_type': 'autofocus_verification',
            'start_position_mm': request.start_position,
            'end_position_mm': request.end_position,
            'repetitions': repetitions
        })

        output_dir = self._get_output_dir('verification/autofocus_verification', operator_name=request.operator_name)
        timestamp = self._get_timestamp()
        run_dir = output_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)

        results = []
        measurement_points = []
        reference_position = None
        
        algorithms_to_test = list(AUTOFOCUS_ALGORITHMS)
        # Optimization: Run exhaustive search only sparingly to save time.
        # < 10 reps: First and Last only.
        # >= 10 reps: First, Middle, and Last.
        if repetitions < 10:
             exhaustive_runs = {0, max(0, repetitions - 1)}
        else:
             exhaustive_runs = {0, max(0, repetitions // 2), max(0, repetitions - 1)}

        try:
            for rep in range(repetitions):
                self.get_logger().info(f'--- Repetition {rep + 1}/{repetitions} ---')
                current_list = self._get_algo_execution_order(algorithms_to_test, rep in exhaustive_runs)

                for mode, name, _ in current_list:
                    result, measurements = self._run_single_autofocus(
                        self.af_client, request, mode, name, rep + 1, run_dir, timestamp, reference_position
                    )
                    
                    results.append(result)
                    measurement_points.extend(measurements)
                    
                    if reference_position is None and result.get('focus_position_mm') != 'N/A':
                        try:
                            pos = float(result['focus_position_mm'])
                            if pos > 0:
                                reference_position = pos
                        except ValueError:
                            pass
        finally:
            if results:
                self.get_logger().info(f"Saving {len(results)} collected results (partial or complete)...")
                csv_path = self._save_autofocus_results(run_dir, timestamp, results, measurement_points, metadata)
                # If we are in the success path, this is redundant but harmless.
                # If we are in exception path, this ensures data is saved.
                if 'csv_path' not in locals(): # should be assigned by _save_autofocus_results return but just to be safe in logic flow
                     pass
        return self._create_af_response(response, results, reference_position, start_time, csv_path)

    def _get_algo_execution_order(self, all_algos, include_exhaustive):
        if include_exhaustive:
            exhaustive = [a for a in all_algos if a[1] == 'exhaustive']
            others = [a for a in all_algos if a[1] != 'exhaustive']
            return exhaustive + others
        else:
            return [a for a in all_algos if a[1] != 'exhaustive']

    def _run_single_autofocus(self, client, request, mode, name, rep_num, run_dir, timestamp, ref_pos):
        self.get_logger().info(f'Running {name.upper()}...')
        algo_start = time.time()

        af_req = AutoFocus.Request()
        af_req.start_position = float(request.start_position)
        af_req.end_position = float(request.end_position)
        af_req.refinement_mode = int(mode)
        af_req.skip_flyover = True
        af_req.use_sift_weighting = False
        af_req.save_best_image = True
        af_req.output_dir = str(run_dir)
        af_req.output_prefix = f'autofocus_best_{name}_rep{rep_num}_{timestamp}'

        af_resp = client.call(af_req)
        duration = time.time() - algo_start

        result = {
            'timestamp': datetime.now().isoformat(),
            'algorithm': name,
            'duration_s': f'{duration:.2f}',
            'repetition': rep_num,
        }
        measurements = []

        if not af_resp.success:
            self.get_logger().error(f'{name} failed: {af_resp.status_message}')
            result.update({
                'focus_position_mm': 'N/A', 'focus_score': 'N/A', 
                'measurements': 0, 'deviation_from_ref_mm': 'N/A'
            })
        else:
            best_pos = af_resp.best_focus_position
            best_score = af_resp.best_focus_value
            deviation = 0.0
            if ref_pos is not None and best_pos is not None:
                deviation = best_pos - ref_pos

            result.update({
                'focus_position_mm': f'{best_pos:.4f}',
                'focus_score': f'{best_score:.0f}',
                'measurements': af_resp.total_measurements_taken,
                'deviation_from_ref_mm': f'{deviation:.4f}',
            })
            
            try:
                positions = list(getattr(af_resp, 'measurement_positions', []) or [])
                scores = list(getattr(af_resp, 'measurement_scores', []) or [])
                for idx, (p, s) in enumerate(zip(positions, scores)):
                    measurements.append({
                        'repetition': rep_num, 'algorithm': name, 'index': idx,
                        'position_mm': float(p), 'score': float(s)
                    })
            except Exception:
                pass

        return result, measurements

    def _create_af_response(self, response, results, ref_pos, start_time, csv_path):
        max_deviation = 0.0
        total_measurements = 0
        for r in results:
            try:
                dev = abs(float(r['deviation_from_ref_mm']))
                if dev > max_deviation: max_deviation = dev
                total_measurements += int(r['measurements'])
            except (ValueError, TypeError): pass
        
        response.success = True
        response.status_message = f'Verification complete. CSV: {csv_path}'
        response.csv_path = str(csv_path)
        response.reference_position_mm = float(ref_pos or 0)
        response.max_deviation_mm = max_deviation
        response.total_duration_seconds = time.time() - start_time
        response.total_measurements = total_measurements
        return response

    # =========================================================================
    # MTF VERIFICATION
    # =========================================================================

    @handle_service_errors()
    def verify_mtf_callback(self, request, response):
        """Verification service: MTF field test with comprehensive output."""
        start_time = time.time()
        repetitions = max(1, request.repetitions) if hasattr(request, 'repetitions') and request.repetitions > 0 else 1
        
        self.get_logger().info(f'MTF Verification: field_test={request.field_test}, reps={repetitions}')

        cv_image = self._get_latest_cv_image()
        if cv_image is None:
            raise ImageProcessingError('No image available')

        metadata = self._get_measurement_metadata()
        metadata.update({
            'operator': request.operator_name or 'unknown',
            'config_name': request.config_name or 'default',
            'notes': request.notes or '',
            'measurement_type': 'mtf_verification',
            'field_test': request.field_test,
            'repetitions': repetitions
        })

        output_dir = self._get_output_dir('verification/mtf_Verification', operator_name=request.operator_name)
        timestamp = self._get_timestamp()
        run_dir = output_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)

        # Force debug export for this verification run into the run directory
        analyzer = self._create_mtf_analyzer(debug_dir=str(run_dir), force_debug=True)
        vis_img, bars, squares = RoiDetector.detect_targets(cv_image)
        
        if not squares and not bars:
            raise ImageProcessingError('No MTF targets detected')

        positions = self._define_measurement_positions(cv_image, request.field_test)
        self._annotate_targets(vis_img, positions)
        cv2.imwrite(str(run_dir / f'mtf_targets_{timestamp}.jpg'), vis_img)

        results = []
        mtf_curves = []
        edges_failed = 0
        edges_tile_path = None

        try:
            for rep in range(repetitions):
                for pos_name, target_x, target_y in positions:
                    chosen_square = self._find_nearest_square(squares, target_x, target_y, cv_image.shape)
                    if not chosen_square:
                        self._record_missing_target(results, metadata, rep+1, pos_name, target_x, target_y)
                        edges_failed += 4
                        continue

                    fixed_roi_dims = (300, 50)
                    edges_with_boxes = RoiDetector.split_square_into_edges_with_boxes(
                        cv_image, chosen_square, fixed_size=fixed_roi_dims
                    )

                    if edges_tile_path is None:
                        edges = [roi for roi, _, _ in edges_with_boxes]
                        if edges:
                            try:
                                vis_edges, _ = RoiDetector.create_debug_visualization(edges)
                                edges_tile_path = run_dir / f'mtf_edges_overview_{timestamp}.jpg'
                                cv2.imwrite(str(edges_tile_path), vis_edges)
                            except Exception: pass

                    for roi_img, (x, y, w_box, h_box), edge_name in edges_with_boxes:
                        self._draw_edge_debug(vis_img, run_dir, cv_image, x, y, w_box, h_box, 
                                            pos_name, edge_name, timestamp)
                        
                        contrast = RoiDetector.calculate_michelson_contrast(roi_img)
                        debug_label = f"{pos_name}_{edge_name}"
                        mtf_res = analyzer.compute_mtf(roi_img, debug_label=debug_label)
                        
                        row = {
                            'timestamp': datetime.now().isoformat(),
                            'config': request.config_name or 'default',
                            'position': pos_name, 'edge': edge_name,
                            'roi_x': int(x), 'roi_y': int(y), 'roi_w': int(w_box), 'roi_h': int(h_box),
                            'contrast': f'{contrast:.3f}',
                        }

                        if mtf_res.valid:
                            if mtf_res.warning_msg:
                                self.get_logger().warn(
                                    f"MTF warning ({pos_name}/{edge_name}): {mtf_res.warning_msg}"
                                )
                            row.update({
                                'mtf50_lpmm': f'{mtf_res.mtf50:.2f}',
                                'mtf20_lpmm': f'{mtf_res.mtf20:.2f}',
                                'mtf10_lpmm': f'{mtf_res.mtf10:.2f}',
                                'edge_angle_deg': f'{mtf_res.edge_angle:.2f}',
                                'nyquist_lpmm': f'{mtf_res.nyquist_frequency:.2f}',
                                'valid': 'true', 'error': ''
                            })
                            if mtf_res.frequencies.size > 0 and len(mtf_curves) < 8:
                                mtf_curves.append({
                                    'label': f'{pos_name}-{edge_name}',
                                    'frequencies': mtf_res.frequencies,
                                    'mtf_values': mtf_res.mtf_values,
                                    'mtf_ideal': mtf_res.mtf_ideal,
                                    'nyquist_lpmm': mtf_res.nyquist_frequency,
                                })
                        else:
                            edges_failed += 1
                            row.update({
                                'mtf50_lpmm': '0', 'mtf20_lpmm': '0', 'mtf10_lpmm': '0', 
                                'edge_angle_deg': '0', 'nyquist_lpmm': '0',
                                'valid': 'false', 'error': mtf_res.error_msg
                            })
                        results.append(row)
        finally:
            if results:
                self.get_logger().info(f"Saving {len(results)} MTF results (partial or complete)...")
                csv_path = run_dir / f'mtf_verification_{timestamp}.csv'
                fieldnames = ['timestamp', 'config', 'position', 'edge', 
                            'roi_x', 'roi_y', 'roi_w', 'roi_h', 'square_cx', 'square_cy',
                            'mtf50_lpmm', 'mtf20_lpmm', 'mtf10_lpmm', 'edge_angle_deg',
                            'contrast', 'nyquist_lpmm', 'valid', 'error']
                self._write_csv_with_metadata(csv_path, metadata, fieldnames, results)

        stats_csv_path = self._save_mtf_statistics(run_dir, timestamp, results)
        dir_stats_path = self._save_mtf_directional_stats(run_dir, timestamp, results)
        self._save_mtf_curves(run_dir, timestamp, mtf_curves)

        try:
            plotter = VerificationPlotter(self.get_logger())
            plot_path = run_dir / f'mtf_results_{timestamp}.png'
            plotter.plot_mtf_verification(results, str(plot_path), curves=mtf_curves)
        except Exception as e:
            self.get_logger().error(f"Plotting failed: {e}")

        response.success = True
        response.status_message = f'MTF Done. CSV: {csv_path.name}'
        response.csv_path = str(csv_path)
        valid_mtf50 = [float(r['mtf50_lpmm']) for r in results if r['valid'] == 'true']
        response.mtf50_mean = float(np.mean(valid_mtf50)) if valid_mtf50 else 0.0
        response.mtf50_std = float(np.std(valid_mtf50)) if len(valid_mtf50) > 1 else 0.0
        response.edges_measured = len(valid_mtf50)
        response.edges_failed = edges_failed

        # Log directional stats if available
        if dir_stats_path:
            self.get_logger().info(f"Directional MTF stats saved: {dir_stats_path.name}")

        return response

    # =========================================================================
    # CORRELATION VERIFICATION
    # =========================================================================

    @handle_service_errors()
    def verify_correlation_callback(self, request, response):
        """Scans a range and returns correlation between AF and MTF peaks."""
        start_time = time.time()
        
        if request.start_position >= request.end_position:
            raise ConfigurationError('start_position must be < end_position')
            
        step_size = request.step_size if request.step_size > 0 else 0.5
        positions = np.arange(request.start_position, request.end_position + step_size, step_size)
        
        self.get_logger().info(
            f'Correlation Verification: {request.start_position}-{request.end_position}mm '
            f'(step={step_size}mm, {len(positions)} points)'
        )

        # Check Services
        if not self.move_client.wait_for_service(timeout_sec=2.0) or \
           not self.status_client.wait_for_service(timeout_sec=2.0):
             raise ServiceCallFailedError('Axis services not available')

        # Prepare IO
        output_dir = self._get_output_dir('verification/correlation')
        timestamp = self._get_timestamp()
        run_dir = output_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        
        analyzer = self._create_mtf_analyzer()
        metadata = self._get_measurement_metadata()
        metadata.update({
             'type': 'correlation_scan',
             'start': request.start_position,
             'end': request.end_position,
             'step': step_size
        })
        
        results = []
        
        try:
            # Scan Loop
            for pos in positions:
                self._move_axis_and_wait(pos)
                time.sleep(request.settle_time if request.settle_time > 0 else 0.5)
                
                cv_image = self._get_latest_cv_image()
                if cv_image is None:
                    self.get_logger().warn(f"No image at Z={pos:.2f}")
                    continue
                
                # 1. Tenengrad
                tenengrad = tenengrad_metric(cv_image)
                
                # 2. MTF (Center ROI)
                # Use center crop for robustness
                h, w = cv_image.shape[:2]
                cx, cy = w // 2, h // 2
                cw, ch = 300, 300 # Fixed window around center
                roi_rect = (max(0, cx-cw//2), max(0, cy-ch//2), min(w, cx+cw//2), min(h, cy+ch//2))
                
                mtf_res = analyzer.compute_mtf(cv_image, roi=roi_rect, debug_label="correlation_center")
                
                mtf_val = mtf_res.mtf50 if mtf_res.valid else 0.0
                if mtf_res.valid and mtf_res.warning_msg:
                    self.get_logger().warn(f"MTF warning (correlation): {mtf_res.warning_msg}")
                
                self.get_logger().info(f"Z={pos:.2f}: Ten={tenengrad:.1f}, MTF50={mtf_val:.3f}")
                
                results.append({
                    'position_mm': float(pos),
                    'tenengrad': float(tenengrad),
                    'mtf50_lpmm': float(mtf_val),
                    'valid': mtf_res.valid
                })
        finally:
            if results:
                # Save Data (partial or complete)
                csv_path = run_dir / f'correlation_{timestamp}.csv'
                self._write_csv_with_metadata(
                    csv_path, metadata, 
                    ['position_mm', 'tenengrad', 'mtf50_lpmm', 'valid'], 
                    results
                )
        
        if not results:
             raise ImageProcessingError("No valid data collected during scan")
        
        # Analyze Peaks
        # Simple argmax for now (could be fitted)
        best_af = max(results, key=lambda x: x['tenengrad'])
        best_mtf = max(results, key=lambda x: x['mtf50_lpmm'])
        
        peak_shift = best_af['position_mm'] - best_mtf['position_mm']
        
        # Plot
        try:
            plotter = VerificationPlotter(self.get_logger())
            plot_path = run_dir / f'correlation_plot_{timestamp}.png'
            plotter.plot_correlation_verification({'data': results, 'peak_shift': peak_shift, 
                                                   'max_af_pos': best_af['position_mm'], 
                                                   'max_mtf_pos': best_mtf['position_mm']}, 
                                                   str(plot_path))
        except Exception:
             pass

        response.success = True
        response.status_message = f"Correlation done. Shift: {peak_shift:.4f}mm"
        response.peak_shift = peak_shift
        response.max_af_pos = best_af['position_mm']
        response.max_mtf_pos = best_mtf['position_mm']
        
        return response

    def _move_axis_and_wait(self, pos_mm):
        req = MoveAbsolute.Request()
        req.axis_position = float(pos_mm)
        future = self.move_client.call_async(req)
        
        start = time.time()
        while not future.done():
            if time.time() - start > 10.0:
                 raise ServiceCallFailedError("Move service timeout")
            time.sleep(0.05)
            
        res = future.result()
        if not res or not res.success:
             raise ServiceCallFailedError(f"Move to {pos_mm} failed")
             
        # Wait for Idle
        start_idle = time.time()
        while time.time() - start_idle > 30.0:
             stat_future = self.status_client.call_async(GetOperationStatus.Request())
             while not stat_future.done():
                 time.sleep(0.01)
             stat = stat_future.result()
             if stat and stat.operation_status == 'idle':
                 return
             time.sleep(0.05)
             
        raise ServiceCallFailedError("Timeout waiting for axis idle")

    # -------------------------------------------------------------------------
    # MTF HELPERS
    # -------------------------------------------------------------------------

    def _create_mtf_analyzer(self, debug_dir: str | None = None, force_debug: bool = False) -> MTFAnalyzer:
        pixel_size = self.get_parameter('pixel_size_um').value
        config = MTFConfig(pixel_size_um=pixel_size, min_edge_angle=2.0)
        # Optional config overrides
        if debug_dir is None:
            debug_dir = str(self.get_parameter('mtf.debug_export_dir').value or "")
            if debug_dir:
                config.debug_export_dir = debug_dir
                config.debug_export_prefix = str(
                    self.get_parameter('mtf.debug_export_prefix').value or config.debug_export_prefix
                )
                config.debug_export_csv = bool(self.get_parameter('mtf.debug_export_csv').value)
                config.debug_export_png = bool(self.get_parameter('mtf.debug_export_png').value)
        else:
            config.debug_export_dir = str(debug_dir)
            config.debug_export_prefix = str(
                self.get_parameter('mtf.debug_export_prefix').value or config.debug_export_prefix
            )
            if force_debug:
                config.debug_export_csv = True
                config.debug_export_png = True
            else:
                config.debug_export_csv = bool(self.get_parameter('mtf.debug_export_csv').value)
                config.debug_export_png = bool(self.get_parameter('mtf.debug_export_png').value)
        config.lsf_window_mode = str(self.get_parameter('mtf.lsf_window_mode').value or config.lsf_window_mode)
        try:
            config.lsf_peak_window_size = int(self.get_parameter('mtf.lsf_peak_window_size').value or 0)
        except Exception:
            pass
        try:
            config.derivative_mode = str(
                self.get_parameter('mtf.derivative_mode').value or config.derivative_mode
            )
        except Exception:
            pass
        try:
            config.apply_derivative_correction = bool(
                self.get_parameter('mtf.apply_derivative_correction').value
            )
        except Exception:
            pass
        try:
            config.derivative_correction_max = float(
                self.get_parameter('mtf.derivative_correction_max').value or 0.0
            )
        except Exception:
            pass
        try:
            config.apply_angle_correction = bool(
                self.get_parameter('mtf.apply_angle_correction').value
            )
        except Exception:
            pass
        try:
            config.esf_smooth_mode = str(
                self.get_parameter('mtf.esf_smooth_mode').value or config.esf_smooth_mode
            )
        except Exception:
            pass
        try:
            config.esf_sg_window = int(
                self.get_parameter('mtf.esf_sg_window').value or config.esf_sg_window
            )
        except Exception:
            pass
        try:
            config.esf_sg_poly = int(
                self.get_parameter('mtf.esf_sg_poly').value or config.esf_sg_poly
            )
        except Exception:
            pass
        try:
            config.edge_validation_mode = str(
                self.get_parameter('mtf.edge_validation_mode').value or config.edge_validation_mode
            )
        except Exception:
            pass
        try:
            config.edge_validation_percentile = float(
                self.get_parameter('mtf.edge_validation_percentile').value or config.edge_validation_percentile
            )
        except Exception:
            pass
        try:
            config.edge_validation_min_points = int(
                self.get_parameter('mtf.edge_validation_min_points').value or config.edge_validation_min_points
            )
        except Exception:
            pass
        try:
            config.clip_to_nyquist = bool(
                self.get_parameter('mtf.clip_to_nyquist').value
            )
        except Exception:
            pass
        try:
            config.export_dual_curves = bool(
                self.get_parameter('mtf.export_dual_curves').value
            )
        except Exception:
            pass
        try:
            config.mtf_clip_max = float(self.get_parameter('mtf.clip_max').value or 0.0)
        except Exception:
            pass
        try:
            config.mtf_warn_threshold = float(
                self.get_parameter('mtf.warn_threshold').value or config.mtf_warn_threshold
            )
        except Exception:
            pass

        # Apply profile last (overrides for ease-of-use)
        try:
            profile = str(self.get_parameter('mtf.profile').value or "default").strip().lower()
        except Exception:
            profile = "default"
        if profile in ("scientific", "debug"):
            config.derivative_mode = "iso"
            config.apply_derivative_correction = True
            config.apply_angle_correction = True
            config.clip_to_nyquist = True
            config.lsf_window_mode = "peak"
            config.lsf_peak_window_size = 0
            config.edge_validation_mode = "warn"
        if profile == "debug":
            if not config.debug_export_dir:
                config.debug_export_dir = str(Path(self.get_parameter('results_dir').value) / "mtf_debug")
            config.debug_export_csv = True
            config.debug_export_png = True
            if config.esf_smooth_mode == "none":
                config.esf_smooth_mode = "sg"
            config.export_dual_curves = True
        if profile not in ("default", "scientific", "debug", ""):
            self.get_logger().warn(f"Unknown mtf.profile='{profile}', using current configuration.")
        return MTFAnalyzer(config)

    def _define_measurement_positions(self, image, field_test: bool):
        h, w = image.shape[:2]
        positions = [('center', w // 2, h // 2)]
        if field_test:
            margin = min(w, h) // 4
            positions.extend([
                ('top_left', margin, margin),
                ('top_right', w - margin, margin),
                ('bottom_left', margin, h - margin),
                ('bottom_right', w - margin, h - margin),
            ])
        return positions

    def _annotate_targets(self, img, positions):
        for name, x, y in positions:
            cv2.circle(img, (int(x), int(y)), 8, (0, 255, 255), 2)
            cv2.putText(img, name, (int(x) + 10, int(y) - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    def _find_nearest_square(self, squares, target_x, target_y, img_shape):
        if not squares: return None
        closest_dist = None
        chosen_square = None
        for rect in squares:
            (cx, cy), _, _ = rect
            dist = ((cx - target_x) ** 2 + (cy - target_y) ** 2) ** 0.5
            if closest_dist is None or dist < closest_dist:
                closest_dist = dist
                chosen_square = rect
        h, w = img_shape[:2]
        max_dist = min(w, h) * 0.35
        if closest_dist is None or closest_dist > max_dist:
            self.get_logger().warn(f'Target too far from {target_x},{target_y} (dist={closest_dist:.1f})')
            return None
        return chosen_square

    def _record_missing_target(self, results, metadata, rep, pos_name, tx, ty):
        results.append({
            'timestamp': datetime.now().isoformat(),
            'config': metadata.get('config_name', 'default'),
            'repetition': rep, 'position': pos_name,
            'edge': 'n/a', 'roi_x': tx, 'roi_y': ty, 'roi_w': 0, 'roi_h': 0,
            'mtf50_lpmm': '0', 'valid': 'false', 'error': 'no_nearby_target'
        })

    def _draw_edge_debug(self, vis_img, run_dir, cv_image, x, y, w, h, pos_name, edge_name, ts):
        cv2.rectangle(vis_img, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.putText(vis_img, f'{edge_name}', (x, max(0, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        pad = 50
        full_h, full_w = cv_image.shape[:2]
        cx, cy = x + w // 2, y + h // 2
        ctx_x = max(0, cx - (w + 2*pad) // 2)
        ctx_y = max(0, cy - (h + 2*pad) // 2)
        ctx_w = min(w + 2*pad, full_w - ctx_x)
        ctx_h = min(h + 2*pad, full_h - ctx_y)
        if ctx_w > 0 and ctx_h > 0:
            context_img = cv_image[ctx_y:ctx_y+ctx_h, ctx_x:ctx_x+ctx_w].copy()
            if len(context_img.shape) == 2:
                context_img = cv2.cvtColor(context_img, cv2.COLOR_GRAY2BGR)
            rel_x, rel_y = x - ctx_x, y - ctx_y
            cv2.rectangle(context_img, (rel_x, rel_y), (rel_x + w, rel_y + h), (0, 255, 0), 1)
            p = run_dir / f'roi_{pos_name}_{edge_name}_{ts}.jpg'
            cv2.imwrite(str(p), context_img)

    def _save_mtf_statistics(self, run_dir, timestamp, results):
        grouped = defaultdict(lambda: {'mtf50': [], 'mtf20': [], 'angle': [], 'contrast': []})
        for r in results:
            if r.get('valid') == 'true':
                key = (r['position'], r['edge'])
                grouped[key]['mtf50'].append(float(r['mtf50_lpmm']))
                grouped[key]['mtf20'].append(float(r['mtf20_lpmm']))
                grouped[key]['angle'].append(float(r['edge_angle_deg']))
                grouped[key]['contrast'].append(float(r['contrast']))
        stats_rows = []
        for (pos, edge), data in grouped.items():
            if data['mtf50']:
                stats_rows.append({
                    'position': pos, 'edge': edge, 'count': len(data['mtf50']),
                    'mtf50_mean': f"{np.mean(data['mtf50']):.2f}",
                    'mtf50_std': f"{np.std(data['mtf50']):.2f}",
                    'angle_mean': f"{np.mean(data['angle']):.2f}",
                    'contrast_mean': f"{np.mean(data['contrast']):.3f}",
                })
        if stats_rows:
            path = run_dir / f'mtf_verification_summary_{timestamp}.csv'
            fields = ['position', 'edge', 'count', 'mtf50_mean', 'mtf50_std', 'angle_mean', 'contrast_mean']
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(stats_rows)
            return path
        return None

    def _save_mtf_directional_stats(self, run_dir, timestamp, results):
        """
        Save aggregated MTF stats by direction:
        - vertical: top/bottom edges
        - horizontal: left/right edges
        """
        groups = {
            'vertical': [],
            'horizontal': []
        }
        for r in results:
            if r.get('valid') != 'true':
                continue
            edge = (r.get('edge') or '').lower()
            if edge in ('top', 'bottom'):
                groups['vertical'].append(r)
            elif edge in ('left', 'right'):
                groups['horizontal'].append(r)

        rows = []
        for direction, vals in groups.items():
            if not vals:
                continue
            mtf50_vals = [float(v.get('mtf50_lpmm', 0)) for v in vals]
            mtf20_vals = [float(v.get('mtf20_lpmm', 0)) for v in vals]
            mtf10_vals = [float(v.get('mtf10_lpmm', 0)) for v in vals]
            rows.append({
                'direction': direction,
                'count': len(mtf50_vals),
                'mtf50_mean': f"{np.mean(mtf50_vals):.2f}",
                'mtf50_std': f"{np.std(mtf50_vals):.2f}",
                'mtf20_mean': f"{np.mean(mtf20_vals):.2f}",
                'mtf20_std': f"{np.std(mtf20_vals):.2f}",
                'mtf10_mean': f"{np.mean(mtf10_vals):.2f}",
                'mtf10_std': f"{np.std(mtf10_vals):.2f}",
            })

        if rows:
            path = run_dir / f'mtf_verification_directional_{timestamp}.csv'
            fields = [
                'direction', 'count',
                'mtf50_mean', 'mtf50_std',
                'mtf20_mean', 'mtf20_std',
                'mtf10_mean', 'mtf10_std'
            ]
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            return path
        return None

    def _save_mtf_curves(self, run_dir, timestamp, curves):
        rows = []
        for curve in curves:
             parts = curve['label'].split('-')
             pos, edge = parts[0], parts[1] if len(parts)>1 else 'unknown'
             nyq = curve['nyquist_lpmm']
             ideals = curve.get('mtf_ideal', [0.0]*len(curve['frequencies']))
             for f, v, ideal in zip(curve['frequencies'], curve['mtf_values'], ideals):
                 if 0 <= f <= nyq * 1.5:
                     rows.append({
                         'timestamp': datetime.now().isoformat(),
                         'position': pos, 'edge': edge,
                         'frequency_lpmm': f'{f:.4f}', 'mtf_value': f'{v:.6f}',
                         'mtf_ideal_value': f'{ideal:.6f}', 'nyquist_limit': f'{nyq:.2f}'
                     })
        if rows:
            path = run_dir / f'mtf_full_curves_{timestamp}.csv'
            fields = ['timestamp', 'position', 'edge', 'frequency_lpmm', 
                      'mtf_value', 'mtf_ideal_value', 'nyquist_limit']
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)

def main(args=None):
    rclpy.init(args=args)
    node = ScientificVerificationNode()
    
    # Use MultiThreadedExecutor to allow callbacks to make synchronous service calls
    # without deadlocking (since callbacks run in the executor's thread pool)
    from rclpy.executors import MultiThreadedExecutor
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
