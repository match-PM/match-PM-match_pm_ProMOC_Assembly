"""Objective-aware focus profile builder for autofocus callbacks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re


COARSE_STEP_MM = 0.5
FLY_OVER_SPEED_MM_S = 10.0


@dataclass(frozen=True)
class FocusProfile:
    """Parameter profile for objective-dependent autofocus behavior."""

    objective: str
    magnification_x: float | None
    beamsplitter: bool
    profile_source: str
    scan_speed_mm_s: float
    coarse_step_mm: float
    min_step_mm: float
    settle_s: float
    max_sample_step_mm: float
    axis_speed_scale: float

    def as_dict(self) -> dict:
        """Return a dictionary representation for legacy callback code."""
        return asdict(self)


class FocusProfileBuilder:
    """Build objective-aware autofocus profiles from node parameters and request."""

    def __init__(self, node):
        self._node = node

    def _param_raw(self, name: str, default=None):
        if not self._node.has_parameter(name):
            return default
        value = self._node.get_parameter(name).value
        if value is None:
            return default
        return value

    def _param_float(self, name: str, default: float) -> float:
        value = self._param_raw(name, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    def _param_str(self, name: str, default: str = "") -> str:
        value = self._param_raw(name, default)
        try:
            return str(value)
        except Exception:
            return str(default)

    @staticmethod
    def _parse_objective_magnification_x(objective: str) -> float | None:
        """Extract numeric magnification from objective string (e.g. '6x')."""
        text = str(objective or "").strip().lower()
        if not text:
            return None
        match = re.search(r"(\d+(?:[.,]\d+)?)\s*x", text)
        if not match:
            match = re.search(r"(\d+(?:[.,]\d+)?)", text)
        if not match:
            return None
        try:
            return float(match.group(1).replace(",", "."))
        except ValueError:
            return None

    @staticmethod
    def _normalize_profile_values(values: dict) -> dict:
        """Keep only numeric autofocus profile keys."""
        if not isinstance(values, dict):
            return {}
        out = {}
        for key in (
            "scan_speed_mm_s",
            "coarse_step_mm",
            "min_step_mm",
            "settle_s",
            "max_sample_step_mm",
            "axis_speed_scale",
        ):
            if key not in values:
                continue
            try:
                out[key] = float(values[key])
            except (TypeError, ValueError):
                continue
        return out

    @staticmethod
    def _magnification_tokens(mag_x: float | None) -> list[str]:
        """Generate possible magnification keys for profile lookup."""
        if mag_x is None or mag_x <= 0:
            return []
        tokens = []
        rounded = int(round(mag_x))
        if abs(mag_x - rounded) < 1e-3:
            tokens.append(f"{rounded}x")
        text = f"{mag_x:g}x"
        if text not in tokens:
            tokens.append(text)
        return tokens

    def _get_profile_overrides(self, mag_x: float | None, beamsplitter: bool) -> tuple[dict, str]:
        """Load optional autofocus profile overrides from JSON parameter."""
        raw = self._param_str("autofocus.profile_table_json", "").strip()
        if not raw:
            return {}, "heuristic"
        try:
            table = json.loads(raw)
        except Exception as exc:
            self._node.get_logger().warn(f"Invalid autofocus.profile_table_json: {exc}")
            return {}, "heuristic"
        if not isinstance(table, dict):
            return {}, "heuristic"

        profiles = table.get("profiles", table)
        if not isinstance(profiles, dict):
            return {}, "heuristic"

        merged = self._normalize_profile_values(table.get("default", {}))
        source = "default"
        bs_key = "bs1" if beamsplitter else "bs0"

        mag_keys = self._magnification_tokens(mag_x)
        for key in mag_keys:
            if key in profiles:
                merged.update(self._normalize_profile_values(profiles[key]))
                source = key

        if bs_key in profiles:
            merged.update(self._normalize_profile_values(profiles[bs_key]))
            source = bs_key

        for key in mag_keys:
            combo = f"{key}_{bs_key}"
            if combo in profiles:
                merged.update(self._normalize_profile_values(profiles[combo]))
                source = combo

        return merged, source

    def build(self, request) -> FocusProfile:
        """Build a focus profile from node parameters and autofocus request."""
        objective = self._param_str("measurement_conditions.camera_objective", "").strip()
        req_mag = float(getattr(request, "objective_magnification_x", 0.0) or 0.0)
        beamsplitter = bool(getattr(request, "use_beamsplitter", False))
        mag_x = req_mag if req_mag > 0 else self._parse_objective_magnification_x(objective)

        base_scan_speed = self._param_float("autofocus.fly_over.scan_speed_fast", FLY_OVER_SPEED_MM_S)
        base_coarse_step = self._param_float("autofocus.fly_over.step_size_coarse", COARSE_STEP_MM)
        base_min_step = self._param_float("autofocus.min_step_mm", 0.01)
        base_settle_s = self._param_float("autofocus.fly_over.settle_fine_s", 0.1)
        base_max_sample_step = self._param_float("autofocus.fly_over.max_sample_step_mm", 0.1)
        base_axis_speed_scale = self._param_float("autofocus.fly_over.axis_speed_scale_default", 1.0)

        high_mag_threshold = self._param_float("autofocus.fly_over.high_mag_threshold_x", 4.0)
        very_high_mag_threshold = self._param_float("autofocus.fly_over.very_high_mag_threshold_x", 6.0)
        high_mag_scan_speed = self._param_float("autofocus.fly_over.scan_speed_high_mag", 2.0)
        very_high_mag_scan_speed = self._param_float("autofocus.fly_over.scan_speed_very_high_mag", 1.0)
        high_mag_coarse_step = self._param_float("autofocus.fly_over.coarse_step_high_mag_mm", 0.1)
        very_high_mag_coarse_step = self._param_float("autofocus.fly_over.coarse_step_very_high_mag_mm", 0.05)
        high_mag_min_step = self._param_float("autofocus.fly_over.min_step_high_mag_mm", 0.005)
        high_mag_settle_s = self._param_float("autofocus.fly_over.settle_high_mag_s", 0.2)
        very_high_mag_settle_s = self._param_float("autofocus.fly_over.settle_very_high_mag_s", 0.25)

        scan_speed = base_scan_speed
        coarse_step = base_coarse_step
        min_step = base_min_step
        settle_s = base_settle_s
        max_sample_step_mm = base_max_sample_step
        axis_speed_scale = max(1e-3, base_axis_speed_scale)

        if mag_x is not None:
            if mag_x >= very_high_mag_threshold:
                scan_speed = min(scan_speed, very_high_mag_scan_speed)
                coarse_step = min(coarse_step, very_high_mag_coarse_step)
                min_step = min(min_step, high_mag_min_step)
                settle_s = max(settle_s, very_high_mag_settle_s)
            elif mag_x >= high_mag_threshold:
                scan_speed = min(scan_speed, high_mag_scan_speed)
                coarse_step = min(coarse_step, high_mag_coarse_step)
                min_step = min(min_step, high_mag_min_step)
                settle_s = max(settle_s, high_mag_settle_s)

        profile_overrides, profile_source = self._get_profile_overrides(mag_x, beamsplitter)
        if "scan_speed_mm_s" in profile_overrides and profile_overrides["scan_speed_mm_s"] > 0:
            scan_speed = profile_overrides["scan_speed_mm_s"]
        if "coarse_step_mm" in profile_overrides and profile_overrides["coarse_step_mm"] > 0:
            coarse_step = profile_overrides["coarse_step_mm"]
        if "min_step_mm" in profile_overrides and profile_overrides["min_step_mm"] > 0:
            min_step = profile_overrides["min_step_mm"]
        if "settle_s" in profile_overrides and profile_overrides["settle_s"] >= 0:
            settle_s = profile_overrides["settle_s"]
        if "max_sample_step_mm" in profile_overrides and profile_overrides["max_sample_step_mm"] > 0:
            max_sample_step_mm = profile_overrides["max_sample_step_mm"]
        if "axis_speed_scale" in profile_overrides and profile_overrides["axis_speed_scale"] > 0:
            axis_speed_scale = profile_overrides["axis_speed_scale"]

        return FocusProfile(
            objective=objective or "unknown",
            magnification_x=mag_x,
            beamsplitter=beamsplitter,
            profile_source=profile_source,
            scan_speed_mm_s=max(0.01, float(scan_speed)),
            coarse_step_mm=max(0.001, float(coarse_step)),
            min_step_mm=max(0.001, float(min_step)),
            settle_s=max(0.0, float(settle_s)),
            max_sample_step_mm=max(0.005, float(max_sample_step_mm)),
            axis_speed_scale=max(1e-3, float(axis_speed_scale)),
        )
