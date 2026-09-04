"""Hardware-independent, bounded measurement state machine.

IO operations must check cancellation and use bounded waits. Raw acquisition
never filters by MTF or silently changes focus/exposure during repetitions.
"""
from __future__ import annotations

from dataclasses import asdict
import json
import math
import shutil
import time

import numpy as np

from .measurement_store import RunStore, atomic_json, atomic_text, csv_text, utc_now


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
        return (abs(levels["bright_fraction"]-self.c.exposure_target) <= self.c.exposure_tolerance
                and levels["saturated_fraction"] <= self.c.max_saturated_fraction)

    def auto_exposure(self):
        self.phase("AUTO_EXPOSURE")
        stable = 0
        for iteration in range(self.c.exposure_max_iterations):
            self.check()
            self.exposure = float(self.io.state()["values"]["exposure_time"])
            if not self.c.exposure_min_us <= self.exposure <= self.c.exposure_max_us:
                self.io.set_exposure(min(self.c.exposure_max_us, max(self.c.exposure_min_us, self.exposure)))
                self.flush()
                self.exposure = float(self.io.state()["values"]["exposure_time"])
            levels = self.sample()
            self.store.event("EXPOSURE_SAMPLE", iteration=iteration+1,
                             exposure_us=self.exposure, **levels)
            stable = stable+1 if self.in_band(levels) else 0
            if stable >= 2:
                return levels
            if stable:
                continue
            ratio = np.clip(self.c.exposure_target/max(levels["bright_fraction"], 1e-6), 0.5, 2.0)**0.7
            if levels["saturated_fraction"] > self.c.max_saturated_fraction:
                ratio = min(ratio, 0.8)
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
        if not self.c.axis_min_mm <= lo < hi <= self.c.axis_max_mm:
            raise MeasurementError("FOCUS_LIMIT", "Entire local focus window must fit within verified travel")
        if lo-self.c.park_position_mm <= self.c.position_tolerance_mm:
            raise MeasurementError("APPROACH_DIRECTION", "Park must lie below the entire local focus window")
        rows = []
        # One deterministic increasing scan, approached from the park side.
        self.move(self.c.park_position_mm)
        for position in np.linspace(lo, hi, self.c.focus_samples):
            self.assert_locked(focus_state)
            actual = self.move(float(position))
            scores = [self.io.focus_score(self.fresh()["image"], self.c) for _ in range(self.c.focus_frames)]
            score = float(np.median(scores))
            if not math.isfinite(score):
                raise MeasurementError("FOCUS_INVALID", "Nonfinite focus score")
            row = {"position_mm": actual, "requested_mm": float(position), "score": score, "stage":"scan"}
            rows.append(row)
            self.store.event("FOCUS_SAMPLE", **row)
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
            self.move(self.c.park_position_mm)
            refined = []
            for position in np.linspace(refine_lo,refine_hi,refine_count):
                self.assert_locked(focus_state)
                actual = self.move(float(position))
                score = float(np.median([self.io.focus_score(self.fresh()["image"],self.c)
                                        for _ in range(self.c.focus_frames)]))
                if not math.isfinite(score):
                    raise MeasurementError("FOCUS_INVALID", "Nonfinite refined focus score")
                row = {"position_mm":actual,"requested_mm":float(position),"score":score,"stage":"refine"}
                refined.append(row)
                self.store.event("FOCUS_SAMPLE", **row)
            selected = max(range(len(refined)),key=lambda i:refined[i]["score"])
            if selected in (0,len(refined)-1):
                raise MeasurementError("FOCUS_EDGE_PEAK", "Refined maximum is on search boundary")
            best = len(rows)+selected
            rows.extend(refined)
            peak = rows[best]["score"]
            grid_spacing = (refine_hi-refine_lo)/(refine_count-1)
        self.focus_position = rows[best]["position_mm"]
        self.move(self.c.park_position_mm)
        self.move(self.focus_position)
        confirmation = float(np.median([self.io.focus_score(self.fresh()["image"], self.c)
                                       for _ in range(self.c.focus_frames)]))
        self.assert_locked(focus_state)
        if confirmation < peak*self.c.focus_confirmation_ratio:
            raise MeasurementError("FOCUS_NOT_REPEATABLE", "Returned focus score is below confirmation threshold")
        result = {"method": "local_exhaustive_tenengrad", "curve": rows,
                  "focus_position_mm": self.focus_position, "confirmation_score": confirmation,
                  "grid_spacing_mm": grid_spacing}
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

    def run(self, plan_source="", resume_run_id=""):
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
                baseline = preparation["locked_state"]
                self.assert_locked(baseline)
                self.move(self.c.park_position_mm)
                self.move(self.focus_position)
                if not self.in_band(self.sample()):
                    raise MeasurementError("RESUME_EXPOSURE", "Exposure drift: resume would require a new run")
                score = self.io.focus_score(self.fresh()["image"], self.c)
                if score < preparation["focus"]["confirmation_score"]*self.c.focus_confirmation_ratio:
                    raise MeasurementError("RESUME_FOCUS", "Focus changed: create a new run")
            else:
                center = self.io.position()
                # Validate the complete window BEFORE any AE or movement.
                if not (self.c.axis_min_mm <= center-self.c.fine_focus_half_range_mm
                        and center+self.c.fine_focus_half_range_mm <= self.c.axis_max_mm
                        and self.c.park_position_mm < center-self.c.fine_focus_half_range_mm):
                    raise MeasurementError("FOCUS_LIMIT", "Coarse focus/park/window relationship is unsafe")
                self.flush()
                self.auto_exposure()
                focus = self.fine_focus(center)
                self.phase("EXPOSURE_CHECK")
                levels = self.sample()
                if not self.in_band(levels):
                    old = self.exposure
                    levels = self.auto_exposure()
                    if abs(self.exposure-old)/old >= self.c.exposure_check_refocus_fraction:
                        # Bounded single repeat, not an unbounded AF/AE loop.
                        focus = self.fine_focus(center)
                        levels = self.sample()
                        if not self.in_band(levels):
                            raise MeasurementError("PREPARATION_UNSTABLE", "AE/AF did not settle after one correction")
                baseline = self.io.state()
                preparation = {"focus": focus, "levels": levels, "locked_state": baseline,
                               "focus_position_mm": self.focus_position, "exposure_us": self.exposure,
                               "prepared_utc": utc_now(), "analysis_config": self.io.analysis_config()}
                reference = self.fresh()
                preparation["reference"] = self.store.save_reference(reference, levels["native_max"])
                atomic_text(self.store.path/"focus_curve.csv", csv_text(focus["curve"]))
                atomic_json(preparation_path, preparation)
            completed = self.store.completed()
            for self.index in range(1, self.c.measurement_count+1):
                if self.index in completed:
                    continue
                self.assert_locked(baseline)
                self.phase("MOVE_TO_PARK")
                self.move(self.c.park_position_mm)
                self.phase("MOVE_TO_MEASUREMENT")
                position = self.move(self.focus_position)
                for retry in range(self.c.max_capture_attempts):
                    attempt, path = self.store.attempt(self.index)
                    if attempt > self.c.max_capture_attempts:
                        raise MeasurementError("ATTEMPT_LIMIT", "Total technical attempts exhausted; review and create a new run")
                    self.phase("CAPTURING", attempt=attempt)
                    frames = []
                    try:
                        before = self.assert_locked(baseline)
                        for _ in range(self.c.frames_per_measurement):
                            frames.append(self.fresh())
                        after = self.assert_locked(baseline)
                        end_position = self.io.position()
                        if abs(end_position-self.focus_position) > self.c.position_tolerance_mm:
                            raise MeasurementError("POSITION_DRIFT", "Axis moved during capture")
                        images = [f["image"] for f in frames]
                        if any(image.shape != images[0].shape or image.dtype != images[0].dtype for image in images):
                            raise MeasurementError("FRAME_GEOMETRY", "Frame format changed during capture")
                        x,y,w,h = self.c.roi_x,self.c.roi_y,self.c.roi_width,self.c.roi_height
                        margin = self.c.context_margin_px
                        ox,oy = max(0,x-margin),max(0,y-margin)
                        ex,ey = min(images[0].shape[1],x+w+margin),min(images[0].shape[0],y+h+margin)
                        stack = np.stack([im[oy:ey,ox:ex] for im in images])
                        levels = self.io.levels(images, self.c)
                        # Quality is recorded, never optimized by recapturing low-MTF frames.
                        flags = [] if self.in_band(levels) else ["INTENSITY_OUTSIDE_TARGET"]
                        rows = [{"frame_index": i+1, **{k:v for k,v in f.items() if k != "image"}}
                                for i,f in enumerate(frames)]
                        for row, image in zip(rows, images):
                            row.update(self.io.levels([image], self.c))
                        metadata = {"measurement_index": self.index, "attempt_index": attempt,
                                    "condition": asdict(self.c), "state_before": before, "state_after": after,
                                    "position_before_mm": position, "position_after_mm": end_position,
                                    "roi": [x,y,w,h], "stack_origin": [ox,oy],
                                    "edge_bbox_in_stack": [x-ox,y-oy,w,h], "levels": levels,
                                    "quality_flags": flags, "analysis_config": preparation["analysis_config"],
                                    "timestamp_utc": utc_now()}
                        if shutil.disk_usage(path).free < stack.nbytes+self.c.min_free_gb*1e9:
                            raise MeasurementError("DISK_SPACE", "Insufficient space for next stack")
                        self.phase("WRITING_RESULTS")
                        manifest = self.store.commit(path, stack, rows, metadata)
                        self.completed_count = self.store.progress("running")
                        self.store.event("CAPTURE_COMMITTED", manifest=str(manifest.relative_to(self.store.path)))
                        if flags:
                            raise MeasurementError("INTENSITY_DRIFT", "Raw data preserved; intensity drift requires review/new run")
                        break
                    except FrameTimeout as exc:
                        self.store.save_partial(path, frames)
                        atomic_json(path / "failure.json", {"code": exc.code, "message": str(exc)})
                        self.store.event("CAPTURE_RETRY", measurement_index=self.index, attempt=attempt)
                        if retry+1 >= self.c.max_capture_attempts:
                            raise
                        self.flush()
                    except BaseException:
                        if path.exists():
                            self.store.save_partial(path, frames)
                        raise
            self.phase("COMPLETE")
            self.store.progress("complete")
            return self.result(True, "", "Acquisition complete; MTF analysis pending")
        except BaseException as exc:
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
