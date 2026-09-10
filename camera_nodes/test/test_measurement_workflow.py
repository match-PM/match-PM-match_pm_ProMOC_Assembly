"""Measurement safety/provenance tests without ROS or real axis commands."""
from dataclasses import asdict, replace
import csv
import json
from pathlib import Path
import re
import threading

import numpy as np
import pytest
import yaml

from camera_nodes.measurement_plan import Condition, load_plan
from camera_nodes.measurement_engine import MeasurementEngine, MeasurementError, FrameTimeout, Cancelled
from camera_nodes.measurement_simulation import SimulatedIO
from camera_nodes.measurement_store import RunStore, verify_capture
from linear_axis_nodes.measurement_lease import MeasurementLease


@pytest.fixture
def condition(tmp_path):
    return Condition(campaign_id="test", condition_id="c1", experiment_id="V1", plan_row_number=1,
        setup_id="assembly1", operator_name="test", camera_profile="mono", camera_serial="123",
        objective_id="myutron-4x", objective_family="FTVxxC-150", magnification_x=4.0,
        component_id="none", target_position="center", illumination_voltage_v=20.0,
        output_root=str(tmp_path), roi_x=16,roi_y=16,roi_width=96,roi_height=96,
        measurement_count=2,frames_per_measurement=2,axis_min_mm=0,axis_max_mm=20,
        park_position_mm=2,focus_samples=11,focus_frames=1, min_free_gb=0.001)


def test_typed_plan_merge_and_duplicate_keys(condition, tmp_path):
    path = tmp_path/"plan.yaml"
    data = asdict(condition)
    data.pop("campaign_id")
    path.write_text(yaml.safe_dump({"schema_version":1,"campaign_id":"test", "defaults":data,
                                   "conditions":[{"condition_id":"c1","objective_id":"budget-4gx"}]}))
    loaded,_ = load_plan(path,"c1")
    assert loaded.objective_id == "budget-4gx" and loaded.magnification_x == 4
    path.write_text("schema_version: 1\nschema_version: 2\n")
    with pytest.raises(ValueError, match="Duplicate"):
        load_plan(path)


@pytest.mark.parametrize("overrides", [dict(park_position_mm=-1),dict(axis_max_mm=301),
    dict(roi_width=0),dict(exposure_max_us=float("nan")),dict(measurement_count=True),
    dict(condition_id="../bad"),dict(focus_samples=10),dict(camera_serial="REPLACE"),
    dict(fine_focus_half_range_mm=10)])
def test_invalid_conditions(condition, overrides):
    with pytest.raises(ValueError):
        replace(condition,**overrides).validate()


def test_complete_and_immutable_analysis(condition):
    io = SimulatedIO(condition)
    result = MeasurementEngine(condition,io).run("test source")
    assert result["success"] and result["captured_frames"] == 4
    from camera_nodes.measurement_analyze import analyze_run
    path = Path(result["output_directory"])
    manifests = list(path.glob("measurements/m*/attempt_*/capture_manifest.json"))
    assert len(manifests) == 2
    original = [p.read_bytes() for p in manifests]
    for manifest in manifests:
        assert verify_capture(manifest,2)["capture_status"] == "complete"
        capture = json.loads(manifest.read_text())
        assert capture["mtf_roi_mode"] == "roi_search_square4"
        assert all(row["edges_total"] == 4 for row in capture["frame_analysis"])
        assert all(row["edges_valid"] == 4 for row in capture["frame_analysis"])
    first = analyze_run(path)
    second = analyze_run(path)
    assert first != second
    assert (first/"frame_results.csv").is_file()
    assert [p.read_bytes() for p in manifests] == original
    with (path/"summary.csv").open(newline="") as handle:
        online_rows = list(csv.DictReader(handle))
    assert len(online_rows) == condition.measurement_count
    assert all(int(row["frames_total"]) == condition.frames_per_measurement for row in online_rows)
    assert all(int(row["frames_valid"]) == condition.frames_per_measurement for row in online_rows)
    assert len(list(path.glob("point_*_overview.png"))) == condition.measurement_count
    assert len(list(path.glob("point_*_edges.png"))) == condition.measurement_count
    assert (path/"analysis"/"mtf50_vs_measurement.png").is_file()
    assert not [thread for thread in threading.enumerate()
                if thread.name == "mtf-analysis-worker"]
    prep = json.loads((path/"preparation.json").read_text())
    assert len(prep["focus"]["curve"]) >= condition.focus_samples
    assert prep["levels"]["bright_fraction"] == pytest.approx(.70,abs=.02)
    # The first capture stays at the prepared focus. Only the gap between m001
    # and m002 gets the prescribed 10 mm approach-reset cycle; no AF is rerun.
    assert io.moves[-4:] == [
        io.best - condition.inter_measurement_travel_mm,
        prep["focus_position_mm"],
        prep["focus_position_mm"] - condition.inter_measurement_travel_mm,
        prep["focus_position_mm"],
    ]


def test_cancel_and_resume_without_af_or_ae(condition):
    io = SimulatedIO(condition)
    state = {"cancel":False}
    def feedback(phase,index,completed):
        if completed == 1:
            state["cancel"] = True
    engine = MeasurementEngine(condition,io,feedback,cancel=lambda:state["cancel"])
    with pytest.raises(Cancelled):
        engine.run("test")
    assert engine.completed_count == 1
    assert not [thread for thread in threading.enumerate()
                if thread.name == "mtf-analysis-worker"]
    io.set_exposure = lambda value: pytest.fail("Resume must not change exposure")
    result = MeasurementEngine(condition,io).run("test",engine.store.run_id)
    assert result["captured_frames"] == 4


def test_resume_rebuilds_missing_online_result_from_raw_stack(condition):
    io = SimulatedIO(condition)
    engine = MeasurementEngine(condition, io)
    engine.run("test")
    run = engine.store.path
    (run/"analysis"/"points"/"point_001.json").unlink()
    (run/"summary.csv").unlink()
    for image in run.glob("point_001_*.png"):
        image.unlink()

    resumed = MeasurementEngine(condition, io).run("test", engine.store.run_id)
    assert resumed["success"]
    with (run/"summary.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == condition.measurement_count
    assert len(list(run.glob("point_001_*.png"))) == 2


def test_resume_after_camera_epoch_change_refused(condition):
    io = SimulatedIO(condition)
    engine = MeasurementEngine(condition,io)
    engine.run("test")
    previous = io.state
    def changed():
        value = previous()
        value["identity"]["camera_node_epoch"] = "new"
        return value
    io.state = changed
    with pytest.raises(MeasurementError,match="epoch"):
        MeasurementEngine(condition,io).run("test",engine.store.run_id)


def test_timestamp_duplicate_refused(condition):
    io = SimulatedIO(condition)
    engine = MeasurementEngine(condition,io)
    engine.fresh()
    io.frame = lambda last,timeout: {"source_timestamp_ns":last,"image":np.zeros((4,4))}
    with pytest.raises(MeasurementError,match="increase"):
        engine.fresh()


def test_partial_stack_never_committed(condition):
    io = SimulatedIO(condition)
    original = io.frame
    state = {"capture":False}
    def feedback(phase,index,done):
        if phase == "CAPTURING":
            state["capture"] = True
    def frame(last,timeout):
        if state["capture"]:
            raise FrameTimeout()
        return original(last,timeout)
    io.frame = frame
    engine = MeasurementEngine(condition,io,feedback)
    with pytest.raises(FrameTimeout):
        engine.run("test")
    assert engine.completed_count == 0
    assert not list(engine.store.path.glob("measurements/m*/attempt_*/capture_manifest.json"))


def test_hash_corruption_and_configuration_change(condition):
    engine = MeasurementEngine(condition,SimulatedIO(condition))
    engine.run("test")
    with pytest.raises(ValueError, match="differs"):
        RunStore(replace(condition,objective_id="budget-4gx"),"test",engine.store.run_id)
    manifest = next(engine.store.path.glob("measurements/m*/attempt_*/capture_manifest.json"))
    raw = manifest.parent/"edge_raw_stack.npy"
    with raw.open("ab") as handle:
        handle.write(b"corruption")
    with pytest.raises(ValueError,match="checksum"):
        verify_capture(manifest)


def test_no_focus_outside_safe_window(condition):
    io = SimulatedIO(condition)
    io.pos = condition.axis_max_mm
    with pytest.raises(MeasurementError, match="unsafe"):
        MeasurementEngine(condition,io).run("test")
    assert io.moves == []


def test_hold_focus_avoids_inter_measurement_moves(condition):
    condition = replace(condition, inter_measurement_motion="hold_focus")
    io = SimulatedIO(condition)
    result = MeasurementEngine(condition, io).run("test")
    assert result["success"]
    preparation = json.loads((Path(result["output_directory"])/"preparation.json").read_text())
    assert io.moves[-2:] == [
        io.best - condition.inter_measurement_travel_mm,
        preparation["focus_position_mm"],
    ]


def test_empty_motion_mode_preserves_park_return(condition):
    assert replace(condition, inter_measurement_motion="").validate().inter_measurement_motion == "park_return"


def test_missing_cube_edges_invalidates_point_but_does_not_abort_series(condition):
    io = SimulatedIO(condition)
    original = io.analyze_mtf_roi_frame
    calls = {"count": 0}

    def lose_one_frame(image, current_condition, config, edge_geometry=None):
        calls["count"] += 1
        if calls["count"] == 1:
            return {"mode": "roi_search_square4", "edges": []}
        return original(image, current_condition, config, edge_geometry)

    io.analyze_mtf_roi_frame = lose_one_frame
    result = MeasurementEngine(condition, io).run("test")

    assert result["success"]
    assert result["completed_measurements"] == 2
    with (Path(result["output_directory"]) / "summary.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["valid"] == "0"
    assert rows[0]["quality_flags"] == "MTF_ROI_EDGE_COUNT_NOT_FOUR"
    assert rows[1]["valid"] == "1"


def test_lease_exclusion_watchdog_and_epoch():
    now = [0.0]
    lease = MeasurementLease(clock=lambda:now[0])
    epoch = lease.epoch
    assert not lease.update("acquire","a",False)
    assert lease.update("acquire","a",True)
    assert not lease.permits("") and not lease.update("acquire","b",True)
    assert lease.permits("a")
    now[0] = 31
    assert lease.expired() and not lease.permits("a")
    assert not lease.update("renew","a",True)
    assert not lease.update("release","b",True)
    assert lease.update("release","a",True)
    lease.invalidate_reference()
    assert lease.epoch != epoch


def test_write_failure_never_advances_progress(condition, monkeypatch):
    def fail(*args):
        raise OSError("simulated disk full")
    monkeypatch.setattr(RunStore,"commit",fail)
    engine = MeasurementEngine(condition,SimulatedIO(condition))
    with pytest.raises(OSError,match="disk full"):
        engine.run("test")
    progress = json.loads((engine.store.path/"progress.json").read_text())
    assert progress["completed_measurements"] == []


def test_changed_exposure_in_repetition_aborts(condition):
    io = SimulatedIO(condition)
    def feedback(phase,index,done):
        if phase == "CAPTURING":
            io.exposure *= 1.2
    engine = MeasurementEngine(condition,io,feedback)
    with pytest.raises(MeasurementError,match="exposure_time"):
        engine.run("test")
    assert engine.completed_count == 0


def test_single_frame_timeout_keeps_partial_data(condition):
    io = SimulatedIO(condition)
    original = io.frame
    state = {"capture":False,"frames":0}
    def feedback(phase,index,done):
        if phase == "CAPTURING":
            state["capture"] = True
    def frame(last,timeout):
        if state["capture"]:
            state["frames"] += 1
            if state["frames"] == 2:
                raise FrameTimeout()
        return original(last,timeout)
    io.frame = frame
    engine = MeasurementEngine(condition,io,feedback)
    result = engine.run("test")
    assert result["captured_frames"] == 4
    partial = list(engine.store.path.glob("measurements/m001/*.pending/partial_raw_stack.npy"))
    assert len(partial) == 1 and np.load(partial[0]).shape[0] == 1
    manifest = next(engine.store.path.glob("measurements/m001/attempt_02/capture_manifest.json"))
    assert verify_capture(manifest)["attempt_index"] == 2


def test_campaign_templates_match_green_v5():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]/"promoc_bringup/config/measurement_plans"
    screening,_ = load_plan(root/"screening_green_v5.yaml")
    components,_ = load_plan(root/"components_green_v5.yaml")
    assert len(screening["conditions"]) == 10
    assert len(components["conditions"]) == 136
    raw_rows = screening["conditions"]+components["conditions"]
    condition_ids = [row["condition_id"] for row in raw_rows]
    assert [int(value[1:4]) for value in condition_ids] == list(range(1, 147))
    assert all(
        re.fullmatch(r"m[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*", value)
        for value in condition_ids
    )
    rows = [
        {**plan["defaults"], **row}
        for plan in (screening, components)
        for row in plan["conditions"]
    ]
    assert len({r["condition_id"] for r in raw_rows}) == 146
    assert sum(r["measurement_count"]*r["frames_per_measurement"] for r in rows) == 73000
    assert all(
        {"measurement_count", "frames_per_measurement"}.isdisjoint(row)
        for row in raw_rows
    )
    assert all(
        {"setup_repeat", "component_id", "beam_angle_deg", "target_position"}.isdisjoint(row)
        for row in screening["conditions"]
    )
    assert screening["defaults"]["expected_gain"] == 1.0
    assert components["defaults"]["expected_gain"] == 1.0
    assert screening["defaults"]["exposure_min_us"] == 80.0
    assert components["defaults"]["exposure_min_us"] == 80.0
    assert len([r for r in rows if r["experiment_id"] == "V054"]) == 3
    assert {r["objective_id"] for r in screening["conditions"]} >= {"budget-4gx","myutron-4x"}
    with pytest.raises(ValueError,match="unresolved"):
        load_plan(root/"screening_green_v5.yaml","m001-screening-color-myutron-1x")
