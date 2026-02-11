#!/usr/bin/env python3
"""Scientific verification node entry point and wiring."""

from pathlib import Path

import rclpy
from cv_bridge import CvBridge
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.node import Node
from sensor_msgs.msg import Image

from promoc_assembly_interfaces.srv import (
    AutoFocus,
    GetOperationStatus,
    GetPosition,
    MoveAbsolute,
    VerifyAutofocus,
    VerifyCorrelation,
    VerifyMTF,
)
from verification.callbacks import ScientificVerificationCallbacks
from camera_nodes.callbacks.camera_format_controller import CameraFormatController


class ScientificVerificationNode(Node, ScientificVerificationCallbacks):
    """Node for scientific verification of camera algorithms."""

    def __init__(self):
        super().__init__("scientific_verification_node")

        self.cb_group = ReentrantCallbackGroup()
        self.bridge = CvBridge()
        self.latest_image_msg = None

        self.declare_parameter("camera_topic", "/promoc/assembly_camera/stream0/image_raw")
        self.declare_parameter("autofocus_service", "/camera_node/autofocus")
        self.declare_parameter("axis_name", "lts300_x_axis")
        self.declare_parameter(
            "results_dir", str(Path.home() / "Dokumente" / "Messungen")
        )

        self.declare_parameter("pixel_size_um", 2.40)
        self.declare_parameter("mtf.debug_export_dir", "")
        self.declare_parameter("mtf.debug_export_prefix", "mtf")
        self.declare_parameter("mtf.debug_export_csv", True)
        self.declare_parameter("mtf.debug_export_png", False)
        self.declare_parameter("mtf.profile", "default")
        self.declare_parameter("mtf.lsf_window_mode", "full")
        self.declare_parameter("mtf.lsf_peak_window_size", 0)
        self.declare_parameter("mtf.derivative_mode", "iso")
        self.declare_parameter("mtf.apply_derivative_correction", True)
        self.declare_parameter("mtf.derivative_correction_max", 0.0)
        self.declare_parameter("mtf.apply_angle_correction", True)
        self.declare_parameter("mtf.esf_smooth_mode", "none")
        self.declare_parameter("mtf.esf_sg_window", 11)
        self.declare_parameter("mtf.esf_sg_poly", 2)
        self.declare_parameter("mtf.edge_validation_mode", "warn")
        self.declare_parameter("mtf.edge_validation_percentile", 90.0)
        self.declare_parameter("mtf.edge_validation_min_points", 50)
        self.declare_parameter("mtf.clip_to_nyquist", True)
        self.declare_parameter("mtf.export_dual_curves", False)
        self.declare_parameter("mtf.clip_max", 0.0)
        self.declare_parameter("mtf.warn_threshold", 1.05)
        self.declare_parameter("mtf.use_full_frame", True)
        self.declare_parameter("mtf.full_frame_width", 5536)
        self.declare_parameter("mtf.full_frame_height", 3692)
        self.declare_parameter("mtf.full_frame_offset_x", 0)
        self.declare_parameter("mtf.full_frame_offset_y", 0)
        self.declare_parameter("mtf.full_frame_binning", 1)
        self.declare_parameter("mtf.full_frame_settle_s", 0.25)
        self.declare_parameter("mtf.full_frame_image_timeout_s", 2.0)
        self.declare_parameter("mtf.restore_after_measurement", True)
        self.declare_parameter("mtf.restore_settle_s", 0.15)
        self.declare_parameter("mtf.log_format_switch", True)
        self.declare_parameter("verify_mtf.frames_per_measurement", 1)
        self.declare_parameter("verify_mtf.frame_timeout_s", 2.0)
        self.declare_parameter("verify_mtf.log_progress", True)
        self.declare_parameter("verify_correlation.frames_per_measurement", 5)
        self.declare_parameter("verify_correlation.frame_timeout_s", 2.0)
        self.declare_parameter("verify_correlation.log_progress", True)
        self.declare_parameter("verify_correlation.use_autofocus_anchor", True)
        self.declare_parameter("verify_correlation.scan_half_range_mm", 1.5)
        self.declare_parameter("verify_correlation.autofocus_focus_mode", 5)
        self.declare_parameter("verify_correlation.autofocus_skip_flyover", True)
        self.declare_parameter("verify_correlation.objective_magnification_x", 0.0)
        self.declare_parameter("verify_correlation.use_beamsplitter", False)
        self.declare_parameter("verify_correlation.roi_size_px", 300)
        self.declare_parameter("verify_correlation.use_detected_square_roi", True)

        self.verify_af_srv = self.create_service(
            VerifyAutofocus,
            "~/verify_autofocus",
            self.verify_autofocus_callback,
            callback_group=self.cb_group,
        )
        self.verify_mtf_srv = self.create_service(
            VerifyMTF,
            "~/verify_mtf",
            self.verify_mtf_callback,
            callback_group=self.cb_group,
        )
        self.verify_corr_srv = self.create_service(
            VerifyCorrelation,
            "~/verify_correlation",
            self.verify_correlation_callback,
            callback_group=self.cb_group,
        )

        self.image_sub = self.create_subscription(
            Image,
            self.get_parameter("camera_topic").value,
            self.image_callback,
            10,
        )

        self.af_client = self.create_client(
            AutoFocus,
            self.get_parameter("autofocus_service").value,
            callback_group=self.cb_group,
        )

        axis_name = self.get_parameter("axis_name").value
        self.move_client = self.create_client(
            MoveAbsolute,
            f"/{axis_name}/move_absolute",
            callback_group=self.cb_group,
        )
        self.status_client = self.create_client(
            GetOperationStatus,
            f"/{axis_name}/get_operation_status",
            callback_group=self.cb_group,
        )
        self.position_client = self.create_client(
            GetPosition,
            f"/{axis_name}/get_position",
            callback_group=self.cb_group,
        )
        self._camera_format_controller = CameraFormatController(self)

        self.get_logger().info("Scientific Verification Node initialized.")


def main(args=None):
    rclpy.init(args=args)
    node = ScientificVerificationNode()

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


if __name__ == "__main__":
    main()
