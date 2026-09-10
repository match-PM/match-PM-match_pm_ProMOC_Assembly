"""Bounded online result writer for the StartMeasurement action."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
import io
import json
from pathlib import Path
from queue import Full, Queue
import re
import threading
import time
from typing import Any

import cv2
import numpy as np

from .algorithms.mtf.debug_export import _overlay_edge_line, write_mtf_plot
from .measurement_store import atomic_json, atomic_text
from .preview import raw_array_to_bgr8_preview


SUMMARY_FIELDNAMES = [
    "timestamp_utc", "run_id", "condition_id", "measurement_index", "status", "valid",
    "quality_flags", "requested_position_mm", "actual_position_before_mm",
    "actual_position_after_mm", "focus_position_mm", "mtf50_lp_mm_mean",
    "mtf50_lp_mm_std", "mtf50_lp_mm_min", "mtf50_lp_mm_max", "frames_valid",
    "frames_total", "edge_angle_deg_mean", "mtf_algorithm", "exposure_us", "gain",
    "auto_exposure_enabled", "auto_exposure_success", "ae_iterations", "white_level",
    "white_level_norm", "black_level", "black_level_norm", "p95", "p95_norm", "p99_9",
    "p99_9_norm", "saturation_fraction", "intensity_method", "clipping_detected",
    "roi_x", "roi_y", "roi_width", "roi_height", "measurement_count",
    "frames_per_measurement", "inter_measurement_motion", "inter_measurement_travel_mm", "exposure_target",
    "exposure_tolerance", "raw_manifest", "overview_image", "edges_image",
    "diagnostic_error", "capture_duration_s", "mtf_compute_duration_s",
    "raw_commit_duration_s", "queue_wait_duration_s", "worker_duration_s",
    "edges_valid", "edges_total", "edges_expected_per_frame", "mtf_roi_mode",
    "warning_messages", "error_messages",
]


@dataclass
class MeasurementJob:
    """Small worker payload; raw 10-frame stacks are already committed to disk."""

    metadata: dict[str, Any]
    frame_results: list[dict[str, Any]]
    intensity: dict[str, Any]
    representative_image: np.ndarray | None
    representative_roi: np.ndarray | None
    representative_result: Any | None
    image_encoding: str
    representative_edges: list[dict[str, Any]] = field(default_factory=list)


class _NullLogger:
    def warning(self, _message: str) -> None:
        pass

    def error(self, _message: str) -> None:
        pass


def _safe_stem(index: int, position_mm: float) -> str:
    text = f"point_{int(index):03d}_z_{float(position_mm):.3f}mm"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._-")


def _csv_text(rows: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=SUMMARY_FIELDNAMES)
    writer.writeheader()
    for row in rows:
        writer.writerow({name: row.get(name, "") for name in SUMMARY_FIELDNAMES})
    return buffer.getvalue()


def _preview(image: np.ndarray, encoding: str) -> np.ndarray:
    return raw_array_to_bgr8_preview(image, encoding)


def _write_overview(path: Path, job: MeasurementJob) -> None:
    image = job.representative_image
    if image is None:
        image = job.representative_roi
    if image is None:
        raise ValueError("representative image unavailable")
    overview = _preview(image, job.image_encoding)
    origin_x, origin_y = [int(value) for value in job.metadata.get("overview_origin", (0, 0))]
    x, y, width, height = [int(value) for value in job.metadata["overview_roi"]]
    x, y = x - origin_x, y - origin_y
    x = max(0, min(x, overview.shape[1] - 1))
    y = max(0, min(y, overview.shape[0] - 1))
    width = max(1, min(width, overview.shape[1] - x))
    height = max(1, min(height, overview.shape[0] - y))
    cv2.rectangle(overview, (x, y), (x + width, y + height), (255, 180, 0), 2, cv2.LINE_AA)
    for edge in job.representative_edges:
        ex, ey, ew, eh = [int(value) for value in edge.get("bbox", (0, 0, 0, 0))]
        ex, ey = ex - origin_x, ey - origin_y
        result = edge.get("result")
        valid = bool(getattr(result, "valid", False))
        color = (0, 220, 0) if valid else (0, 0, 255)
        cv2.rectangle(overview, (ex, ey), (ex + ew, ey + eh), color, 2, cv2.LINE_AA)
        cv2.putText(overview, str(edge.get("edge_name", "edge")), (ex + 2, max(16, ey - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
        edge_line = getattr(result, "edge_line", None) if result is not None else None
        if edge_line is not None:
            roi_view = overview[max(0, ey):max(0, ey) + eh, max(0, ex):max(0, ex) + ew]
            if roi_view.size:
                _overlay_edge_line(roi_view, edge_line)
    if not job.representative_edges:
        result = job.representative_result
        edge_line = getattr(result, "edge_line", None) if result is not None else None
        if edge_line is not None:
            roi_view = overview[y:y + height, x:x + width]
            if roi_view.size:
                _overlay_edge_line(roi_view, edge_line)
    label = f"point {job.metadata['measurement_index']:03d}  z={job.metadata['position_before_mm']:.3f} mm"
    cv2.putText(overview, label, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                (255, 255, 255), 3, cv2.LINE_AA)
    cv2.putText(overview, label, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                (0, 180, 0), 1, cv2.LINE_AA)
    if not cv2.imwrite(str(path), overview):
        raise OSError(f"failed to write {path}")


def _write_edges(path: Path, job: MeasurementJob) -> None:
    if job.representative_edges:
        import matplotlib

        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt

        edges = job.representative_edges
        figure, axes = plt.subplots(
            len(edges), 3, figsize=(13, max(3.0, 2.7 * len(edges))),
            constrained_layout=True, squeeze=False,
        )
        try:
            for row_index, edge in enumerate(edges):
                result = edge["result"]
                label = str(edge.get("edge_name", f"edge {row_index + 1}"))
                axes[row_index, 0].plot(np.asarray(result.esf))
                axes[row_index, 0].set_title(f"{label}: ESF")
                axes[row_index, 1].plot(np.asarray(result.lsf), label="LSF", alpha=0.65)
                axes[row_index, 1].plot(np.asarray(result.lsf_windowed), label="windowed")
                axes[row_index, 1].set_title(f"{label}: LSF")
                axes[row_index, 1].legend(fontsize=7)
                axes[row_index, 2].plot(np.asarray(result.frequencies), np.asarray(result.mtf_raw),
                                        label="raw", alpha=0.65)
                axes[row_index, 2].plot(np.asarray(result.frequencies), np.asarray(result.mtf_values),
                                        label="used")
                axes[row_index, 2].set_title(
                    f"{label}: MTF50={float(result.mtf50):.2f} lp/mm"
                    if result.valid else f"{label}: invalid"
                )
                axes[row_index, 2].legend(fontsize=7)
                for axis in axes[row_index]:
                    axis.grid(True, alpha=0.25)
            figure.suptitle(
                f"Point {job.metadata['measurement_index']:03d} – four cube edges"
            )
            figure.savefig(path, dpi=150)
        finally:
            plt.close(figure)
        return
    result = job.representative_result
    if result is None:
        raise ValueError("representative MTF result unavailable")
    write_mtf_plot(
        path,
        esf=np.asarray(result.esf),
        lsf=np.asarray(result.lsf),
        lsf_windowed=np.asarray(result.lsf_windowed),
        frequencies=np.asarray(result.frequencies),
        mtf_raw=np.asarray(result.mtf_raw),
        mtf_used=np.asarray(result.mtf_values),
        mtf_ideal=np.asarray(result.mtf_ideal),
        title=f"Point {job.metadata['measurement_index']:03d} – ESF / LSF / MTF",
    )


class OnlineAnalysisWorker:
    """Single-consumer analysis/export worker with bounded backpressure."""

    SENTINEL = object()

    def __init__(self, run_dir: Path, logger=None, *, maxsize: int = 1):
        self.run_dir = Path(run_dir)
        self.logger = logger or _NullLogger()
        self.queue: Queue = Queue(maxsize=maxsize)
        self.rows: list[dict[str, Any]] = []
        self.error: BaseException | None = None
        self._closed = False
        self.analysis_dir = self.run_dir / "analysis"
        self.points_dir = self.analysis_dir / "points"
        self.points_dir.mkdir(parents=True, exist_ok=True)
        for path in sorted(self.points_dir.glob("point_*.json")):
            try:
                self.rows.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        self.rows.sort(key=lambda row: int(row["measurement_index"]))
        self.thread = threading.Thread(
            target=self._run,
            name="mtf-analysis-worker",
            daemon=False,
        )
        self.thread.start()

    @property
    def analyzed_indices(self) -> set[int]:
        return {int(row["measurement_index"]) for row in self.rows}

    def submit(self, job: MeasurementJob) -> float:
        """Submit with bounded waits so worker failures cannot deadlock acquisition."""
        if self._closed:
            raise RuntimeError("online analysis worker is closed")
        started = time.perf_counter()
        while True:
            if self.error is not None:
                raise RuntimeError("online analysis worker failed") from self.error
            try:
                job.metadata["queue_wait_duration_s"] = time.perf_counter() - started
                self.queue.put(job, timeout=0.1)
                return time.perf_counter() - started
            except Full:
                continue

    def close(self) -> None:
        """Drain every job, finalize plots and surface worker failures."""
        if self._closed:
            if self.error is not None:
                raise RuntimeError("online analysis worker failed") from self.error
            return
        while True:
            try:
                self.queue.put(self.SENTINEL, timeout=0.1)
                break
            except Full:
                continue
        self.queue.join()
        self.thread.join()
        self._closed = True
        if self.error is not None:
            raise RuntimeError("online analysis worker failed") from self.error

    def _run(self) -> None:
        try:
            # Rebuild from immutable per-point rows on resume, including the
            # case where a previous atomic summary replacement failed.
            atomic_text(self.run_dir / "summary.csv", _csv_text(self.rows))
        except BaseException as exc:
            self.error = exc
            self.logger.error(f"Online summary initialization failed: {exc}")
        while True:
            item = self.queue.get()
            stop = item is self.SENTINEL
            try:
                if stop:
                    if self.error is None:
                        self._finalize()
                elif self.error is None:
                    self._process(item)
            except BaseException as exc:
                if self.error is None:
                    self.error = exc
                    self.logger.error(f"Online analysis worker failed: {exc}")
            finally:
                self.queue.task_done()
            if stop:
                return

    def _process(self, job: MeasurementJob) -> None:
        started = time.perf_counter()
        valid = [row for row in job.frame_results if bool(row.get("valid"))]
        values = np.asarray([float(row["mtf50"]) for row in valid], dtype=np.float64)
        angles = np.asarray([float(row["edge_angle"]) for row in valid], dtype=np.float64)
        total = len(job.frame_results)
        point_valid = len(valid) == total and total > 0
        metadata = job.metadata
        expected_edges = 4 if metadata.get("mtf_roi_mode") == "roi_search_square4" else 1
        edges_valid = sum(
            int(row.get("edges_valid", int(bool(row.get("valid")))))
            for row in job.frame_results
        )
        edges_total = sum(int(row.get("edges_total", 1)) for row in job.frame_results)
        position = float(metadata["position_before_mm"])
        stem = _safe_stem(int(metadata["measurement_index"]), position)
        overview_path = self.run_dir / f"{stem}_overview.png"
        edges_path = self.run_dir / f"{stem}_edges.png"
        diagnostic_errors = []
        for writer, path in ((_write_overview, overview_path), (_write_edges, edges_path)):
            try:
                writer(path, job)
            except Exception as exc:
                diagnostic_errors.append(f"{path.name}: {exc}")
                self.logger.warning(f"Diagnostic export failed for {path.name}: {exc}")

        intensity = job.intensity
        warnings = [str(row.get("warning", "")) for row in job.frame_results if row.get("warning")]
        errors = [str(row.get("error", "")) for row in job.frame_results if row.get("error")]
        row = {
            "timestamp_utc": metadata["timestamp_utc"],
            "run_id": metadata["run_id"],
            "condition_id": metadata["condition_id"],
            "measurement_index": int(metadata["measurement_index"]),
            "status": "valid" if point_valid else "invalid_mtf",
            "valid": int(point_valid),
            "quality_flags": ";".join(metadata.get("quality_flags", [])),
            "requested_position_mm": float(metadata["requested_position_mm"]),
            "actual_position_before_mm": position,
            "actual_position_after_mm": float(metadata["position_after_mm"]),
            "focus_position_mm": float(metadata["focus_position_mm"]),
            "mtf50_lp_mm_mean": float(np.mean(values)) if values.size else "",
            "mtf50_lp_mm_std": float(np.std(values, ddof=1)) if values.size > 1 else "",
            "mtf50_lp_mm_min": float(np.min(values)) if values.size else "",
            "mtf50_lp_mm_max": float(np.max(values)) if values.size else "",
            "frames_valid": len(valid),
            "frames_total": total,
            "edge_angle_deg_mean": float(np.mean(angles)) if angles.size else "",
            "mtf_algorithm": metadata["mtf_algorithm"],
            "exposure_us": float(metadata["exposure_us"]),
            "gain": float(metadata["gain"]),
            "auto_exposure_enabled": 1,
            "auto_exposure_success": int(bool(metadata["auto_exposure"]["success"])),
            "ae_iterations": int(metadata["auto_exposure"]["iterations"]),
            **{name: intensity[name] for name in (
                "white_level", "white_level_norm", "black_level", "black_level_norm",
                "p95", "p95_norm", "p99_9", "p99_9_norm", "saturation_fraction",
                "intensity_method", "clipping_detected",
            )},
            "roi_x": int(metadata["roi"][0]), "roi_y": int(metadata["roi"][1]),
            "roi_width": int(metadata["roi"][2]), "roi_height": int(metadata["roi"][3]),
            "measurement_count": int(metadata["measurement_count"]),
            "frames_per_measurement": int(metadata["frames_per_measurement"]),
            "inter_measurement_motion": metadata["inter_measurement_motion"],
            "inter_measurement_travel_mm": float(metadata.get("inter_measurement_travel_mm", 10.0)),
            "exposure_target": float(metadata["exposure_target"]),
            "exposure_tolerance": float(metadata["exposure_tolerance"]),
            "raw_manifest": metadata["raw_manifest"],
            "overview_image": overview_path.name if overview_path.exists() else "",
            "edges_image": edges_path.name if edges_path.exists() else "",
            "diagnostic_error": "; ".join(diagnostic_errors),
            "capture_duration_s": float(metadata["capture_duration_s"]),
            "mtf_compute_duration_s": float(metadata["mtf_compute_duration_s"]),
            "raw_commit_duration_s": float(metadata["raw_commit_duration_s"]),
            "queue_wait_duration_s": float(metadata.get("queue_wait_duration_s", 0.0)),
            "worker_duration_s": time.perf_counter() - started,
            "edges_valid": edges_valid,
            "edges_total": edges_total,
            "edges_expected_per_frame": expected_edges,
            "mtf_roi_mode": metadata.get("mtf_roi_mode", "legacy_direct"),
            "warning_messages": "; ".join(warnings),
            "error_messages": "; ".join(errors),
        }
        point_path = self.points_dir / f"point_{int(metadata['measurement_index']):03d}.json"
        atomic_json(point_path, row)
        self.rows = [existing for existing in self.rows
                     if int(existing["measurement_index"]) != int(row["measurement_index"])]
        self.rows.append(row)
        self.rows.sort(key=lambda value: int(value["measurement_index"]))
        atomic_text(self.run_dir / "summary.csv", _csv_text(self.rows))

    def _finalize(self) -> None:
        if not self.rows:
            atomic_text(self.run_dir / "summary.csv", _csv_text([]))
        plotted = [row for row in self.rows if row.get("mtf50_lp_mm_mean", "") != ""]
        import matplotlib

        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt

        figure = None
        try:
            x = np.asarray([int(row["measurement_index"]) for row in plotted])
            y = np.asarray([float(row["mtf50_lp_mm_mean"]) for row in plotted])
            error = np.asarray([
                float(row["mtf50_lp_mm_std"]) if row["mtf50_lp_mm_std"] != "" else 0.0
                for row in plotted
            ])
            figure, axis = plt.subplots(figsize=(9, 5), constrained_layout=True)
            if plotted:
                axis.errorbar(x, y, yerr=error, marker="o", capsize=3)
            else:
                axis.text(0.5, 0.5, "No valid MTF50 values", ha="center", va="center",
                          transform=axis.transAxes)
            axis.set_xlabel("Measurement index")
            axis.set_ylabel("MTF50 (lp/mm, image space)")
            axis.set_title("MTF50 repeatability")
            axis.grid(True, alpha=0.3)
            figure.savefig(self.analysis_dir / "mtf50_vs_measurement.png", dpi=150)
        finally:
            if figure is not None:
                plt.close(figure)
