#!/usr/bin/env python3
import time
import json
import csv
from datetime import datetime
from pathlib import Path
from threading import Thread, Event
from sensor_msgs.msg import Image
from .logic import VerificationLogic
from .algorithms import AutofocusConfig
from .report_generator import ReportGenerator
import yaml

from ament_index_python.packages import get_package_share_directory

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_srvs.srv import Trigger
from .plotting.plotter import ResultsPlotter

from promoc_assembly_interfaces.srv import (
    RunVerification,
    # AutoFocus,  # Unused
    # MeasureMTF, # Unused
    MoveAbsolute,
    Stop,
    GetOperationStatus,
    GetPosition,
    JogAxis,
    SetVelocityParameters,
    GetVelocityParameters
)

class VerificationState:
    IDLE = "IDLE"
    AF_VERIFICATION = "AF_VERIFICATION"
    BASELINE_MTF = "BASELINE_MTF"
    WAITING_FOR_USER = "WAITING_FOR_USER"
    STRAHLTEILER_VERIFICATION = "STRAHLTEILER_VERIFICATION"
    CORRELATION_VERIFICATION = "CORRELATION_VERIFICATION"
    FINISHED = "FINISHED"
    ERROR = "ERROR"

class VerificationOrchestrator(Node):
    def __init__(self):
        super().__init__('verification_orchestrator')
        self.state = VerificationState.IDLE
        self.results = {}
        self.current_config = {}
        self.latest_image_msg = None
        
        # Parameters
        self.declare_parameter('results_dir', str(Path.home() / 'mtf_results'))
        self.declare_parameter('focus_axis_name', 'lts300_x_axis')
        self.declare_parameter('camera_topic', '/promoc/assembly_camera/stream0/image_raw')
        
        # Config Paths
        bringup_dir = Path(get_package_share_directory('promoc_bringup'))
        # Try to find bringup dir in workspace if not installed
        if not bringup_dir.exists():
             # Fallback logic for dev environment
             bringup_dir = Path(__file__).parent.parent.parent.parent / 'promoc_bringup'

        self.declare_parameter('camera_config_path', str(bringup_dir / 'config' / 'cameras' / 'ids_u3_3800cp_hq.yaml'))
        self.declare_parameter('axis_config_path', str(bringup_dir / 'config' / 'linear_axes_params.yaml'))
        
        # Load System Configuration
        self.system_config = self._load_system_config()
        
        # Services & Subscribers
        self.cb_group = ReentrantCallbackGroup()
        axis_name = self.get_parameter('focus_axis_name').value
        
        # Clients dict for Logic
        self.axis_clients = {
            'move': self.create_client(MoveAbsolute, f'/{axis_name}/move_absolute', callback_group=self.cb_group),
            'status': self.create_client(GetOperationStatus, f'/{axis_name}/get_operation_status', callback_group=self.cb_group),
            'position': self.create_client(GetPosition, f'/{axis_name}/get_position', callback_group=self.cb_group),
            'stop': self.create_client(Stop, f'/{axis_name}/stop', callback_group=self.cb_group),
            'jog': self.create_client(JogAxis, f'/{axis_name}/jog_axis', callback_group=self.cb_group),
            'set_vel': self.create_client(SetVelocityParameters, f'/{axis_name}/set_velocity_parameters', callback_group=self.cb_group),
            'get_vel': self.create_client(GetVelocityParameters, f'/{axis_name}/get_velocity_parameters', callback_group=self.cb_group),
        }

        # Subscribers
        self.create_subscription(Image, self.get_parameter('camera_topic').value, self.image_callback, 10)



        # Logic
        self.logic = VerificationLogic(self, self.axis_clients, system_config=self.system_config)

        # Service Servers
        self.run_service = self.create_service(RunVerification, '~/run_verification', self.run_verification_callback)
        self.resume_service = self.create_service(Trigger, '~/resume_verification', self.resume_verification_callback)

        # Threading
        self.verification_thread = None
        self.resume_event = Event()
        
        self.get_logger().info('Verification Orchestrator initialized.')

    def image_callback(self, msg):
        self.latest_image_msg = msg

    def run_verification_callback(self, request, response):
        if self.state != VerificationState.IDLE:
            response.success = False
            response.status_message = f"Process busy in state {self.state}"
            return response

        self.get_logger().info(f"Starting verification for operator: {request.operator_name}")
        self.current_config = {
            'run_af': request.run_autofocus_verification,
            'run_mtf': request.run_mtf_verification,
            'run_correlation': getattr(request, 'run_correlation_verification', False),
            'operator': request.operator_name,
            'notes': request.notes,
            'timestamp': datetime.now().isoformat(),
            'start_pos': request.start_position_mm if request.start_position_mm != request.end_position_mm else 0.0,
            'end_pos': request.end_position_mm if request.start_position_mm != request.end_position_mm else 10.0,
            'repetitions': request.repetitions if request.repetitions > 0 else 3,
            'step_size': request.step_size_mm if request.step_size_mm > 0 else 0.5,
            'step_size': request.step_size_mm if request.step_size_mm > 0 else 0.5,
            'focus_position_mm': request.focus_position_mm if hasattr(request, 'focus_position_mm') else 0.0,
            'environment_start': {'valid': False, 'temperature_c': 0.0, 'humidity_percent': 0.0}
        }

        self.verification_thread = Thread(target=self._verification_process)
        self.verification_thread.start()

        response.success = True
        response.status_message = "Verification process started in background."
        return response

    def resume_verification_callback(self, request, response):
        if self.state == VerificationState.WAITING_FOR_USER:
            self.get_logger().info("Resume signal received.")
            self.resume_event.set()
            response.success = True
            response.status_message = "Resuming process."
        else:
            response.success = False
            response.status_message = "Not waiting for user."
        return response

    def _check_services(self):
        """Checks if all critical services are available."""
        timeout_sec = 2.0
        for name, client in self.axis_clients.items():
            if not client.wait_for_service(timeout_sec=timeout_sec):
                raise RuntimeError(f"Service {name} unavailable after {timeout_sec}s")

    def _verification_process(self):
        try:
            results_dir = Path(self.get_parameter('results_dir').value)
            results_dir.mkdir(parents=True, exist_ok=True)
            
            self.get_logger().info("Checking hardware connectivity...")
            self.logic._check_services()
            
            self._validate_input()

            # --- PHASE 1: Autofocus Verification ---
            if self.current_config['run_af']:
                self._run_af_phase()

            # --- PHASE 1.5: Correlation Verification (AF Peak vs MTF Peak) ---
            if self.current_config['run_correlation']:
                self._run_correlation_phase()
            
            # --- PHASE 2 & 3: MTF Baseline & User Interaction ---
            best_pos = None
            if self.current_config['run_mtf']:
                best_pos = self._run_baseline_mtf_phase()

                # --- PHASE 3: User Interaction ---
                self.state = VerificationState.WAITING_FOR_USER
                self.get_logger().warn("PLEASE INSERT STRAHLTEILER AND CALL /verification_orchestrator/resume_verification")
                self.resume_event.clear()
                self.resume_event.wait() 

                # --- PHASE 4: Strahlteiler Verification ---
                self._run_strahlteiler_phase(best_pos)

            # --- Finalize ---
            self._finalize_process(results_dir)

        except Exception as e:
            self.state = VerificationState.ERROR
            self.get_logger().error(f"Verification Failed: {e}", exc_info=True)

    def _validate_input(self):
        if self.current_config['start_pos'] >= self.current_config['end_pos']:
            raise ValueError("Start position must be less than end position")

    def _run_af_phase(self):
        self.state = VerificationState.AF_VERIFICATION
        self.get_logger().info("Starting Autofocus Verification...")
        
        af_config = {
            'start_pos': self.current_config.get('start_pos', 0.0),
            'end_pos': self.current_config.get('end_pos', 10.0),
            'step_size': self.current_config.get('step_size', 0.5),
            'repetitions': self.current_config.get('repetitions', 3)
        }
        
        af_results, ref_pos = self.logic.run_autofocus_verification(af_config)
        self.results['af_verification_raw'] = af_results
        
        best_overall = ref_pos if ref_pos else (af_results[0]['focus_position_mm'] if af_results else 5.0)
        self.results['af_verification'] = {
            'success': True,
            'best_pos': best_overall
        }
        self.get_logger().info(f"AF Verification Done. Best Pos: {best_overall}")

    def _run_correlation_phase(self):
        self.state = VerificationState.CORRELATION_VERIFICATION
        self.get_logger().info("Starting Correlation Verification (AF-Peak vs MTF-Peak)...")
        
        start_pos = self.current_config.get('start_pos', 0.0)
        end_pos = self.current_config.get('end_pos', 10.0)
        step_size = self.current_config.get('step_size', 0.5)
        
        # Use existing logic
        result = self.logic.run_correlation_verification(start_pos, end_pos, step_size)
        
        if result['success']:
             self.results['correlation_verification'] = result
             self.get_logger().info(f"Correlation: Shift={result['peak_shift']:.3f}mm "
                                    f"(AF_Peak={result['max_af_pos']:.3f}, MTF_Peak={result['max_mtf_pos']:.3f})")
        else:
             self.get_logger().error(f"Correlation Verification Failed: {result.get('message')}")
             self.results['correlation_verification'] = {'success': False, 'error': result.get('message')}

    def _run_baseline_mtf_phase(self):
        self.state = VerificationState.BASELINE_MTF
        self.get_logger().info("Starting Baseline MTF...")
        
        best_pos = None
        # 1. Determine Focus Position
        if 'af_verification' in self.results:
            best_pos = self.results['af_verification'].get('best_pos')
            self.get_logger().info(f"Using AF result: {best_pos}mm")
        elif self.current_config.get('focus_position_mm', 0.0) > 0:
            best_pos = self.current_config['focus_position_mm']
            self.get_logger().info(f"Using manual focus position: {best_pos}mm")
        else:
            self.get_logger().info("Running Quick-AF (GoldenSection) to find focus...")
            config = AutofocusConfig(
                start_mm=self.current_config.get('start_pos', 0.0),
                end_mm=self.current_config.get('end_pos', 10.0),
                step_mm=0.2
            )
            from .algorithms import GoldenSectionAutofocus
            af = GoldenSectionAutofocus(config)
            best_pos, score, _ = self.logic._run_autofocus_loop(af)
            
            if best_pos is None:
                raise RuntimeError("Quick-AF failed to find focus!")
            self.get_logger().info(f"Quick-AF found focus at {best_pos}mm (Score: {score})")
        
        # 2. Move & Measure
        self.axis_clients['move'].call(MoveAbsolute.Request(axis_position=best_pos))
        self.logic._wait_for_axis_idle()
        
        mtf_res = self.logic.run_mtf_verification(repetitions=10)
        self.results['baseline_mtf'] = mtf_res
        self.get_logger().info(f"Baseline MTF50: {mtf_res.get('mtf50_mean', 'N/A')} +/- {mtf_res.get('mtf50_std', 0.0)}")
        return best_pos

    def _run_strahlteiler_phase(self, best_pos):
        self.state = VerificationState.STRAHLTEILER_VERIFICATION
        self.get_logger().info("Starting Strahlteiler Verification...")
        
        # Re-Focus (Shift expected)
        config = AutofocusConfig(start_mm=best_pos-2.0, end_mm=best_pos+2.0, step_mm=0.1)
        from .algorithms import GoldenSectionAutofocus
        af = GoldenSectionAutofocus(config)
        new_best_pos, _, _ = self.logic._run_autofocus_loop(af)
        
        if new_best_pos is None:
            new_best_pos = best_pos # Fallback
        
        self.results['st_verification'] = {
            'new_pos': new_best_pos,
            'shift': new_best_pos - best_pos
        }
        
        self.axis_clients['move'].call(MoveAbsolute.Request(axis_position=new_best_pos))
        self.logic._wait_for_axis_idle()

        # Measure MTF
        st_mtf = self.logic.run_mtf_verification(repetitions=10)
        self.results['st_verification'].update(st_mtf)
        
        if 'mtf50_mean' in st_mtf and 'mtf50_mean' in self.results['baseline_mtf']:
             bl_mean = self.results['baseline_mtf']['mtf50_mean']
             st_mean = st_mtf['mtf50_mean']
             deg = (bl_mean - st_mean) / bl_mean * 100.0
             self.results['st_verification']['degradation_percent'] = deg
             
             bl_std = self.results['baseline_mtf']['mtf50_std']
             diff = bl_mean - st_mean
             is_significant = diff > (2 * bl_std)
             self.results['st_verification']['significant_degradation'] = bool(is_significant)
             self.get_logger().info(f"Degradation: {deg:.2f}% (Significant: {is_significant})")

    def _finalize_process(self, results_dir):
        self.get_logger().info("Generating Reports...")
        plotter = ResultsPlotter(results_dir)
        report_paths = {}
        
        if 'af_verification_raw' in self.results:
            path = plotter.plot_autofocus_verification(
                self.results['af_verification_raw'],
                filename=f"af_verification_{datetime.now().strftime('%H%M%S')}.png"
            )
            report_paths['af_plot'] = str(path)
        
        if 'st_verification' in self.results and 'baseline_mtf' in self.results:
            bl_data = {
                'mtf50': self.results['baseline_mtf']['mtf50_mean'],
                'mtf50_std': self.results['baseline_mtf'].get('mtf50_std', 0)
            }
            st_data = {
                'mtf50': self.results['st_verification']['mtf50_mean'],
                'mtf50_std': self.results['st_verification'].get('mtf50_std', 0)
            }
            
            path = plotter.plot_mtf_verification(
                bl_data, 
                st_data,
                filename=f"mtf_impact_{datetime.now().strftime('%H%M%S')}.png"
            )
            report_paths['mtf_plot'] = str(path)

        if 'correlation_verification' in self.results and self.results['correlation_verification']['success']:
             path = plotter.plot_correlation_verification(
                 self.results['correlation_verification'],
                 filename=f"correlation_{datetime.now().strftime('%H%M%S')}.png"
             )
             report_paths['correlation_plot'] = str(path)

        self.state = VerificationState.FINISHED
        self.current_config['environment_end'] = {'valid': False, 'temperature_c': 0.0, 'humidity_percent': 0.0}
        
        self._save_report(results_dir, report_paths)
        self._export_csv(results_dir)
        
        gen = ReportGenerator(results_dir)
        gen.generate(self.results, self.current_config)
        
        self.get_logger().info("Verification Pipeline Finished.")

    def _load_system_config(self):
        """Load and merge system calibration from distributed config files."""
        merged_config = {'camera': {}, 'axis': {}, 'defaults': {}}
        
        # 1. Load Camera Config
        cam_path = Path(self.get_parameter('camera_config_path').value)
        try:
            if cam_path.exists():
                with open(cam_path, 'r') as f:
                    cam_data = yaml.safe_load(f)
                    
                # Extract relevant fields
                params = cam_data.get('camera_params', {})
                merged_config['camera']['name'] = params.get('cameraname', 'Unknown')
                merged_config['camera']['pixel_size_um'] = params.get('pixelsize', 2.4)
                merged_config['camera']['pixel_size_uncertainty_um'] = params.get('pixel_size_uncertainty_um', 0.05)
                merged_config['camera']['resolution'] = [params.get('sensor_resolution_h'), params.get('sensor_resolution_v')]
                
                # Calibration file path (construct relative to camera config or standard location)
                # Ideally this should be dynamic, but for now we reconstruct the package URI or verify path
                # The camera config doesn't explicitly point to the calibration YAML used by camera_info_manager, 
                # but we know it's in the same directory usually or standard path.
                # However, logic.py expects 'calibration_file' key. 
                # The 'camera_info' section in yaml HAS the matrices! We can just use that!
                
                # Check if camera_info is in the yaml (it is in the file we viewed)
                if 'camera_info' in cam_data:
                     # Pass the whole camera_info dictionary, Logic can parse it or we parse it here
                     # Actually Logic expects a path key 'calibration_file'.
                     # Let's verify existing logic.logic.py loads from file path.
                     # We should probably modify logic to accept the dict directly to be cleaner?
                     # For now, let's keep logic compatible. logic.py loads 'calibration_file'. 
                     # If we want to use the data from THIS file, we can point 'calibration_file' to THIS file 
                     # and ensure logic.py can parse it. 
                     # ids_u3_3800cp_hq.yaml contains "camera_info" key with "camera_matrix".
                     # logic._load_calibration_data expects basic opencv yaml format or standard ROS format?
                     # logic.py expects: calib_data['camera_matrix']['data']
                     # ids config has: camera_info: camera_matrix: data
                     # So if we point logic to this file, it needs to access root['camera_info']... 
                     # Existing logic just does `calib_data['camera_matrix']`.
                     
                     # Easier approach: Point 'calibration_file' to this very file 
                     # AND Update Logic to handle the nesting 'camera_info' IF it exists.
                     merged_config['camera']['calibration_file'] = str(cam_path)

            else:
                self.get_logger().warn(f"Camera config not found: {cam_path}")
        except Exception as e:
            self.get_logger().error(f"Failed to load camera config: {e}")

        # 2. Load Axis Config
        axis_path = Path(self.get_parameter('axis_config_path').value)
        axis_name = self.get_parameter('focus_axis_name').value
        try:
            if axis_path.exists():
                with open(axis_path, 'r') as f:
                    axis_data = yaml.safe_load(f)
                
                # Retrieve specific axis data
                if axis_name in axis_data:
                    node_params = axis_data[axis_name].get('ros__parameters', {})
                    calib = node_params.get('calibration', {})
                    
                    merged_config['axis']['name'] = axis_name
                    merged_config['axis']['repeatability_mm'] = calib.get('repeatability_mm', 0.002)
                    merged_config['axis']['backlash_mm'] = calib.get('backlash_mm', 0.002)
                    merged_config['axis']['accuracy_mm'] = calib.get('accuracy_mm', 0.005)
                else:
                    self.get_logger().warn(f"Axis {axis_name} not found in {axis_path}")
            else:
                self.get_logger().warn(f"Axis config not found: {axis_path}")
        except Exception as e:
             self.get_logger().error(f"Failed to load axis config: {e}")

        # Defaults
        merged_config['defaults']['mtf_algorithm_uncertainty_percent'] = 1.5
        merged_config['defaults']['confidence_level_sigma'] = 2.0
        
        self.get_logger().info("System Configuration Loaded.")
        return merged_config

    def _save_report(self, directory, report_paths=None):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = directory / f"verification_report_{ts}.json"
        
        final_data = {
            'config': self.current_config,
            'results': self.results,
            'report_paths': report_paths or {}
        }
        
        with open(path, 'w') as f:
            json.dump(final_data, f, indent=2)
        self.get_logger().info(f"Report saved to {path}")

    def _export_csv(self, directory):
        """Exports results to CSV for external analysis."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Autofocus Results CSV
        if 'af_verification_raw' in self.results:
            csv_path = directory / f"af_results_{timestamp}.csv"
            with open(csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Algorithm', 'Repetition', 'Strategy', 'Start_Pos_mm', 'Position_mm', 'Score', 'Duration_s', 'Deviation_mm', 'Measurements', 'Success'])
                for r in self.results['af_verification_raw']:
                    writer.writerow([
                        r.get('algorithm'), r.get('repetition'), r.get('start_strategy', 'N/A'), r.get('start_pos_mm', 0.0),
                        r.get('focus_position_mm'), r.get('focus_score'), r.get('duration_s'), 
                        r.get('deviation_from_ref_mm'), r.get('measurements'), r.get('success')
                    ])
            self.get_logger().info(f"Saved AF CSV: {csv_path}")

        # 2. MTF Results CSV (Detailed)
        mtf_data = []
        if 'baseline_mtf' in self.results:
            for item in self.results['baseline_mtf'].get('raw_data', []):
                item['phase'] = 'baseline'
                mtf_data.append(item)
        if 'st_verification' in self.results:
            # Merge raw data from ST verification
            for item in self.results['st_verification'].get('raw_data', []):
                item['phase'] = 'strahlteiler'
                mtf_data.append(item)
            
        if mtf_data:
            csv_path = directory / f"mtf_results_{timestamp}.csv"
            keys = mtf_data[0].keys()
            with open(csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(mtf_data)
            self.get_logger().info(f"Saved MTF CSV: {csv_path}")

        # 3. Correlation Results CSV
        if 'correlation_verification' in self.results:
            corr_res = self.results['correlation_verification']
            if corr_res.get('success'):
                csv_path = directory / f"correlation_results_{timestamp}.csv"
                with open(csv_path, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=['pos', 'tenengrad', 'mtf', 'angle'])
                    writer.writeheader()
                    writer.writerows(corr_res['data'])
                self.get_logger().info(f"Saved Correlation CSV: {csv_path}")

def main(args=None):
    rclpy.init(args=args)
    node = VerificationOrchestrator()
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
