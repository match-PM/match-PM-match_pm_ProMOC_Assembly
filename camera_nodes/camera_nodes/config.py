"""Camera-node parameter defaults and lightweight grouped loading."""

from __future__ import annotations

from types import SimpleNamespace


ALL_PARAM_VALUES: tuple[tuple[str, object], ...] = (
    ("use_simulator", False),
    ("pixel_size_um", 2.40),
    ("default_roi_width", 200),
    ("default_roi_height", 200),
    ("x_axis_node_name", "lts300_x_axis"),
    ("measurement.username", ""),
    ("measurement.base_path", ""),
    ("enable_debug_overlay", False),
    ("autofocus.refinement_samples", 51),
    ("autofocus.min_step_mm", 0.01),
    ("autofocus.refinement_shrink_factor", 0.35),
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
<<<<<<< HEAD
=======
    ("mtf.debug_export_dir", ""),
    ("mtf.debug_export_prefix", "mtf"),
    ("mtf.debug_export_csv", True),
    ("mtf.debug_export_png", False),
    ("mtf.profile", "default"),
    ("mtf.lsf_window_mode", "full"),
    ("mtf.lsf_peak_window_size", 0),
    ("mtf.derivative_mode", "iso"),
    ("mtf.apply_derivative_correction", True),
    ("mtf.derivative_correction_max", 0.0),
    ("mtf.apply_angle_correction", True),
    ("mtf.esf_smooth_mode", "none"),
    ("mtf.esf_sg_window", 11),
    ("mtf.esf_sg_poly", 2),
    ("mtf.edge_validation_mode", "warn"),
    ("mtf.edge_validation_percentile", 90.0),
    ("mtf.edge_validation_min_points", 50),
    ("mtf.edge_validation_only_auto", False),
    ("mtf.clip_to_nyquist", True),
    ("mtf.export_dual_curves", False),
    ("mtf.clip_max", 0.0),
    ("mtf.warn_threshold", 1.05),
    ("mtf.use_full_frame", False),
    ("mtf.full_frame_width", 5536),
    ("mtf.full_frame_height", 3692),
    ("mtf.full_frame_offset_x", 0),
    ("mtf.full_frame_offset_y", 0),
    ("mtf.full_frame_binning", 1),
    ("mtf.full_frame_settle_s", 0.25),
    ("mtf.full_frame_image_timeout_s", 2.0),
    ("mtf.restore_after_measurement", True),
    ("mtf.restore_settle_s", 0.15),
    ("mtf.log_format_switch", True),
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
    ("exposure.settle_frames_after_set", 2),
    ("exposure.frame_timeout_s", 1.0),
)

ACTIVE_PARAM_VALUES: tuple[tuple[str, object], ...] = ALL_PARAM_VALUES

_GROUP_SPECS: dict[str, tuple[tuple[str, str, type, object], ...]] = {
    "core": (
        ("use_simulator", "use_simulator", bool, False),
        ("pixel_size_um", "pixel_size_um", float, 2.40),
        ("default_roi_width", "default_roi_width", int, 200),
        ("default_roi_height", "default_roi_height", int, 200),
        ("x_axis_node_name", "x_axis_node_name", str, "lts300_x_axis"),
        ("enable_debug_overlay", "enable_debug_overlay", bool, False),
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
<<<<<<< HEAD
=======
    "mtf": (
        ("mtf.profile", "profile", str, "default"),
        ("mtf.use_full_frame", "use_full_frame", bool, False),
        ("mtf.full_frame_width", "full_frame_width", int, 5536),
        ("mtf.full_frame_height", "full_frame_height", int, 3692),
        ("mtf.debug_export_dir", "debug_export_dir", str, ""),
    ),
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
    "exposure": (
        ("exposure.settle_frames_after_set", "settle_frames_after_set", int, 2),
        ("exposure.frame_timeout_s", "frame_timeout_s", float, 1.0),
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
<<<<<<< HEAD
=======
        mtf=_load_group(node, "mtf"),
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
        exposure=_load_group(node, "exposure"),
    )
