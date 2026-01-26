"""Verification callbacks for scientific validation of autofocus and MTF measurements."""

from datetime import datetime
from pathlib import Path
import time
import csv
import numpy as np

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
                best_pos, best_score, measurements = self._run_autofocus_loop(af, clients)
                
                duration = time.time() - algo_start
                
                # Store reference position from exhaustive
                if name == 'exhaustive' and rep == 0 and best_pos is not None:
                    reference_position = best_pos
                
                # Calculate deviation from reference
                deviation = 0.0
                if reference_position is not None and best_pos is not None:
                    deviation = best_pos - reference_position
                
                results.append({
                    'timestamp': datetime.now().isoformat(),
                    'algorithm': name,
                    'focus_position_mm': f'{best_pos:.4f}' if best_pos else 'N/A',
                    'focus_score': f'{best_score:.0f}',
                    'duration_s': f'{duration:.2f}',
                    'measurements': measurements,
                    'deviation_from_ref_mm': f'{deviation:.4f}',
                    'repetition': rep + 1,
                })
                
                self._node.get_logger().info(
                    f'{name}: pos={best_pos:.3f}mm, score={best_score:.0f}, '
                    f'time={duration:.1f}s, dev={deviation:.4f}mm'
                )
        
        # Write CSV
        output_dir = self._get_output_dir('verification')
        timestamp = self._get_timestamp()
        csv_path = output_dir / f'autofocus_verification_{timestamp}.csv'
        
        fieldnames = ['timestamp', 'algorithm', 'focus_position_mm', 'focus_score',
                        'duration_s', 'measurements', 'deviation_from_ref_mm', 'repetition']
        
        self._write_csv_with_metadata(csv_path, metadata, fieldnames, results)
        
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
        
        self._node.get_logger().info(
            f'MTF Verification: field_test={request.field_test}, config={request.config_name}'
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
        
        pixel_size_um = self._node.get_parameter('pixel_size_um').value or 2.40  # IDS U3-3800CP
        config = MTFConfig(pixel_size_um=pixel_size_um)
        analyzer = MTFAnalyzer(config)
        
        results = []
        mtf50_values = []
        mtf20_values = []
        mtf10_values = []
        edges_failed = 0
        
        # Detect targets
        _, bars, squares = RoiDetector.detect_targets(cv_image)
        
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
        
        # For each position, find nearest target and measure
        for pos_name, target_x, target_y in positions:
            self._node.get_logger().info(f'Measuring at {pos_name} ({target_x}, {target_y})')
            
            # Find squares or use detected ROIs
            if squares:
                # Use largest square
                largest_square = max(squares, key=lambda r: r[1][0] * r[1][1])
                edges = RoiDetector.split_square_into_edges(cv_image, largest_square)
                edge_names = ['top', 'right', 'bottom', 'left']
                
                for i, edge_img in enumerate(edges):
                    edge_name = edge_names[i] if i < 4 else f'edge_{i}'
                    
                    contrast = RoiDetector.calculate_michelson_contrast(edge_img)
                    result = analyzer.compute_mtf(edge_img)
                    
                    if result.valid:
                        results.append({
                            'timestamp': datetime.now().isoformat(),
                            'config': request.config_name or 'default',
                            'position': pos_name,
                            'edge': edge_name,
                            'roi_x': target_x,
                            'roi_y': target_y,
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
                            'roi_x': target_x,
                            'roi_y': target_y,
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
        output_dir = self._get_output_dir('verification')
        timestamp = self._get_timestamp()
        csv_path = output_dir / f'mtf_verification_{timestamp}.csv'
        
        fieldnames = ['timestamp', 'config', 'position', 'edge', 'roi_x', 'roi_y',
                        'mtf50_lpmm', 'mtf20_lpmm', 'mtf10_lpmm', 'edge_angle_deg',
                        'contrast', 'nyquist_lpmm', 'valid']
        
        self._write_csv_with_metadata(csv_path, metadata, fieldnames, results)
        
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
