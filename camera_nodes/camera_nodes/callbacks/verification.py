"""Verification callbacks for scientific validation of autofocus and MTF measurements."""

from datetime import datetime
from pathlib import Path
import time
import csv
import numpy as np
import cv2

from promoc_assembly_interfaces.srv import (
    MoveAbsolute,
    GetOperationStatus,
)
from promoc_core.promoc_exceptions import (
    ConfigurationError,
    ImageProcessingError,
    ServiceCallFailedError,
)
from .base import CallbackBase
from ..algorithms import (
    AutofocusConfig,
    AUTOFOCUS_ALGORITHMS,  # Use centralized definition
)
from ..algorithms.mtf_analysis import MTFAnalyzer, MTFConfig
from ..algorithms.roi_detection import RoiDetector
from ..plotting import VerificationPlotter
from promoc_core.error_handling import handle_service_errors


class VerificationCallbacks(CallbackBase):
    """Callbacks for scientific verification of autofocus and MTF."""

    def _get_measurement_metadata(self) -> dict:
        """Collects all measurement metadata from node parameters."""
        return {
            'timestamp': datetime.now().isoformat(),
            'camera_model': 'IDS UI-3590CP-M-GL Rev.2.2',  # TODO: Get from driver
            'camera_serial': self._node.get_parameter('measurement.username').value or 'unknown',
            'objective': self._node.get_parameter('measurement_conditions.camera_objective').value,
            'pixel_size_um': self._node.get_parameter('pixel_size_um').value,
            'coaxial_light_voltage': self._node.get_parameter('measurement_conditions.coaxial_light_voltage').value,
            'coaxial_light_current': self._node.get_parameter('measurement_conditions.coaxial_light_current').value,
            'notes': self._node.get_parameter('measurement_conditions.notes').value,
        }

    def _write_csv_with_metadata(self, filepath: Path, metadata: dict, 
                                   fieldnames: list, rows: list) -> None:
        """Writes CSV file with scientific metadata header."""
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            # Write metadata as comments
            f.write(f"# VERIFICATION_REPORT\n")
            for key, value in metadata.items():
                f.write(f"# {key}: {value}\n")
            f.write("#\n")
            
            # Write CSV data
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    @handle_service_errors()
    def verify_autofocus_callback(self, request, response):
        """Verification service: compares all autofocus algorithms."""
        start_time = time.time()
        
        self._node.get_logger().info(
            f'Autofocus Verification: range {request.start_position}-{request.end_position}mm, '
            f'repetitions={request.repetitions}, include_exhaustive={request.include_exhaustive}'
        )

        # Validate input
        if request.start_position >= request.end_position:
            raise ConfigurationError('start_position must be < end_position')
        
        repetitions = max(1, request.repetitions) if request.repetitions > 0 else 1
        include_exhaustive = request.include_exhaustive
        
        # Get axis clients
        clients = self._get_all_axis_clients()
        
        # Collect metadata
        metadata = self._get_measurement_metadata()
        metadata['operator'] = request.operator_name or 'unknown'
        metadata['notes'] = request.notes or metadata.get('notes', '')
        metadata['measurement_type'] = 'autofocus_verification'
        metadata['start_position_mm'] = request.start_position
        metadata['end_position_mm'] = request.end_position
        metadata['repetitions'] = repetitions

        output_dir = self._get_output_dir('verification')
        timestamp = self._get_timestamp()
        
        # Results storage
        results = []
        reference_position = None
        
        # Select algorithms to test
        algorithms_to_test = AUTOFOCUS_ALGORITHMS.copy()
        if not include_exhaustive:
            algorithms_to_test = [a for a in algorithms_to_test if a[1] != 'exhaustive']
        
        # Run each algorithm
        for rep in range(repetitions):
            self._node.get_logger().info(f'--- Repetition {rep + 1}/{repetitions} ---')
            
            for mode, name, algo_class in algorithms_to_test:
                self._node.get_logger().info(f'Running {name.upper()}...')
                
                config = AutofocusConfig(
                    start_mm=float(request.start_position),
                    end_mm=float(request.end_position),
                    step_mm=0.5,  # Coarse step
                )
                
                af = algo_class(config)
                algo_start = time.time()
                
                # Run autofocus loop
                best_pos, best_score, measurements, best_image = self._run_autofocus_loop(
                    af, clients, return_best_image=True
                )
                
                duration = time.time() - algo_start
                
                # Store reference position from exhaustive
                if name == 'exhaustive' and rep == 0 and best_pos is not None:
                    reference_position = best_pos
                
                # Calculate deviation from reference
                deviation = 0.0
                if reference_position is not None and best_pos is not None:
                    deviation = best_pos - reference_position
                
                pos_str = f'{best_pos:.4f}' if best_pos is not None else 'N/A'
                score_str = f'{best_score:.0f}' if best_score is not None else 'N/A'

                results.append({
                    'timestamp': datetime.now().isoformat(),
                    'algorithm': name,
                    'focus_position_mm': pos_str,
                    'focus_score': score_str,
                    'duration_s': f'{duration:.2f}',
                    'measurements': measurements,
                    'deviation_from_ref_mm': f'{deviation:.4f}',
                    'repetition': rep + 1,
                })

                if best_image is not None:
                    img_path = output_dir / f'autofocus_best_{name}_rep{rep + 1}_{timestamp}.jpg'
                    cv2.imwrite(str(img_path), best_image)
                    self._node.get_logger().info(f'Saved best image: {img_path}')
                
                self._node.get_logger().info(
                    f'{name}: pos={pos_str}mm, score={score_str}, '
                    f'time={duration:.1f}s, dev={deviation:.4f}mm'
                )
        
        # Write CSV
        csv_path = output_dir / f'autofocus_verification_{timestamp}.csv'
        
        fieldnames = ['timestamp', 'algorithm', 'focus_position_mm', 'focus_score',
                        'duration_s', 'measurements', 'deviation_from_ref_mm', 'repetition']
        
        self._write_csv_with_metadata(csv_path, metadata, fieldnames, results)

        plotter = VerificationPlotter(self._node.get_logger())
        plot_path = output_dir / f'autofocus_verification_{timestamp}.png'
        if plotter.plot_autofocus_verification(results, str(plot_path)):
            self._node.get_logger().info(f'Autofocus plot saved: {plot_path}')
        
        # Calculate summary statistics
        max_deviation = 0.0
        total_measurements = 0
        for r in results:
            try:
                dev = abs(float(r['deviation_from_ref_mm']))
                if dev > max_deviation:
                    max_deviation = dev
                total_measurements += int(r['measurements'])
            except (ValueError, TypeError):
                pass
        
        total_duration = time.time() - start_time
        
        response.success = True
        response.status_message = f'Verification complete. CSV: {csv_path}'
        response.csv_path = str(csv_path)
        response.reference_position_mm = float(reference_position or 0)
        response.max_deviation_mm = max_deviation
        response.total_duration_seconds = total_duration
        response.total_measurements = total_measurements
            
        return response

    @handle_service_errors()
    def verify_mtf_callback(self, request, response):
        """Verification service: MTF field test with comprehensive output."""
        start_time = time.time()
        
        repetitions = max(1, request.repetitions) if hasattr(request, 'repetitions') and request.repetitions > 0 else 1
        
        self._node.get_logger().info(
            f'MTF Verification: field_test={request.field_test}, config={request.config_name}, '
            f'repetitions={repetitions}'
        )

        cv_image = self._get_latest_cv_image()
        if cv_image is None:
            raise ImageProcessingError('No image available')
        
        # Collect metadata
        metadata = self._get_measurement_metadata()
        metadata['operator'] = request.operator_name or 'unknown'
        metadata['config_name'] = request.config_name or 'default'
        metadata['notes'] = request.notes or metadata.get('notes', '')
        metadata['measurement_type'] = 'mtf_verification'
        metadata['field_test'] = request.field_test
        metadata['repetitions'] = repetitions
        
        pixel_size_um = self._node.get_parameter('pixel_size_um').value or 2.40  # IDS U3-3800CP
        config = MTFConfig(pixel_size_um=pixel_size_um)
        analyzer = MTFAnalyzer(config)
        
        results = []
        # Track per-edge measurements for statistics
        from collections import defaultdict
        edge_measurements = defaultdict(lambda: {'mtf50': [], 'mtf20': [], 'mtf10': [], 'contrast': []})
        edges_failed = 0
        mtf_curves = []
        
        # Detect targets + save debug images
        vis_img, bars, squares = RoiDetector.detect_targets(cv_image)

        output_dir = self._get_output_dir('verification')
        timestamp = self._get_timestamp()

        edges_tile_path = None
        
        if not squares and not bars:
            raise ImageProcessingError('No MTF targets detected')
        
        # Define measurement positions
        h, w = cv_image.shape[:2]
        positions = [('center', w // 2, h // 2)]
        
        if request.field_test:
            margin = min(w, h) // 4
            positions.extend([
                ('top_left', margin, margin),
                ('top_right', w - margin, margin),
                ('bottom_left', margin, h - margin),
                ('bottom_right', w - margin, h - margin),
            ])

        # Annotate measurement positions on debug image
        for pos_name, target_x, target_y in positions:
            cv2.circle(vis_img, (int(target_x), int(target_y)), 8, (0, 255, 255), 2)
            cv2.putText(
                vis_img,
                pos_name,
                (int(target_x) + 10, int(target_y) - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2,
            )

        targets_path = output_dir / f'mtf_targets_{timestamp}.jpg'
        cv2.imwrite(str(targets_path), vis_img)
        
        # REPEATABILITY LOOP: Measure multiple times if requested
        for rep in range(repetitions):
            if repetitions > 1:
                self._node.get_logger().info(f'--- Repetition {rep + 1}/{repetitions} ---')
        
            # For each position, find nearest target and measure
            for pos_name, target_x, target_y in positions:
                self._node.get_logger().info(f'Measuring at {pos_name} ({target_x}, {target_y})')

                # Find nearest square for this position
                chosen_square = None
                if squares:
                    closest_dist = None
                    for rect in squares:
                        (cx, cy), _, _ = rect
                        dist = ((cx - target_x) ** 2 + (cy - target_y) ** 2) ** 0.5
                        if closest_dist is None or dist < closest_dist:
                            closest_dist = dist
                            chosen_square = rect

                    # Skip if square is too far from requested position
                    max_dist = min(w, h) * 0.35
                    if closest_dist is None or closest_dist > max_dist:
                        self._node.get_logger().warn(
                            f'No nearby target for {pos_name} (dist={closest_dist})'
                        )
                        cv2.putText(
                            vis_img,
                            f'no_target:{pos_name}',
                            (int(target_x) + 10, int(target_y) + 15),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (0, 0, 255),
                            1,
                        )
                        results.append({
                            'timestamp': datetime.now().isoformat(),
                            'config': request.config_name or 'default',
                            'repetition': rep + 1,
                            'position': pos_name,
                            'edge': 'n/a',
                            'roi_x': target_x,
                            'roi_y': target_y,
                            'mtf50_lpmm': '0',
                            'mtf20_lpmm': '0',
                            'mtf10_lpmm': '0',
                            'edge_angle_deg': '0',
                            'contrast': '0',
                            'nyquist_lpmm': '0',
                            'valid': 'false',
                            'error': 'no_nearby_target',
                        })
                        edges_failed += 4
                        continue
            
            # Find squares or use detected ROIs
            if chosen_square is not None:
                # Draw chosen square and edge boxes on debug image
                (roi_cx, roi_cy), _, _ = chosen_square
                box = np.int32(cv2.boxPoints(chosen_square))
                cv2.drawContours(vis_img, [box], 0, (0, 128, 255), 2)
                cv2.putText(
                    vis_img,
                    f'roi:{pos_name}',
                    (int(roi_cx) + 10, int(roi_cy) + 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 128, 255),
                    1,
                )

                edges_with_boxes = RoiDetector.split_square_into_edges_with_boxes(cv_image, chosen_square)
                edges = [roi for roi, _, _ in edges_with_boxes]
                edge_names = ['top', 'right', 'bottom', 'left']

                # Save tiled edge visualization for first position only
                if edges_tile_path is None and edges:
                    vis_edges, _ = RoiDetector.create_debug_visualization(edges)
                    edges_tile_path = output_dir / f'mtf_edges_{timestamp}.jpg'
                    cv2.imwrite(str(edges_tile_path), vis_edges)

                for roi, (x, y, w_box, h_box), name in edges_with_boxes:
                    cv2.rectangle(vis_img, (x, y), (x + w_box, y + h_box), (0, 0, 255), 2)
                    cv2.putText(
                        vis_img,
                        f'edge:{name}',
                        (x, max(0, y - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 0, 255),
                        1,
                    )
                
                for i, edge_img in enumerate(edges):
                    edge_name = edge_names[i] if i < 4 else f'edge_{i}'
                    
                    contrast = RoiDetector.calculate_michelson_contrast(edge_img)
                    result = analyzer.compute_mtf(edge_img)
                    
                    if result.valid:
                        if result.frequencies.size and result.mtf_values.size and len(mtf_curves) < 6:
                            mtf_curves.append({
                                'label': f'{pos_name}-{edge_name}',
                                'frequencies': result.frequencies,
                                'mtf_values': result.mtf_values,
                                'nyquist_lpmm': result.nyquist_frequency,
                            })
                        results.append({
                            'timestamp': datetime.now().isoformat(),
                            'config': request.config_name or 'default',
                            'position': pos_name,
                            'edge': edge_name,
                            'roi_x': int(roi_cx),
                            'roi_y': int(roi_cy),
                            'mtf50_lpmm': f'{result.mtf50:.2f}',
                            'mtf20_lpmm': f'{result.mtf20:.2f}',
                            'mtf10_lpmm': f'{result.mtf10:.2f}',
                            'edge_angle_deg': f'{result.edge_angle:.2f}',
                            'contrast': f'{contrast:.3f}',
                            'nyquist_lpmm': f'{result.nyquist_frequency:.2f}',
                            'valid': 'true',
                        })
                        mtf50_values.append(result.mtf50)
                        mtf20_values.append(result.mtf20)
                        mtf10_values.append(result.mtf10)
                    else:
                        edges_failed += 1
                        results.append({
                            'timestamp': datetime.now().isoformat(),
                            'config': request.config_name or 'default',
                            'position': pos_name,
                            'edge': edge_name,
                            'roi_x': int(roi_cx),
                            'roi_y': int(roi_cy),
                            'mtf50_lpmm': '0',
                            'mtf20_lpmm': '0',
                            'mtf10_lpmm': '0',
                            'edge_angle_deg': '0',
                            'contrast': f'{contrast:.3f}',
                            'nyquist_lpmm': '0',
                            'valid': 'false',
                            'error': result.error_msg,
                        })
                
                # Only measure center for now (field test would need multiple targets)
                if not request.field_test:
                    break
        
        # Write CSV
        csv_path = output_dir / f'mtf_verification_{timestamp}.csv'
        
        fieldnames = ['timestamp', 'config', 'position', 'edge', 'roi_x', 'roi_y',
                'mtf50_lpmm', 'mtf20_lpmm', 'mtf10_lpmm', 'edge_angle_deg',
                'contrast', 'nyquist_lpmm', 'valid', 'error']
        
        self._write_csv_with_metadata(csv_path, metadata, fieldnames, results)

        plotter = VerificationPlotter(self._node.get_logger())
        plot_path = output_dir / f'mtf_results_{timestamp}.png'
        if plotter.plot_mtf_verification(results, str(plot_path), curves=mtf_curves):
            self._node.get_logger().info(f'MTF plot saved: {plot_path}')
        
        # Calculate statistics
        mtf50_mean = float(np.mean(mtf50_values)) if mtf50_values else 0.0
        mtf50_std = float(np.std(mtf50_values)) if len(mtf50_values) > 1 else 0.0
        mtf20_mean = float(np.mean(mtf20_values)) if mtf20_values else 0.0
        mtf10_mean = float(np.mean(mtf10_values)) if mtf10_values else 0.0
        
        response.success = True
        response.status_message = f'MTF verification complete. CSV: {csv_path}'
        response.csv_path = str(csv_path)
        response.mtf50_mean = mtf50_mean
        response.mtf50_std = mtf50_std
        response.mtf20_mean = mtf20_mean
        response.mtf10_mean = mtf10_mean
        response.edges_measured = len(mtf50_values)
        response.edges_failed = edges_failed

        return response
