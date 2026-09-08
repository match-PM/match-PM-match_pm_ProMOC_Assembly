"""Versioned measurement plans. No ROS imports and no hardware side effects."""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import hashlib
import json
import math
from pathlib import Path
import re

import yaml


@dataclass
class Condition:
    campaign_id: str = ""
    condition_id: str = ""
    experiment_id: str = ""
    plan_row_number: int = 0
    setup_id: str = ""
    setup_repeat: int = 0
    operator_name: str = ""
    camera_profile: str = ""
    camera_serial: str = ""
    objective_id: str = ""
    objective_family: str = ""
    magnification_x: float = 0.0
    component_id: str = ""
    beam_angle_deg: int = 0
    target_position: str = ""
    notes: str = ""
    illumination_voltage_v: float = 0.0
    output_root: str = ""
    roi_x: int = 0
    roi_y: int = 0
    roi_width: int = 0
    roi_height: int = 0
    measurement_count: int = 50
    frames_per_measurement: int = 10
    park_position_mm: float = -1.0
    axis_min_mm: float = -1.0
    axis_max_mm: float = -1.0
    position_tolerance_mm: float = 0.01
    settle_time_s: float = 1.0
    move_timeout_s: float = 60.0
    frame_timeout_s: float = 3.0
    discard_frames: int = 3
    max_capture_attempts: int = 2
    fine_focus_half_range_mm: float = 0.5
    focus_samples: int = 21
    focus_frames: int = 3
    focus_min_prominence: float = 0.02
    focus_confirmation_ratio: float = 0.8
    exposure_min_us: float = 80.0
    exposure_max_us: float = 100000.0
    exposure_target: float = 0.75
    exposure_tolerance: float = 0.02
    exposure_max_iterations: int = 15
    exposure_check_refocus_fraction: float = 0.1
    max_saturated_fraction: float = 0.001
    expected_gain: float = 0.0
    min_free_gb: float = 2.0
    context_margin_px: int = 64

    def validate(self, *, allow_interactive_roi=False):
        data = asdict(self)
        for field in fields(self):
            value = data[field.name]
            if field.type == "str":
                if not isinstance(value, str) or "?" in value or "REPLACE" in value:
                    raise ValueError(f"Invalid/unresolved {field.name}")
            elif field.type == "int":
                if type(value) is not int:
                    raise ValueError(f"{field.name} must be an integer")
            else:
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise ValueError(f"{field.name} must be a finite number")
                setattr(self, field.name, float(value))
        for key in ("campaign_id", "condition_id", "setup_id"):
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", data[key]):
                raise ValueError(f"Invalid path-safe {key}")
        for key in ("experiment_id", "operator_name", "camera_profile", "camera_serial",
                    "objective_id", "objective_family", "component_id", "target_position"):
            if not data[key].strip():
                raise ValueError(f"Missing {key}")
        if self.plan_row_number < 1 or self.setup_repeat < 0:
            raise ValueError("A source plan row and nonnegative setup repeat are required")
        if self.magnification_x <= 0 or self.beam_angle_deg not in (0, 90):
            raise ValueError("Invalid magnification or beam angle")
        if not 19.5 <= self.illumination_voltage_v <= 20.5:
            raise ValueError("Confirm the displayed light voltage near the 20 V reference")
        if not Path(self.output_root).is_absolute() or Path(self.output_root) == Path("/"):
            raise ValueError("output_root must be an absolute measurement directory")
        if not 0 <= self.axis_min_mm < self.park_position_mm < self.axis_max_mm <= 300:
            raise ValueError("Set verified axis limits and an absolute park position inside them")
        for key in ("measurement_count", "frames_per_measurement", "focus_frames",
                    "exposure_max_iterations", "max_capture_attempts"):
            if not 1 <= data[key] <= 10000:
                raise ValueError(f"Invalid {key}")
        if not 5 <= self.focus_samples <= 201 or self.focus_samples % 2 != 1:
            raise ValueError("focus_samples must be odd, between 5 and 201")
        for key in ("position_tolerance_mm", "settle_time_s", "move_timeout_s",
                    "frame_timeout_s", "fine_focus_half_range_mm", "min_free_gb"):
            if data[key] <= 0:
                raise ValueError(f"{key} must be positive")
        if self.fine_focus_half_range_mm > 5:
            raise ValueError("Only local focus windows up to +/-5 mm are supported")
        if 2*self.fine_focus_half_range_mm/(self.focus_samples-1) < 2*self.position_tolerance_mm:
            raise ValueError("Focus grid spacing must be >= twice the position tolerance")
        if not 1 <= self.discard_frames <= 100 or not 0 <= self.context_margin_px <= 4096:
            raise ValueError("Invalid discard count or context margin")
        if not 0 < self.exposure_min_us < self.exposure_max_us <= 10000000:
            raise ValueError("Invalid finite exposure limits")
        if self.frame_timeout_s <= self.exposure_max_us / 1e6:
            raise ValueError("Frame timeout must exceed maximum exposure duration")
        if not 0.05 <= self.exposure_target <= 0.95 or not 0.001 <= self.exposure_tolerance <= 0.1:
            raise ValueError("Invalid exposure target/tolerance")
        if not 0 <= self.max_saturated_fraction <= 0.05 or self.expected_gain < 0:
            raise ValueError("Invalid saturation limit/gain")
        if not 0 < self.focus_min_prominence < 1 or not 0 < self.focus_confirmation_ratio <= 1:
            raise ValueError("Invalid focus quality thresholds")
        if not 0 < self.exposure_check_refocus_fraction <= 1:
            raise ValueError("Invalid refocus threshold")
        if not allow_interactive_roi or self.roi_width or self.roi_height:
            if min(self.roi_x, self.roi_y) < 0 or min(self.roi_width, self.roi_height) < 32:
                raise ValueError("Select a slanted-edge ROI at least 32x32 pixels")
        return self

    def fingerprint(self):
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


def _unique_yaml_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


class PlanLoader(yaml.SafeLoader):
    pass


PlanLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_yaml_mapping)


def load_plan(path, condition_id=None, overrides=None):
    """Flat typed defaults + per-condition overrides; reject misspelled fields."""
    source = Path(path).read_text(encoding="utf-8")
    plan = yaml.load(source, Loader=PlanLoader)
    if not isinstance(plan, dict) or plan.get("schema_version") != 1:
        raise ValueError("Expected measurement schema_version: 1")
    if set(plan) - {"schema_version", "campaign_id", "defaults", "conditions", "source"}:
        raise ValueError("Unknown top-level plan keys")
    conditions = plan.get("conditions")
    if not isinstance(conditions, list) or not conditions:
        raise ValueError("conditions must be a nonempty list")
    if any(not isinstance(c, dict) for c in conditions):
        raise ValueError("Each condition must be a mapping")
    ids = [c.get("condition_id") for c in conditions]
    if any(not x for x in ids) or len(ids) != len(set(ids)):
        raise ValueError("Missing or duplicate condition_id")
    allowed = {f.name for f in fields(Condition)}
    for entry in [plan.get("defaults", {}), *conditions, overrides or {}]:
        if not isinstance(entry, dict):
            raise ValueError("defaults/conditions/overrides must be mappings")
        if set(entry) - allowed:
            raise ValueError(f"Unknown condition fields: {set(entry) - allowed}")
    if condition_id is None:
        return plan, source
    if condition_id not in ids:
        raise ValueError(f"Unknown condition {condition_id}")
    data = {**plan.get("defaults", {}), **conditions[ids.index(condition_id)],
            **(overrides or {}), "campaign_id": plan["campaign_id"]}
    return Condition(**data).validate(allow_interactive_roi=True), source
