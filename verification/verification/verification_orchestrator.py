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

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_srvs.srv import Trigger
from .plotting.plotter import ResultsPlotter

from promoc_assembly_interfaces.srv import (
    RunVerification,
    AutoFocus,
    MeasureMTF,
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
        
        # Service Clients
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
        self.logic = VerificationLogic(self, self.axis_clients)

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
            'operator': request.operator_name,
            'notes': request.notes,
            'timestamp': datetime.now().isoformat(),
            'start_pos': request.start_position_mm if request.start_position_mm != request.end_position_mm else 0.0,
            'end_pos': request.end_position_mm if request.start_position_mm != request.end_position_mm else 10.0,
            'repetitions': request.repetitions if request.repetitions > 0 else 3,
            'step_size': request.step_size_mm if request.step_size_mm > 0 else 0.5,
            'focus_position_mm': request.focus_position_mm if hasattr(request, 'focus_position_mm') else 0.0
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
            
            # Check services first
            self.get_logger().info("Checking hardware connectivity...")
            self.logic._check_services() # Add this method to Logic or call here if logic has access
                                         # Logic has access to clients but maybe better to keep clean.
                                         # Let's add it to Logic class.
            
            # Input Validation
            if self.current_config['start_pos'] >= self.current_config['end_pos']:
                raise ValueError("Start position must be less than end position")

            # --- PHASE 1: Autofocus Verification ---
            if self.current_config['run_af']:
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
            
            # --- PHASE 2: MTF Baseline ---
            if self.current_config['run_mtf']:
                self.state = VerificationState.BASELINE_MTF
                self.get_logger().info("Starting Baseline MTF...")
                
                # Determine focus position
                best_pos = None
                
                # Check if AF was run in this session
                if 'af_verification' in self.results:
                    best_pos = self.results['af_verification'].get('best_pos')
                    self.get_logger().info(f"Using AF result: {best_pos}mm")
                
                # Check if manual position was provided
                elif self.current_config.get('focus_position_mm', 0.0) > 0:
                    best_pos = self.current_config['focus_position_mm']
                    self.get_logger().info(f"Using manual focus position: {best_pos}mm")
                
                # Otherwise: Quick AF
                else:
                    self.get_logger().info("Running Quick-AF (GoldenSection) to find focus...")
                    start_pos = self.current_config.get('start_pos', 0.0)
                    end_pos = self.current_config.get('end_pos', 10.0)
                    config = AutofocusConfig(start_mm=start_pos, end_mm=end_pos, step_mm=0.2)
                    from .algorithms import GoldenSectionAutofocus
                    af = GoldenSectionAutofocus(config)
                    best_pos, score, _ = self.logic._run_autofocus_loop(af)
                    
                    if best_pos is None:
                        raise RuntimeError("Quick-AF failed to find focus!")
                    
                    self.get_logger().info(f"Quick-AF found focus at {best_pos}mm (Score: {score})")
                
                # Move to focus position
                self.axis_clients['move'].call(MoveAbsolute.Request(axis_position=best_pos))
                self.logic._wait_for_axis_idle()
                
                # Measure MTF locally (N=10 repetitions)
                mtf_res = self.logic.run_mtf_verification(repetitions=10)
                self.results['baseline_mtf'] = mtf_res
                self.get_logger().info(f"Baseline MTF50: {mtf_res.get('mtf50_mean', 'N/A')} +/- {mtf_res.get('mtf50_std', 0.0)}")

                # --- PHASE 3: User Interaction ---
                self.state = VerificationState.WAITING_FOR_USER
                self.get_logger().warn("PLEASE INSERT STRAHLTEILER AND CALL /verification_orchestrator/resume_verification")
                self.resume_event.clear()
                self.resume_event.wait() # Blocks until set

                # --- PHASE 4: Strahlteiler Verification ---
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
                     
                     # Check Significance
                     bl_std = self.results['baseline_mtf']['mtf50_std']
                     diff = bl_mean - st_mean
                     is_significant = diff > (2 * bl_std)
                     self.results['st_verification']['significant_degradation'] = bool(is_significant)
                     self.get_logger().info(f"Degradation: {deg:.2f}% (Significant: {is_significant})")

                # --- Export & Visualization ---

                self.get_logger().info("Generating Reports...")
                plotter = ResultsPlotter(results_dir)
                
                report_paths = {}
                
                # Plot AF Results
                if 'af_verification_raw' in self.results:
                    path = plotter.plot_autofocus_verification(
                        self.results['af_verification_raw'],
                        filename=f"af_verification_{datetime.now().strftime('%H%M%S')}.png"
                    )
                    report_paths['af_plot'] = str(path)
                
                # Plot MTF Results
                if 'st_verification' in self.results and 'baseline_mtf' in self.results:
                    # Use means and std for plotting with error bars
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
                    
            self.state = VerificationState.FINISHED
            self._save_report(results_dir, report_paths)
            self._export_csv(results_dir)
            
            # Generate Markdown Report
            gen = ReportGenerator(results_dir)
            gen.generate(self.results)
            
            self.get_logger().info("Verification Pipeline Finished.")

        except Exception as e:
            self.state = VerificationState.ERROR
            self.get_logger().error(f"Verification Failed: {e}", exc_info=True)

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
