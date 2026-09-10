"""Producer/consumer and export behavior for online measurement analysis."""

from types import SimpleNamespace
import csv
import json
import threading
import time

import numpy as np
import pytest
import yaml

from camera_nodes.measurement_online import MeasurementJob, OnlineAnalysisWorker


def _result():
    frequency = np.linspace(0, 100, 16)
    curve = np.linspace(1, 0, 16)
    signal = np.linspace(0, 1, 16)
    return SimpleNamespace(
        esf=signal, lsf=np.gradient(signal), lsf_windowed=np.gradient(signal),
        frequencies=frequency, mtf_raw=curve, mtf_values=curve, mtf_ideal=curve,
        edge_line=(10.0, 10.0, 80.0, 18.0),
    )


def _job(total=10, invalid_index=None):
    frames = []
    for index in range(total):
        valid = index != invalid_index
        frames.append({
            "valid": valid, "mtf50": 50.0 + index, "edge_angle": 5.0,
            "warning": "", "error": "" if valid else "no edge",
        })
    intensity = {
        "white_level": 2800.0, "white_level_norm": 0.684,
        "black_level": 100.0, "black_level_norm": 0.024,
        "p95": 2801.0, "p95_norm": 0.684, "p99_9": 2802.0,
        "p99_9_norm": 0.684, "saturation_fraction": 0.0,
        "intensity_method": "segmented_plateau_median", "clipping_detected": False,
    }
    metadata = {
        "timestamp_utc": "2026-01-01T00:00:00+00:00", "run_id": "run",
        "condition_id": "condition", "measurement_index": 1,
        "requested_position_mm": 294.12, "position_before_mm": 294.12,
        "position_after_mm": 294.12, "focus_position_mm": 294.12,
        "exposure_us": 1000.0, "gain": 0.0,
        "auto_exposure": {"success": True, "iterations": 4},
        "roi": [10, 10, 80, 80], "overview_roi": [10, 10, 80, 80],
        "measurement_count": 1, "frames_per_measurement": total,
        "inter_measurement_motion": "park_return", "exposure_target": 0.70,
        "exposure_tolerance": 0.02, "mtf_algorithm": "dense_gray",
        "raw_manifest": "measurements/m001/attempt_01/capture_manifest.json",
        "quality_flags": [], "capture_duration_s": 0.1,
        "mtf_compute_duration_s": 0.05, "raw_commit_duration_s": 0.02,
    }
    image = np.zeros((100, 100), dtype=np.uint16)
    return MeasurementJob(metadata, frames, intensity, image, image[10:90, 10:90],
                          _result(), "mono16")


def test_queue_is_size_one_and_backpressure_blocks_third_job(tmp_path):
    worker = OnlineAnalysisWorker(tmp_path)
    assert worker.queue.maxsize == 1
    gate = threading.Event()
    entered = threading.Event()

    def slow(_job):
        entered.set()
        gate.wait(timeout=2)

    worker._process = slow
    worker.submit(_job())
    assert entered.wait(timeout=1)
    worker.submit(_job())
    submitter = threading.Thread(target=lambda: worker.submit(_job()))
    submitter.start()
    time.sleep(0.05)
    assert submitter.is_alive()
    gate.set()
    submitter.join(timeout=2)
    worker.close()
    assert not worker.thread.is_alive()


def test_invalid_single_frame_exports_statistics_but_invalidates_point(tmp_path):
    worker = OnlineAnalysisWorker(tmp_path)
    worker.submit(_job(invalid_index=4))
    worker.close()
    with (tmp_path/"summary.csv").open(newline="") as handle:
        row = next(csv.DictReader(handle))
    assert row["valid"] == "0"
    assert row["status"] == "invalid_mtf"
    assert row["frames_valid"] == "9" and row["frames_total"] == "10"
    assert row["mtf50_lp_mm_mean"] != ""
    assert {path.name for path in tmp_path.glob("point_*.png")} == {
        "point_001_z_294.120mm_overview.png",
        "point_001_z_294.120mm_edges.png",
    }


def test_diagnostic_failure_is_nonfatal_and_recorded(tmp_path, monkeypatch):
    import camera_nodes.measurement_online as online

    monkeypatch.setattr(online, "_write_overview", lambda *_args: (_ for _ in ()).throw(OSError("png")))
    worker = OnlineAnalysisWorker(tmp_path)
    worker.submit(_job())
    worker.close()
    with (tmp_path/"summary.csv").open(newline="") as handle:
        row = next(csv.DictReader(handle))
    assert "png" in row["diagnostic_error"]
    assert row["overview_image"] == ""
    assert row["edges_image"].endswith("_edges.png")


def test_summary_write_failure_is_fatal(tmp_path, monkeypatch):
    import camera_nodes.measurement_online as online

    original = online.atomic_text

    def fail_summary(path, text):
        if path.name == "summary.csv":
            raise OSError("csv full")
        return original(path, text)

    monkeypatch.setattr(online, "atomic_text", fail_summary)
    worker = OnlineAnalysisWorker(tmp_path)
    with pytest.raises(RuntimeError, match="worker failed"):
        worker.close()


def test_series_plot_failure_prevents_successful_worker_join(tmp_path, monkeypatch):
    worker = OnlineAnalysisWorker(tmp_path)
    worker.submit(_job())
    monkeypatch.setattr(worker, "_finalize", lambda: (_ for _ in ()).throw(OSError("series png")))
    with pytest.raises(RuntimeError, match="worker failed"):
        worker.close()


def test_online_compare_reports_only_eligible_relative_transmission(tmp_path):
    from camera_nodes.measurement_analyze import report_online_runs

    runs = []
    context = {
        "camera_profile": "mono", "camera_serial": "123", "objective_id": "4x",
        "objective_family": "family", "magnification_x": 4.0,
        "illumination_voltage_v": 20.0, "illumination_color": "green",
        "illumination_reference_voltage_v": 20.0,
    }
    for index, exposure in enumerate((1000.0, 500.0), start=1):
        run = tmp_path/f"run{index}"
        run.mkdir()
        (run/"resolved_condition.yaml").write_text(yaml.safe_dump(context))
        job = _job()
        job.metadata["run_id"] = f"run{index}"
        job.metadata["exposure_us"] = exposure
        worker = OnlineAnalysisWorker(run)
        worker.submit(job)
        worker.close()
        runs.append(run)

    output = report_online_runs(runs, tmp_path/"eligible")
    report = json.loads((output/"run_report.json").read_text())
    assert report["runs"][1]["relative_transmission"] == pytest.approx(2.0)
    assert (output/"measurement_report.png").is_file()

    changed = dict(context, objective_id="different")
    (runs[1]/"resolved_condition.yaml").write_text(yaml.safe_dump(changed))
    output = report_online_runs(runs, tmp_path/"rejected")
    report = json.loads((output/"run_report.json").read_text())
    assert report["runs"][1]["relative_transmission"] is None
    assert report["runs"][1]["transmission_rejection_reason"] == "objective differs"
