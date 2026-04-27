"""Camera-node parameter defaults and lightweight grouped loading."""

from __future__ import annotations

from types import SimpleNamespace


ALL_PARAM_VALUES: tuple[tuple[str, object], ...] = (
    ("pixel_size_um", 2.40),
    ("default_roi_width", 200),
    ("default_roi_height", 200),
    ("measurement.username", ""),
    ("measurement.base_path", ""),
    ("enable_debug_overlay", False),
    ("camera.expected_width", 0),
    ("camera.expected_height", 0),
    ("camera.default_exposure_us", 0.0),
    ("camera.min_exposure_us", 0.0),
    ("camera.max_exposure_us", 0.0),
    ("camera.default_pixel_format", "RGB8"),
    ("camera.image_topic", "/promoc/promoc_camera/stream0/image_raw"),
    ("camera.camera_info_topic", "/promoc/promoc_camera/stream0/camera_info"),
    ("camera.param_set_service_primary", "/promoc/promoc_camera/set_parameters"),
    (
        "camera.param_set_service_secondary",
        "/promoc/promoc_camera_controller/set_parameters",
    ),
    ("camera.driver_declared_parameters_json", ""),
    ("autofocus.refinement_samples", 51),
    ("autofocus.min_step_mm", 0.01),
    ("autofocus.refinement_shrink_factor", 0.35),
    ("autofocus.analysis_roi_width_px", 2000),
    ("autofocus.analysis_roi_height_px", 2000),
    ("autofocus.analysis_downsample_max_dim_px", 1024),
    ("autofocus.analysis_use_center_roi", True),
    ("autofocus.analysis_log_effective_roi", True),
    ("autofocus.exposure_guard_s", 0.02),
    ("autofocus.profile_table_json", ""),
    ("autofocus.refinement_mode", 0),
    ("autofocus.fly_over.scan_speed_fast", 10.0),
    ("autofocus.fly_over.step_size_coarse", 0.5),
    ("autofocus.fly_over.step_size_fine", 0.01),
    ("autofocus.fly_over.detection_stddev_threshold", 15.0),
    ("autofocus.fly_over.roi_size", 512),
    ("autofocus.fly_over.backtrack_mm", 2.0),
    ("autofocus.fly_over.coarse_scan_range_mm", 10.0),
    ("autofocus.fly_over.fine_scan_range_mm", 0.3),
    ("autofocus.fly_over.coarse_drop_ratio", 0.6),
    ("autofocus.fly_over.fine_drop_ratio", 0.8),
    ("autofocus.fly_over.settle_coarse_s", 0.2),
    ("autofocus.fly_over.settle_fine_s", 0.3),
    ("autofocus.fly_over.use_sift_weighting", False),
    ("autofocus.fly_over.detection_poll_s", 0.05),
    ("autofocus.fly_over.max_sample_step_mm", 0.10),
    ("autofocus.fly_over.axis_speed_scale_default", 1.0),
    ("autofocus.fly_over.smooth_window_samples", 5),
    ("autofocus.fly_over.baseline_percentile", 20.0),
    ("autofocus.fly_over.snr_threshold", 3.0),
    ("autofocus.fly_over.full_scan_for_peak", True),
    ("autofocus.fly_over.peak_window_ratio", 0.9),
    ("autofocus.fly_over.peak_window_margin_mm", 1.0),
    ("autofocus.fly_over.peak_window_guard_mm", 1.5),
    ("autofocus.fly_over.min_peak_window_width_mm", 6.0),
    ("autofocus.fly_over.high_mag_threshold_x", 4.0),
    ("autofocus.fly_over.very_high_mag_threshold_x", 6.0),
    ("autofocus.fly_over.scan_speed_high_mag", 2.0),
    ("autofocus.fly_over.scan_speed_very_high_mag", 1.0),
    ("autofocus.fly_over.coarse_step_high_mag_mm", 0.10),
    ("autofocus.fly_over.coarse_step_very_high_mag_mm", 0.05),
    ("autofocus.fly_over.min_step_high_mag_mm", 0.005),
    ("autofocus.fly_over.settle_high_mag_s", 0.20),
    ("autofocus.fly_over.settle_very_high_mag_s", 0.25),
    ("autofocus.fly_over.refinement_strategy", "linear"),
    ("autofocus.fly_over.refinement_mode", 0),
    ("measurement_conditions.coaxial_light_voltage", 0.0),
    ("measurement_conditions.coaxial_light_current", 0.0),
    ("measurement_conditions.camera_objective", "unknown"),
    ("measurement_conditions.notes", ""),
    ("mtf.debug_export_dir", ""),
    ("mtf.debug_export_prefix", "mtf"),
    ("mtf.debug_export_csv", True),
    ("mtf.debug_export_png", False),
    ("mtf.profile", "default"),
    ("mtf.lsf_window_mode", "peak"),
    ("mtf.lsf_peak_window_size", 0),
    ("mtf.derivative_mode", "iso"),
    ("mtf.apply_derivative_correction", True),
    ("mtf.derivative_correction_max", 1.15),
    ("mtf.apply_angle_correction", True),
    ("mtf.esf_smooth_mode", "sg"),
    ("mtf.esf_sg_window", 11),
    ("mtf.esf_sg_poly", 2),
    ("mtf.edge_validation_mode", "warn"),
    ("mtf.edge_validation_percentile", 90.0),
    ("mtf.edge_validation_min_points", 50),
    ("mtf.angle_estimation_mode", "hybrid"),
    ("mtf.angle_allow_phase_fallback", True),
    ("mtf.angle_consistency_warn_deg", 1.5),
    ("mtf.angle_min_support_points", 20),
    ("mtf.analysis_strip_width_px", 60),
    ("mtf.edge_validation_only_auto", False),
    ("mtf.roi_detection.min_contour_area_px", 500),
    ("mtf.roi_detection.min_square_area_px", 2500),
    ("mtf.roi_detection.min_square_side_px", 40),
    ("mtf.roi_detection.min_edge_roi_width_px", 20),
    ("mtf.roi_detection.edge_roi_width_px", 60),
    ("mtf.clip_to_nyquist", True),
    ("mtf.export_dual_curves", False),
    ("mtf.clip_max", 0.0),
    ("mtf.warn_threshold", 1.05),
    ("mtf.use_full_frame", False),
    ("mtf.use_raw_capture", True),
    ("mtf.capture_required_raw", True),
    ("mtf.capture_pixel_format", "BayerRG12"),
    ("mtf.capture_bayer_pattern", "RGGB"),
    ("mtf.capture_width", 5536),
    ("mtf.capture_height", 3692),
    ("mtf.capture_offset_x", 0),
    ("mtf.capture_offset_y", 0),
    ("mtf.capture_binning", 1),
    ("mtf.capture_gain", 0.0),
    ("mtf.capture_exposure_us", 0.0),
    ("mtf.capture_settle_s", 0.35),
    ("mtf.capture_image_timeout_s", 2.0),
    ("mtf.capture_disable_exposure_auto", True),
    ("mtf.capture_disable_gain_auto", True),
    ("mtf.capture_disable_white_balance_auto", True),
    ("mtf.capture_disable_gamma", True),
    ("mtf.capture_disable_color_transform", True),
    ("mtf.skip_runtime_switch_if_live_raw", True),
    ("mtf.raw_green_pair_warn_pct", 10.0),
    ("mtf.green_wavelength_um", 0.555),
    ("mtf.restore_after_measurement", True),
    ("mtf.restore_settle_s", 0.15),
    ("mtf.log_format_switch", True),
    ("exposure.settle_frames_after_set", 2),
    ("exposure.frame_timeout_s", 1.0),
    ("exposure.readback_tolerance_us", 500.0),
)

ACTIVE_PARAM_VALUES: tuple[tuple[str, object], ...] = ALL_PARAM_VALUES

_GROUP_SPECS: dict[str, tuple[tuple[str, str, type, object], ...]] = {
    "core": (
        ("pixel_size_um", "pixel_size_um", float, 2.40),
        ("default_roi_width", "default_roi_width", int, 200),
        ("default_roi_height", "default_roi_height", int, 200),
        ("enable_debug_overlay", "enable_debug_overlay", bool, False),
        ("camera.expected_width", "expected_width", int, 0),
        ("camera.expected_height", "expected_height", int, 0),
        ("camera.default_exposure_us", "default_exposure_us", float, 0.0),
        ("camera.min_exposure_us", "min_exposure_us", float, 0.0),
        ("camera.max_exposure_us", "max_exposure_us", float, 0.0),
        ("camera.default_pixel_format", "default_pixel_format", str, "RGB8"),
        (
            "camera.image_topic",
            "image_topic",
            str,
            "/promoc/promoc_camera/stream0/image_raw",
        ),
        (
            "camera.camera_info_topic",
            "camera_info_topic",
            str,
            "/promoc/promoc_camera/stream0/camera_info",
        ),
        (
            "camera.param_set_service_primary",
            "param_set_service_primary",
            str,
            "/promoc/promoc_camera/set_parameters",
        ),
        (
            "camera.param_set_service_secondary",
            "param_set_service_secondary",
            str,
            "/promoc/promoc_camera_controller/set_parameters",
        ),
        (
            "camera.driver_declared_parameters_json",
            "driver_declared_parameters_json",
            str,
            "",
        ),
    ),
    "measurement": (
        ("measurement.username", "username", str, ""),
        ("measurement.base_path", "base_path", str, ""),
        (
            "measurement_conditions.coaxial_light_voltage",
            "coaxial_light_voltage",
            float,
            0.0,
        ),
        (
            "measurement_conditions.coaxial_light_current",
            "coaxial_light_current",
            float,
            0.0,
        ),
        ("measurement_conditions.camera_objective", "camera_objective", str, "unknown"),
        ("measurement_conditions.notes", "notes", str, ""),
    ),
    "autofocus": (
        ("autofocus.refinement_samples", "refinement_samples", int, 51),
        ("autofocus.min_step_mm", "min_step_mm", float, 0.01),
        (
            "autofocus.refinement_shrink_factor",
            "refinement_shrink_factor",
            float,
            0.35,
        ),
        ("autofocus.analysis_roi_width_px", "analysis_roi_width_px", int, 2000),
        ("autofocus.analysis_roi_height_px", "analysis_roi_height_px", int, 2000),
        (
            "autofocus.analysis_downsample_max_dim_px",
            "analysis_downsample_max_dim_px",
            int,
            1024,
        ),
        (
            "autofocus.analysis_use_center_roi",
            "analysis_use_center_roi",
            bool,
            True,
        ),
        (
            "autofocus.analysis_log_effective_roi",
            "analysis_log_effective_roi",
            bool,
            True,
        ),
        ("autofocus.exposure_guard_s", "exposure_guard_s", float, 0.02),
        ("autofocus.profile_table_json", "profile_table_json", str, ""),
        ("autofocus.refinement_mode", "refinement_mode", int, 0),
        (
            "autofocus.fly_over.refinement_strategy",
            "fly_over_refinement_strategy",
            str,
            "linear",
        ),
        ("autofocus.fly_over.refinement_mode", "fly_over_refinement_mode", int, 0),
    ),
    "mtf": (
        ("mtf.profile", "profile", str, "default"),
        ("mtf.use_full_frame", "use_full_frame", bool, False),
        ("mtf.use_raw_capture", "use_raw_capture", bool, True),
        ("mtf.capture_required_raw", "capture_required_raw", bool, True),
        ("mtf.capture_pixel_format", "capture_pixel_format", str, "BayerRG12"),
        ("mtf.capture_bayer_pattern", "capture_bayer_pattern", str, "RGGB"),
        ("mtf.capture_width", "capture_width", int, 5536),
        ("mtf.capture_height", "capture_height", int, 3692),
        ("mtf.capture_binning", "capture_binning", int, 1),
        ("mtf.capture_gain", "capture_gain", float, 0.0),
        ("mtf.capture_exposure_us", "capture_exposure_us", float, 0.0),
        (
            "mtf.skip_runtime_switch_if_live_raw",
            "skip_runtime_switch_if_live_raw",
            bool,
            True,
        ),
        ("mtf.angle_estimation_mode", "angle_estimation_mode", str, "hybrid"),
        (
            "mtf.roi_detection.min_contour_area_px",
            "roi_detection_min_contour_area_px",
            int,
            500,
        ),
        (
            "mtf.roi_detection.min_square_area_px",
            "roi_detection_min_square_area_px",
            int,
            2500,
        ),
        (
            "mtf.roi_detection.min_square_side_px",
            "roi_detection_min_square_side_px",
            int,
            40,
        ),
        (
            "mtf.roi_detection.min_edge_roi_width_px",
            "roi_detection_min_edge_roi_width_px",
            int,
            20,
        ),
        (
            "mtf.roi_detection.edge_roi_width_px",
            "roi_detection_edge_roi_width_px",
            int,
            60,
        ),
        (
            "mtf.raw_green_pair_warn_pct",
            "raw_green_pair_warn_pct",
            float,
            10.0,
        ),
        ("mtf.debug_export_dir", "debug_export_dir", str, ""),
    ),
    "exposure": (
        ("exposure.settle_frames_after_set", "settle_frames_after_set", int, 2),
        ("exposure.frame_timeout_s", "frame_timeout_s", float, 1.0),
        ("exposure.readback_tolerance_us", "readback_tolerance_us", float, 500.0),
    ),
}


def declare_camera_parameters(node) -> None:
    """Declare all parameters required by camera_node and handlers."""
    for name, default in ALL_PARAM_VALUES:
        node.declare_parameter(name, default)


def get_camera_param(node, name: str, default=None):
    """Read a ROS parameter value with fallback for missing or null values."""
    if not node.has_parameter(name):
        return default
    value = node.get_parameter(name).value
    return default if value is None else value


def _load_group(node, group_name: str) -> SimpleNamespace:
    values = {}
    for param_name, attr_name, cast, default in _GROUP_SPECS[group_name]:
        try:
            values[attr_name] = cast(get_camera_param(node, param_name, default))
        except (TypeError, ValueError):
            values[attr_name] = cast(default)
    return SimpleNamespace(**values)


def load_camera_runtime_config(node) -> SimpleNamespace:
    """Load grouped runtime settings for tests and optional node consumers."""
    return SimpleNamespace(
        core=_load_group(node, "core"),
        measurement=_load_group(node, "measurement"),
        autofocus=_load_group(node, "autofocus"),
        mtf=_load_group(node, "mtf"),
        exposure=_load_group(node, "exposure"),
    )
