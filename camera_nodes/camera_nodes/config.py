"""Central camera node parameter declaration and typed config loading."""

from __future__ import annotations

from dataclasses import dataclass


# Keep all camera-node defaults in one place so the node wiring stays compact.
ALL_PARAM_VALUES: tuple[tuple[str, object], ...] = (
    ("use_simulator", False),
    ("mtf_csv_path", ""),
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
    ("exposure.settle_frames_after_set", 2),
    ("exposure.frame_timeout_s", 1.0),
)

# Legacy/deprecated parameters that are still declared in Release N for compatibility.
DEPRECATED_PARAMETER_REPLACEMENTS: dict[str, str] = {
    "mtf_csv_path": "mtf.debug_export_dir",
    "autofocus.fly_over.step_size_fine": "autofocus.min_step_mm",
    "autofocus.fly_over.coarse_scan_range_mm": "AutoFocus.srv request range",
    "autofocus.fly_over.fine_scan_range_mm": "autofocus.refinement_shrink_factor",
    "autofocus.fly_over.coarse_drop_ratio": "autofocus.fly_over.peak_window_ratio",
    "autofocus.fly_over.fine_drop_ratio": "autofocus.fly_over.peak_window_ratio",
    "autofocus.fly_over.settle_coarse_s": "autofocus.fly_over.settle_fine_s",
}

ACTIVE_PARAM_VALUES: tuple[tuple[str, object], ...] = tuple(
    (name, default)
    for name, default in ALL_PARAM_VALUES
    if name not in DEPRECATED_PARAMETER_REPLACEMENTS
)

DEPRECATED_PARAM_VALUES: tuple[tuple[str, object], ...] = tuple(
    (name, default)
    for name, default in ALL_PARAM_VALUES
    if name in DEPRECATED_PARAMETER_REPLACEMENTS
)

DEPRECATED_PARAM_DEFAULTS: dict[str, object] = {
    name: default for name, default in DEPRECATED_PARAM_VALUES
}


@dataclass(frozen=True)
class CameraNodeCoreConfig:
    use_simulator: bool
    pixel_size_um: float
    default_roi_width: int
    default_roi_height: int
    x_axis_node_name: str
    enable_debug_overlay: bool


@dataclass(frozen=True)
class MeasurementConfig:
    username: str
    base_path: str
    coaxial_light_voltage: float
    coaxial_light_current: float
    camera_objective: str
    notes: str


@dataclass(frozen=True)
class AutofocusConfigGroup:
    refinement_samples: int
    min_step_mm: float
    refinement_shrink_factor: float
    profile_table_json: str
    refinement_mode: int
    fly_over_refinement_strategy: str
    fly_over_refinement_mode: int


@dataclass(frozen=True)
class MtfConfigGroup:
    profile: str
    use_full_frame: bool
    full_frame_width: int
    full_frame_height: int
    debug_export_dir: str


@dataclass(frozen=True)
class ExposureConfigGroup:
    settle_frames_after_set: int
    frame_timeout_s: float


@dataclass(frozen=True)
class CameraRuntimeConfig:
    core: CameraNodeCoreConfig
    measurement: MeasurementConfig
    autofocus: AutofocusConfigGroup
    mtf: MtfConfigGroup
    exposure: ExposureConfigGroup


def declare_camera_parameters(node) -> None:
    """Declare all parameters required by camera_node and handlers."""
    for name, default in ACTIVE_PARAM_VALUES:
        node.declare_parameter(name, default)
    for name, default in DEPRECATED_PARAM_VALUES:
        node.declare_parameter(name, default)


def warn_on_deprecated_parameter_overrides(node) -> None:
    """
    Emit warnings when deprecated parameters are actively overridden.

    Default-valued deprecated parameters remain silent to avoid startup noise.
    """
    logger = node.get_logger()
    for name, replacement in DEPRECATED_PARAMETER_REPLACEMENTS.items():
        if not node.has_parameter(name):
            continue
        value = node.get_parameter(name).value
        default = DEPRECATED_PARAM_DEFAULTS.get(name)
        if value is None or value == default:
            continue
        logger.warning(
            f"Deprecated parameter '{name}' is set to '{value}'. "
            f"Use '{replacement}' instead."
        )


def _read_value(node, name: str, default):
    if not node.has_parameter(name):
        return default
    value = node.get_parameter(name).value
    return default if value is None else value


def load_camera_runtime_config(node) -> CameraRuntimeConfig:
    """Read declared ROS parameters into typed camera runtime config."""
    core = CameraNodeCoreConfig(
        use_simulator=bool(_read_value(node, "use_simulator", False)),
        pixel_size_um=float(_read_value(node, "pixel_size_um", 2.40)),
        default_roi_width=int(_read_value(node, "default_roi_width", 200)),
        default_roi_height=int(_read_value(node, "default_roi_height", 200)),
        x_axis_node_name=str(_read_value(node, "x_axis_node_name", "lts300_x_axis")),
        enable_debug_overlay=bool(_read_value(node, "enable_debug_overlay", False)),
    )

    measurement = MeasurementConfig(
        username=str(_read_value(node, "measurement.username", "")),
        base_path=str(_read_value(node, "measurement.base_path", "")),
        coaxial_light_voltage=float(
            _read_value(node, "measurement_conditions.coaxial_light_voltage", 0.0)
        ),
        coaxial_light_current=float(
            _read_value(node, "measurement_conditions.coaxial_light_current", 0.0)
        ),
        camera_objective=str(
            _read_value(node, "measurement_conditions.camera_objective", "unknown")
        ),
        notes=str(_read_value(node, "measurement_conditions.notes", "")),
    )

    autofocus = AutofocusConfigGroup(
        refinement_samples=int(_read_value(node, "autofocus.refinement_samples", 51)),
        min_step_mm=float(_read_value(node, "autofocus.min_step_mm", 0.01)),
        refinement_shrink_factor=float(
            _read_value(node, "autofocus.refinement_shrink_factor", 0.35)
        ),
        profile_table_json=str(_read_value(node, "autofocus.profile_table_json", "")),
        refinement_mode=int(_read_value(node, "autofocus.refinement_mode", 0)),
        fly_over_refinement_strategy=str(
            _read_value(node, "autofocus.fly_over.refinement_strategy", "linear")
        ),
        fly_over_refinement_mode=int(
            _read_value(node, "autofocus.fly_over.refinement_mode", 0)
        ),
    )

    mtf = MtfConfigGroup(
        profile=str(_read_value(node, "mtf.profile", "default")),
        use_full_frame=bool(_read_value(node, "mtf.use_full_frame", False)),
        full_frame_width=int(_read_value(node, "mtf.full_frame_width", 5536)),
        full_frame_height=int(_read_value(node, "mtf.full_frame_height", 3692)),
        debug_export_dir=str(_read_value(node, "mtf.debug_export_dir", "")),
    )

    exposure = ExposureConfigGroup(
        settle_frames_after_set=int(
            _read_value(node, "exposure.settle_frames_after_set", 2)
        ),
        frame_timeout_s=float(_read_value(node, "exposure.frame_timeout_s", 1.0)),
    )

    return CameraRuntimeConfig(
        core=core,
        measurement=measurement,
        autofocus=autofocus,
        mtf=mtf,
        exposure=exposure,
    )
