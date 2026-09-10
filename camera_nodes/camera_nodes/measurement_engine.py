"""Hardware-independent, bounded measurement state machine.

IO operations must check cancellation and use bounded waits. Raw acquisition
never filters by MTF or silently changes focus/exposure during repetitions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
import shutil
import time

import numpy as np

from .measurement_store import RunStore, atomic_json, atomic_text, csv_text, utc_now
from .intensity import aggregate_intensity, exposure_ratio
from .measurement_online import MeasurementJob, OnlineAnalysisWorker


class MeasurementError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class Cancelled(MeasurementError):
    def __init__(self):
        super().__init__("CANCELED", "Measurement canceled")


class FrameTimeout(MeasurementError):
    def __init__(self):
        super().__init__("FRAME_TIMEOUT", "Fresh frame deadline exceeded")


@dataclass(frozen=True)
class _RoiCondition:
    """Minimal condition view used when replaying a context-crop stack."""

    roi_x: int
    roi_y: int
    roi_width: int
    roi_height: int


class MeasurementEngine:
    def __init__(self, condition, io, feedback=lambda *args: None, cancel=lambda: False):
        self.c = condition.validate()
        self.io = io
        self.feedback = feedback
        self.cancel = cancel
        self.store = None
        self.index = 0
        self.completed_count = 0
        self.focus_position = math.nan
        self.exposure = math.nan
        self.last_timestamp = 0
        self.auto_exposure_result = {}

    def check(self):
        if self.cancel():
            raise Cancelled()
        self.io.check()

    def phase(self, phase, **data):
        self.check()
        self.feedback(phase, self.index, self.completed_count)
        self.store.event(phase, measurement_index=self.index, **data)

    def wait(self, seconds):
        if getattr(self.io, "simulated", False):
            self.check()
            return
        deadline = time.monotonic()+seconds
        while time.monotonic() < deadline:
            self.check()
            time.sleep(min(0.05, max(0, deadline-time.monotonic())))

    def fresh(self):
        self.check()
        frame = self.io.frame(self.last_timestamp, self.c.frame_timeout_s)
        timestamp = int(frame["source_timestamp_ns"])
        if timestamp <= self.last_timestamp:
            raise MeasurementError("STALE_FRAME", "Frame timestamps must increase")
        self.last_timestamp = timestamp
        return frame

    def flush(self):
        # Barrier is established after movement/setting + exposure guard.
        self.last_timestamp = max(self.last_timestamp, self.io.latest_timestamp())
        for _ in range(self.c.discard_frames):
            self.fresh()

    def sample(self, count=3):
        frames = [self.fresh() for _ in range(count)]
        return self.io.levels([f["image"] for f in frames], self.c)

    def in_band(self, levels):
        white = float(levels.get("white_level_norm", levels.get("bright_fraction", 0.0)))
        clipping = bool(levels.get("clipping_detected", False))
        saturated = float(
            levels.get("saturation_fraction", levels.get("saturated_fraction", 0.0))
        )
        return (
            abs(white-self.c.exposure_target) <= self.c.exposure_tolerance
            and not clipping
            and saturated <= self.c.max_saturated_fraction
        )

    def auto_exposure(self):
        self.phase("AUTO_EXPOSURE")
        stable = 0
        for iteration in range(1, self.c.exposure_max_iterations + 1):
            self.check()
            self.exposure = float(self.io.state()["values"]["exposure_time"])
            if not self.c.exposure_min_us <= self.exposure <= self.c.exposure_max_us:
                self.io.set_exposure(min(self.c.exposure_max_us, max(self.c.exposure_min_us, self.exposure)))
                self.flush()
                self.exposure = float(self.io.state()["values"]["exposure_time"])
            levels = self.sample()
            self.store.event("EXPOSURE_SAMPLE", iteration=iteration,
                             exposure_us=self.exposure, **levels)
            stable = stable+1 if self.in_band(levels) else 0
            if stable >= 2:
                self.auto_exposure_result = {
                    **levels,
                    "success": True,
                    "iterations": iteration,
                    "exposure_us": self.exposure,
                }
                return self.auto_exposure_result
            if stable:
                continue
            ratio = exposure_ratio(levels, self.c.exposure_target)
            target = float(np.clip(self.exposure*ratio, self.c.exposure_min_us, self.c.exposure_max_us))
            if abs(target-self.exposure) < 0.5:
                break
            self.io.set_exposure(target)
            self.wait(target/1e6)
            self.flush()
        raise MeasurementError("EXPOSURE_NOT_CONVERGED", "Target cannot be reached within configured limits")

    def move(self, position):
        self.check()
        if not self.c.axis_min_mm <= position <= self.c.axis_max_mm:
            raise MeasurementError("AXIS_LIMIT", "Target outside verified travel limits")
        actual = self.io.move(position, self.c.move_timeout_s, self.c.position_tolerance_mm)
        if abs(actual-position) > self.c.position_tolerance_mm:
            raise MeasurementError("POSITION_MISMATCH", "Axis position is outside tolerance")
        self.store.event("POSITION_CONFIRMED", measurement_index=self.index,
                         requested_mm=position, actual_mm=actual)
        self.wait(max(self.c.settle_time_s, self.exposure/1e6 if math.isfinite(self.exposure) else 0))
        self.flush()
        return actual

    def fine_focus(self, center):
        self.phase("FINE_FOCUS", center_mm=center)
        focus_state = self.io.state()
        lo, hi = center-self.c.fine_focus_half_range_mm, center+self.c.fine_focus_half_range_mm
        approach_position = center-self.c.inter_measurement_travel_mm
        if not self.c.axis_min_mm <= lo < hi <= self.c.axis_max_mm:
            raise MeasurementError("FOCUS_LIMIT", "Entire local focus window must fit within verified travel")
        if not self.c.axis_min_mm <= approach_position < lo-self.c.position_tolerance_mm:
            raise MeasurementError(
                "APPROACH_DIRECTION",
                "Dynamic focus approach (coarse focus minus inter-measurement travel) "
                "must lie below the complete local focus window",
            )
        rows = []
        # One deterministic increasing scan, approached from 10 mm below the
        # operator-established coarse focus. This follows moving objective
        # focus positions without requiring one absolute park value per lens.
        self.move(approach_position)
        for position in np.linspace(lo, hi, self.c.focus_samples):
            actual = self.move(float(position))
            scores = [self.io.focus_score(self.fresh()["image"], self.c) for _ in range(self.c.focus_frames)]
            score = float(np.median(scores))
            if not math.isfinite(score):
                raise MeasurementError("FOCUS_INVALID", "Nonfinite focus score")
            row = {"position_mm": actual, "requested_mm": float(position), "score": score, "stage":"scan"}
            rows.append(row)
            self.store.event("FOCUS_SAMPLE", **row)
        # Camera settings are fixed at launch and externally serialized. A
        # checkpoint after the scan detects real changes without querying the
        # driver's parameter services before every individual focus position.
        self.assert_locked(focus_state)
        best = max(range(len(rows)), key=lambda i: rows[i]["score"])
        peak = rows[best]["score"]
        if best in (0, len(rows)-1) or peak <= 0:
            raise MeasurementError("FOCUS_EDGE_PEAK", "No interior local focus maximum; adjust coarse focus")
        if (peak-min(r["score"] for r in rows))/peak < self.c.focus_min_prominence:
            raise MeasurementError("FOCUS_FLAT", "Focus curve has insufficient prominence")
        grid_spacing = (hi-lo)/(self.c.focus_samples-1)
        refine_lo, refine_hi = rows[best-1]["requested_mm"], rows[best+1]["requested_mm"]
        refine_count = min(11, int((refine_hi-refine_lo)/(2*self.c.position_tolerance_mm))+1)
        if refine_count % 2 == 0:
            refine_count -= 1
        if refine_count >= 5:
            self.move(approach_position)
            refined = []
            for position in np.linspace(refine_lo,refine_hi,refine_count):
                actual = self.move(float(position))
                score = float(np.median([self.io.focus_score(self.fresh()["image"],self.c)
                                        for _ in range(self.c.focus_frames)]))
                if not math.isfinite(score):
                    raise MeasurementError("FOCUS_INVALID", "Nonfinite refined focus score")
                row = {"position_mm":actual,"requested_mm":float(position),"score":score,"stage":"refine"}
                refined.append(row)
                self.store.event("FOCUS_SAMPLE", **row)
            self.assert_locked(focus_state)
            selected = max(range(len(refined)),key=lambda i:refined[i]["score"])
            if selected in (0,len(refined)-1):
                raise MeasurementError("FOCUS_EDGE_PEAK", "Refined maximum is on search boundary")
            best = len(rows)+selected
            rows.extend(refined)
            peak = rows[best]["score"]
            grid_spacing = (refine_hi-refine_lo)/(refine_count-1)
        self.focus_position = rows[best]["position_mm"]
        self.move(approach_position)
        self.move(self.focus_position)
        confirmation = float(np.median([self.io.focus_score(self.fresh()["image"], self.c)
                                       for _ in range(self.c.focus_frames)]))
        self.assert_locked(focus_state)
        if confirmation < peak*self.c.focus_confirmation_ratio:
            raise MeasurementError("FOCUS_NOT_REPEATABLE", "Returned focus score is below confirmation threshold")
        result = {"method": "local_exhaustive_tenengrad", "curve": rows,
                  "focus_position_mm": self.focus_position, "confirmation_score": confirmation,
                  "grid_spacing_mm": grid_spacing,
                  "approach_position_mm": approach_position}
        self.store.event("FOCUS_COMPLETE", **result)
        return result

    def assert_locked(self, baseline):
        state = self.io.state()
        if state["identity"] != baseline["identity"]:
            raise MeasurementError("DEVICE_CHANGED", "Device/reference epoch changed")
        for key, expected in baseline["values"].items():
            actual = state["values"].get(key)
            tolerance = max(1.0, abs(expected)*0.002) if key == "exposure_time" else 1e-6
            equal = (actual is not None and abs(float(actual)-float(expected)) <= tolerance
                     if type(expected) in (int, float) else actual == expected)
            if not equal:
                raise MeasurementError("CAMERA_CHANGED", f"Camera {key}: expected {expected}, read {actual}")
        return state

    @staticmethod
    def _numeric_mtf_result(result):
        """Discard large curves for non-representative frames."""
        def finite(value):
            value = float(value)
            return value if math.isfinite(value) else 0.0

        mtf50 = finite(result.mtf50)
        valid = bool(result.valid) and math.isfinite(float(result.mtf50))
        error = str(result.error_msg or "")
        if bool(result.valid) and not valid:
            error = "; ".join(value for value in (error, "nonfinite MTF50") if value)
        return {
            "valid": valid,
            "mtf50": mtf50,
            "mtf20": finite(result.mtf20),
            "mtf10": finite(result.mtf10),
            "edge_angle": finite(result.edge_angle),
            "g1_mtf50": finite(result.g1_mtf50),
            "g2_mtf50": finite(result.g2_mtf50),
            "warning": str(result.warning_msg or ""),
            "error": error,
        }

    @classmethod
    def _numeric_mtf_frame(cls, analysis):
        """Reduce four service edge results to one bounded per-frame record."""
        edges = []
        for edge in list((analysis or {}).get("edges", [])):
            numeric = cls._numeric_mtf_result(edge["result"])
            edges.append({
                "edge_label": str(edge.get("edge_label", "")),
                "edge_name": str(edge.get("edge_name", "")),
                "edge_direction": str(edge.get("edge_direction", "")),
                "bbox": [int(value) for value in edge.get("bbox", ())],
                "contrast": float(edge.get("contrast", 0.0)),
                **numeric,
            })
        valid_edges = [edge for edge in edges if edge["valid"]]
        exact_square = len(edges) == 4
        frame_valid = exact_square and len(valid_edges) == 4

        def mean(name):
            values = [float(edge[name]) for edge in valid_edges]
            return float(np.mean(values)) if values else 0.0

        errors = [edge["error"] for edge in edges if edge.get("error")]
        if not exact_square:
            errors.append(f"measure_mtf_roi detected {len(edges)}/4 cube edges")
        elif len(valid_edges) != 4:
            errors.append(f"measure_mtf_roi valid edges {len(valid_edges)}/4")
        warnings = [edge["warning"] for edge in edges if edge.get("warning")]
        return {
            "valid": frame_valid,
            "mtf50": mean("mtf50"),
            "mtf20": mean("mtf20"),
            "mtf10": mean("mtf10"),
            "edge_angle": mean("edge_angle"),
            "g1_mtf50": mean("g1_mtf50"),
            "g2_mtf50": mean("g2_mtf50"),
            "edges_valid": len(valid_edges),
            "edges_total": len(edges),
            "edges": edges,
            "warning": "; ".join(warnings),
            "error": "; ".join(errors),
        }

    @staticmethod
    def _make_analyzer(config_data):
        """Build the existing MTF analyzer without debug I/O in the producer."""
        from .algorithms.mtf import MTFAnalyzer, MTFConfig

        config = MTFConfig(**config_data)
        config.debug_export_dir = None
        config.debug_export_csv = False
        config.debug_export_png = False
        return MTFAnalyzer(config)

    def _recovery_job(self, manifest_path, preparation):
        """Rebuild a missing online result from one immutable raw capture."""
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        stack = np.load(manifest_path.parent / manifest["raw_stack"], allow_pickle=False)
        x, y, width, height = [int(value) for value in manifest["edge_bbox_in_stack"]]
        frame_results = list(manifest.get("frame_analysis", []))
        representative_result = None
        representative_edges = []
        representative_index = 0
        roi_mode = str(manifest.get("mtf_roi_mode", "legacy_direct"))
        if roi_mode == "roi_search_square4":
            search_roi = tuple(int(value) for value in manifest.get(
                "search_roi_in_stack", manifest["edge_bbox_in_stack"]
            ))
            if not frame_results:
                frame_results = []
                for image in stack:
                    try:
                        analysis = self.io.analyze_mtf_roi_frame(
                            image,
                            _RoiCondition(*search_roi),
                            manifest["analysis_config"],
                        )
                    except Exception as exc:
                        analysis = {"edges": []}
                        numeric = self._numeric_mtf_frame(analysis)
                        numeric["error"] += f"; recovery measure_mtf_roi: {exc}"
                    else:
                        numeric = self._numeric_mtf_frame(analysis)
                    frame_results.append(numeric)
            if len(stack):
                representative_index = next(
                    (i for i, row in enumerate(frame_results) if row.get("valid")), 0
                )
                analysis = self.io.analyze_mtf_roi_frame(
                    stack[representative_index],
                    _RoiCondition(*search_roi),
                    manifest["analysis_config"],
                )
                representative_edges = list(analysis.get("edges", []))
                if representative_edges:
                    representative_result = representative_edges[0]["result"]
            overview_roi = list(search_roi)
        else:
            analyzer = self._make_analyzer(manifest["analysis_config"])
            if not frame_results:
                frame_results = []
                for index, image in enumerate(stack):
                    result = analyzer.compute_mtf(
                        image[y:y+height, x:x+width],
                        roi_origin=(manifest["stack_origin"][0]+x,
                                    manifest["stack_origin"][1]+y),
                    )
                    frame_results.append(self._numeric_mtf_result(result))
                    if representative_result is None and result.valid:
                        representative_result, representative_index = result, index
            if representative_result is None and len(stack):
                representative_index = next(
                    (i for i, row in enumerate(frame_results) if row.get("valid")), 0
                )
                representative_result = analyzer.compute_mtf(
                    stack[representative_index, y:y+height, x:x+width],
                    roi_origin=(manifest["stack_origin"][0]+x,
                                manifest["stack_origin"][1]+y),
                )
            overview_roi = [x, y, width, height]
        levels = dict(manifest.get("levels", {}))
        aliases = {
            "white_level_norm": levels.get("bright_fraction", 0.0),
            "black_level_norm": levels.get("dark_fraction", 0.0),
            "saturation_fraction": levels.get("saturated_fraction", 0.0),
        }
        for key, value in aliases.items():
            levels.setdefault(key, value)
        maximum = float(levels.get("native_max", 1.0) or 1.0)
        for raw_key, norm_key in (("white_level", "white_level_norm"),
                                  ("black_level", "black_level_norm"),
                                  ("p95", "p95_norm"), ("p99_9", "p99_9_norm")):
            levels.setdefault(norm_key, levels.get("white_level_norm", 0.0))
            levels.setdefault(raw_key, float(levels[norm_key]) * maximum)
        levels.setdefault("intensity_method", "legacy_p95")
        levels.setdefault("clipping_detected", False)
        state = manifest["state_before"]["values"]
        metadata = {
            "timestamp_utc": manifest["timestamp_utc"],
            "run_id": manifest["run_id"],
            "condition_id": self.c.condition_id,
            "measurement_index": manifest["measurement_index"],
            "requested_position_mm": manifest["position_before_mm"],
            "position_before_mm": manifest["position_before_mm"],
            "position_after_mm": manifest["position_after_mm"],
            "focus_position_mm": preparation["focus_position_mm"],
            "exposure_us": state["exposure_time"],
            "gain": state["gain"],
            "auto_exposure": preparation.get("auto_exposure", {
                "success": True, "iterations": 0,
            }),
            "roi": manifest["roi"],
            "overview_roi": overview_roi,
            "overview_origin": [0, 0],
            "measurement_count": self.c.measurement_count,
            "frames_per_measurement": self.c.frames_per_measurement,
            "inter_measurement_motion": self.c.inter_measurement_motion,
            "inter_measurement_travel_mm": self.c.inter_measurement_travel_mm,
            "exposure_target": self.c.exposure_target,
            "exposure_tolerance": self.c.exposure_tolerance,
            "mtf_algorithm": manifest["analysis_config"].get("input_mode", ""),
            "mtf_roi_mode": roi_mode,
            "raw_manifest": str(manifest_path.relative_to(self.store.path)),
            "quality_flags": manifest.get("quality_flags", []),
            "capture_duration_s": 0.0,
            "mtf_compute_duration_s": 0.0,
            "raw_commit_duration_s": 0.0,
        }
        representative = stack[representative_index].copy() if len(stack) else None
        return MeasurementJob(
            metadata=metadata,
            frame_results=frame_results,
            intensity=levels,
            representative_image=None,
            representative_roi=representative,
            representative_result=representative_result,
            image_encoding=str(manifest["analysis_config"].get("source_encoding", "mono16")),
            representative_edges=representative_edges,
        )

    def run(self, plan_source="", resume_run_id=""):
        worker = None
        worker_closed = False
        resume_approach_performed = False
        try:
            self.store = RunStore(self.c, plan_source, resume_run_id)
        except BaseException:
            self.io.release()
            raise
        try:
            self.phase("VALIDATING")
            self.io.acquire(self.store.run_id)
            self.preflight = self.io.preflight(self.c)
            atomic_json(self.store.path / ("resume_preflight.json" if resume_run_id else "preflight.json"), self.preflight)
            if shutil.disk_usage(self.store.path).free < self.c.min_free_gb*1e9:
                raise MeasurementError("DISK_SPACE", "Insufficient free space")
            self.completed_count = len(self.store.completed())
            preparation_path = self.store.path / "preparation.json"
            if resume_run_id:
                if not preparation_path.exists():
                    raise MeasurementError("RESUME_NOT_PREPARED", "Preparation incomplete: create a new run")
                preparation = json.loads(preparation_path.read_text())
                self.focus_position = preparation["focus_position_mm"]
                self.exposure = preparation["exposure_us"]
                self.auto_exposure_result = dict(preparation.get("auto_exposure", {
                    "success": True, "iterations": 0, "exposure_us": self.exposure,
                }))
                baseline = preparation["locked_state"]
                self.assert_locked(baseline)
                current_position = float(self.io.position())
                if abs(current_position-self.focus_position) > self.c.position_tolerance_mm:
                    if self.c.inter_measurement_motion == "hold_focus":
                        raise MeasurementError(
                            "POSITION_DRIFT",
                            "Axis is no longer at the saved focus position for hold_focus resume",
                        )
                    resume_return = self.focus_position - self.c.inter_measurement_travel_mm
                    if resume_return < self.c.axis_min_mm:
                        raise MeasurementError(
                            "AXIS_LIMIT", "Resume approach travel exceeds the lower-axis limit"
                        )
                    self.move(resume_return)
                    self.move(self.focus_position)
                    resume_approach_performed = True
                if not self.in_band(self.sample()):
                    raise MeasurementError("RESUME_EXPOSURE", "Exposure drift: resume would require a new run")
                score = self.io.focus_score(self.fresh()["image"], self.c)
                if score < preparation["focus"]["confirmation_score"]*self.c.focus_confirmation_ratio:
                    raise MeasurementError("RESUME_FOCUS", "Focus changed: create a new run")
            else:
                center = self.io.position()
                # Validate the complete window BEFORE any AE or movement.
                focus_lo = center-self.c.fine_focus_half_range_mm
                focus_hi = center+self.c.fine_focus_half_range_mm
                approach_position = center-self.c.inter_measurement_travel_mm
                if not (
                    self.c.axis_min_mm <= approach_position
                    and approach_position < focus_lo-self.c.position_tolerance_mm
                    and focus_hi <= self.c.axis_max_mm
                ):
                    raise MeasurementError(
                        "FOCUS_LIMIT",
                        "unsafe local focus geometry: "
                        f"coarse={center:.3f} mm, window={focus_lo:.3f}..{focus_hi:.3f} mm, "
                        f"dynamic_approach={approach_position:.3f} mm, "
                        f"axis={self.c.axis_min_mm:.3f}..{self.c.axis_max_mm:.3f} mm",
                    )
                self.flush()
                self.auto_exposure_result = self.auto_exposure()
                focus = self.fine_focus(center)
                self.phase("EXPOSURE_CHECK")
                levels = self.sample()
                if not self.in_band(levels):
                    old = self.exposure
                    self.auto_exposure_result = self.auto_exposure()
                    levels = self.auto_exposure_result
                    if abs(self.exposure-old)/old >= self.c.exposure_check_refocus_fraction:
                        # Bounded single repeat, not an unbounded AF/AE loop.
                        focus = self.fine_focus(center)
                        levels = self.sample()
                        if not self.in_band(levels):
                            raise MeasurementError("PREPARATION_UNSTABLE", "AE/AF did not settle after one correction")
                baseline = self.io.state()
                preparation = {"focus": focus, "levels": levels, "locked_state": baseline,
                               "focus_position_mm": self.focus_position, "exposure_us": self.exposure,
                               "auto_exposure": self.auto_exposure_result,
                               "prepared_utc": utc_now(), "analysis_config": self.io.analysis_config()}
                reference = self.fresh()
                preparation["reference"] = self.store.save_reference(reference, levels["native_max"])
                atomic_text(self.store.path/"focus_curve.csv", csv_text(focus["curve"]))
                atomic_json(preparation_path, preparation)
            logger = None
            node = getattr(self.io, "node", None)
            if node is not None and hasattr(node, "get_logger"):
                logger = node.get_logger()
            worker = OnlineAnalysisWorker(self.store.path, logger, maxsize=1)
            return_position = self.focus_position - self.c.inter_measurement_travel_mm
            if (
                self.c.inter_measurement_motion == "park_return"
                and return_position < self.c.axis_min_mm
            ):
                raise MeasurementError(
                    "AXIS_LIMIT",
                    "The configured inter-measurement travel exceeds the available lower-axis travel",
                )
            completed = self.store.completed()
            for recovered_index, manifest_path in sorted(completed.items()):
                if recovered_index not in worker.analyzed_indices:
                    self.phase("RECOVERING_ANALYSIS", recovered_index=recovered_index)
                    worker.submit(self._recovery_job(manifest_path, preparation))

            for self.index in range(1, self.c.measurement_count+1):
                if self.index in completed:
                    continue
                self.assert_locked(baseline)
                if self.c.inter_measurement_motion == "park_return":
                    if self.completed_count > 0 and not resume_approach_performed:
                        self.phase("MOVE_AWAY_BETWEEN_MEASUREMENTS")
                        self.move(return_position)
                        self.phase("RETURN_TO_MEASUREMENT")
                        position = self.move(self.focus_position)
                    else:
                        self.phase("READY_AT_FOCUS")
                        position = float(self.io.position())
                        if abs(position-self.focus_position) > self.c.position_tolerance_mm:
                            raise MeasurementError(
                                "POSITION_DRIFT", "Axis left the focus position before first capture"
                            )
                    resume_approach_performed = False
                else:
                    self.phase("HOLD_FOCUS")
                    position = float(self.io.position())
                    if abs(position-self.focus_position) > self.c.position_tolerance_mm:
                        raise MeasurementError(
                            "POSITION_DRIFT", "Axis left the focus position while hold_focus was active"
                        )
                for retry in range(self.c.max_capture_attempts):
                    attempt, path = self.store.attempt(self.index)
                    if attempt > self.c.max_capture_attempts:
                        raise MeasurementError("ATTEMPT_LIMIT", "Total technical attempts exhausted; review and create a new run")
                    self.phase("CAPTURING", attempt=attempt)
                    partial_frames = []
                    try:
                        before = self.assert_locked(baseline)
                        capture_started = time.perf_counter()
                        raw_crops = []
                        rows = []
                        frame_results = []
                        intensity_rows = []
                        representative_image = None
                        representative_result = None
                        representative_edges = []
                        fallback_image = None
                        fallback_result = None
                        fallback_edges = []
                        point_edge_geometry = None
                        first_shape = None
                        first_dtype = None
                        mtf_compute_duration = 0.0
                        x, y, w, h = (
                            self.c.roi_x, self.c.roi_y,
                            self.c.roi_width, self.c.roi_height,
                        )
                        margin = self.c.context_margin_px
                        ox = oy = ex = ey = 0
                        for frame_index in range(self.c.frames_per_measurement):
                            frame = self.fresh()
                            image = frame.pop("image")
                            if first_shape is None:
                                first_shape, first_dtype = image.shape, image.dtype
                                ox, oy = max(0, x-margin), max(0, y-margin)
                                ex = min(image.shape[1], x+w+margin)
                                ey = min(image.shape[0], y+h+margin)
                                if x < 0 or y < 0 or x+w > image.shape[1] or y+h > image.shape[0]:
                                    raise MeasurementError("FRAME_GEOMETRY", "MTF ROI exceeds the camera frame")
                            elif image.shape != first_shape or image.dtype != first_dtype:
                                raise MeasurementError("FRAME_GEOMETRY", "Frame format changed during capture")

                            context_crop = image[oy:ey, ox:ex].copy()
                            raw_crops.append(context_crop)
                            partial_frames.append({"image": context_crop, **frame})
                            intensity = self.io.levels([image], self.c)
                            intensity_rows.append(intensity)
                            row = {"frame_index": frame_index+1, **frame, **intensity}
                            rows.append(row)

                            mtf_started = time.perf_counter()
                            try:
                                analysis = self.io.analyze_mtf_roi_frame(
                                    image, self.c, preparation["analysis_config"],
                                    point_edge_geometry,
                                )
                            except Exception as exc:
                                analysis = {"mode": "roi_search_square4", "edges": []}
                                analysis_error = str(exc)
                            mtf_compute_duration += time.perf_counter() - mtf_started
                            numeric_result = self._numeric_mtf_frame(analysis)
                            if 'analysis_error' in locals():
                                numeric_result["error"] = "; ".join(
                                    value for value in (
                                        numeric_result["error"],
                                        f"measure_mtf_roi: {analysis_error}",
                                    ) if value
                                )
                                del analysis_error
                            frame_results.append(numeric_result)
                            edge_results = list(analysis.get("edges", []))
                            if point_edge_geometry is None and len(edge_results) == 4:
                                point_edge_geometry = [
                                    {
                                        "bbox": edge["bbox"],
                                        "edge_name": edge["edge_name"],
                                        "edge_direction": edge["edge_direction"],
                                        "parent_center": edge.get("parent_center"),
                                    }
                                    for edge in edge_results
                                ]
                            if fallback_image is None:
                                fallback_image = image
                                fallback_edges = edge_results
                                fallback_result = (
                                    edge_results[0]["result"] if edge_results else None
                                )
                            if representative_image is None and numeric_result["valid"]:
                                representative_image = image
                                representative_edges = edge_results
                                representative_result = edge_results[0]["result"]
                                fallback_image = fallback_result = None
                                fallback_edges = []

                        after = self.assert_locked(baseline)
                        end_position = self.io.position()
                        if abs(end_position-self.focus_position) > self.c.position_tolerance_mm:
                            raise MeasurementError("POSITION_DRIFT", "Axis moved during capture")
                        capture_duration = time.perf_counter() - capture_started
                        stack = np.stack(raw_crops)
                        levels = aggregate_intensity(intensity_rows)
                        levels["bright_fraction"] = levels["white_level_norm"]
                        levels["dark_fraction"] = levels["black_level_norm"]
                        levels["saturated_fraction"] = levels["saturation_fraction"]
                        # Quality is recorded, never optimized by recapturing low-MTF frames.
                        intensity_drift = not self.in_band(levels)
                        flags = ["INTENSITY_OUTSIDE_TARGET"] if intensity_drift else []
                        if any(int(row.get("edges_total", 0)) != 4 for row in frame_results):
                            flags.append("MTF_ROI_EDGE_COUNT_NOT_FOUR")
                        metadata = {"measurement_index": self.index, "attempt_index": attempt,
                                    "condition": asdict(self.c), "state_before": before, "state_after": after,
                                    "position_before_mm": position, "position_after_mm": end_position,
                                    "roi": [x,y,w,h], "stack_origin": [ox,oy],
                                    "edge_bbox_in_stack": [x-ox,y-oy,w,h], "levels": levels,
                                    "mtf_roi_mode": "roi_search_square4",
                                    "search_roi_in_stack": [x-ox,y-oy,w,h],
                                    "quality_flags": flags, "analysis_config": preparation["analysis_config"],
                                    "frame_analysis": frame_results,
                                    "timestamp_utc": utc_now()}
                        if shutil.disk_usage(path).free < stack.nbytes+self.c.min_free_gb*1e9:
                            raise MeasurementError("DISK_SPACE", "Insufficient space for next stack")
                        self.phase("WRITING_RESULTS")
                        raw_commit_started = time.perf_counter()
                        manifest = self.store.commit(path, stack, rows, metadata)
                        raw_commit_duration = time.perf_counter() - raw_commit_started
                        self.completed_count = self.store.progress("running")
                        self.store.event("CAPTURE_COMMITTED", manifest=str(manifest.relative_to(self.store.path)))
                        if representative_image is None:
                            representative_image = fallback_image
                            representative_result = fallback_result
                            representative_edges = fallback_edges
                        state_values = before["values"]
                        job = MeasurementJob(
                            metadata={
                                "timestamp_utc": metadata["timestamp_utc"],
                                "run_id": self.store.run_id,
                                "condition_id": self.c.condition_id,
                                "measurement_index": self.index,
                                "requested_position_mm": self.focus_position,
                                "position_before_mm": position,
                                "position_after_mm": end_position,
                                "focus_position_mm": self.focus_position,
                                "exposure_us": state_values["exposure_time"],
                                "gain": state_values["gain"],
                                "auto_exposure": self.auto_exposure_result,
                                "roi": [x, y, w, h],
                                "overview_roi": [x, y, w, h],
                                "overview_origin": [0, 0],
                                "measurement_count": self.c.measurement_count,
                                "frames_per_measurement": self.c.frames_per_measurement,
                                "inter_measurement_motion": self.c.inter_measurement_motion,
                                "inter_measurement_travel_mm": self.c.inter_measurement_travel_mm,
                                "exposure_target": self.c.exposure_target,
                                "exposure_tolerance": self.c.exposure_tolerance,
                                "mtf_algorithm": preparation["analysis_config"].get("input_mode", ""),
                                "mtf_roi_mode": "roi_search_square4",
                                "raw_manifest": str(manifest.relative_to(self.store.path)),
                                "quality_flags": flags,
                                "capture_duration_s": capture_duration,
                                "mtf_compute_duration_s": mtf_compute_duration,
                                "raw_commit_duration_s": raw_commit_duration,
                            },
                            frame_results=frame_results,
                            intensity=levels,
                            representative_image=representative_image,
                            # The full-frame representative already contains
                            # the ROI; avoid a redundant queued crop. Recovery
                            # jobs use representative_roi because only their
                            # persisted context crop exists.
                            representative_roi=None,
                            representative_result=representative_result,
                            image_encoding=str(preparation["analysis_config"].get(
                                "source_encoding", rows[0].get("encoding", "mono16")
                            )),
                            representative_edges=representative_edges,
                        )
                        queue_wait_duration = worker.submit(job)
                        self.store.event(
                            "ANALYSIS_QUEUED", measurement_index=self.index,
                            queue_wait_duration_s=queue_wait_duration,
                        )
                        if intensity_drift:
                            raise MeasurementError("INTENSITY_DRIFT", "Raw data preserved; intensity drift requires review/new run")
                        break
                    except FrameTimeout as exc:
                        self.store.save_partial(path, partial_frames)
                        atomic_json(path / "failure.json", {"code": exc.code, "message": str(exc)})
                        self.store.event("CAPTURE_RETRY", measurement_index=self.index, attempt=attempt)
                        if retry+1 >= self.c.max_capture_attempts:
                            raise
                        self.flush()
                    except BaseException:
                        if path.exists():
                            self.store.save_partial(path, partial_frames)
                        raise
            try:
                worker.close()
            finally:
                worker_closed = True
            self.phase("COMPLETE")
            self.store.progress("complete")
            return self.result(True, "", "Acquisition and online MTF analysis complete")
        except BaseException as exc:
            if worker is not None and not worker_closed:
                try:
                    worker.close()
                    worker_closed = True
                except Exception as worker_exc:
                    try:
                        self.store.event("ANALYSIS_WORKER_FAILED", message=str(worker_exc))
                    except Exception:
                        pass
            code = getattr(exc, "code", "MEASUREMENT_FAILED")
            try:
                self.store.event("FAILED", code=code, message=str(exc))
                self.store.progress("canceled" if code == "CANCELED" else "failed", error_code=code, error=str(exc))
            except Exception:
                pass  # Original failure is authoritative, especially disk errors.
            raise
        finally:
            try:
                try:
                    self.io.release()
                except Exception as exc:
                    try:
                        self.store.event("CLEANUP_FAILED", message=str(exc))
                        self.store.progress("cleanup_failed", error=str(exc))
                    except Exception:
                        pass
                    raise
            finally:
                self.store.close()

    def result(self, success, code, message):
        return {"success": success, "error_code": code, "status_message": message,
                "run_id": self.store.run_id if self.store else "",
                "output_directory": str(self.store.path) if self.store else "",
                "completed_measurements": self.completed_count,
                "captured_frames": self.completed_count*self.c.frames_per_measurement,
                "exposure_time_us": self.exposure if math.isfinite(self.exposure) else 0.0,
                "focus_position_mm": self.focus_position if math.isfinite(self.focus_position) else 0.0}
