"""Centralized ROS-parameter to MTFConfig mapping."""

from __future__ import annotations

from .algorithms.mtf_analysis import MTFConfig


MTF_PARAM_MAP = (
    ("mtf.lsf_window_mode", "lsf_window_mode", str, True),
    ("mtf.lsf_peak_window_size", "lsf_peak_window_size", int, False),
    ("mtf.derivative_mode", "derivative_mode", str, True),
    ("mtf.apply_derivative_correction", "apply_derivative_correction", bool, False),
    ("mtf.derivative_correction_max", "derivative_correction_max", float, False),
    ("mtf.apply_angle_correction", "apply_angle_correction", bool, False),
    ("mtf.esf_smooth_mode", "esf_smooth_mode", str, True),
    ("mtf.esf_sg_window", "esf_sg_window", int, False),
    ("mtf.esf_sg_poly", "esf_sg_poly", int, False),
    ("mtf.edge_validation_mode", "edge_validation_mode", str, True),
    ("mtf.edge_validation_percentile", "edge_validation_percentile", float, False),
    ("mtf.edge_validation_min_points", "edge_validation_min_points", int, False),
    ("mtf.clip_to_nyquist", "clip_to_nyquist", bool, False),
    ("mtf.export_dual_curves", "export_dual_curves", bool, False),
    ("mtf.clip_max", "mtf_clip_max", float, False),
    ("mtf.warn_threshold", "mtf_warn_threshold", float, False),
)


def apply_mtf_param_mapping(config: MTFConfig, get_param_raw) -> None:
    """Apply declarative parameter overrides to a config object."""
    for param_name, attr_name, cast, require_truthy in MTF_PARAM_MAP:
        raw = get_param_raw(param_name, None)
        if raw is None:
            continue
        if require_truthy and not raw:
            continue
        try:
            setattr(config, attr_name, cast(raw))
        except Exception:
            continue
