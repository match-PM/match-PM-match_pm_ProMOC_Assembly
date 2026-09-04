"""Measurement safety/provenance tests without ROS or real axis commands."""
from dataclasses import asdict, replace
import json

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
    from pathlib import Path
    from camera_nodes.measurement_analyze import analyze_run
    path = Path(result["output_directory"])
    manifests = list(path.glob("measurements/m*/attempt_*/capture_manifest.json"))
    assert len(manifests) == 2
    original = [p.read_bytes() for p in manifests]
    for manifest in manifests:
        assert verify_capture(manifest,2)["capture_status"] == "complete"
    first = analyze_run(path)
    second = analyze_run(path)
    assert first != second
    assert (first/"frame_results.csv").is_file()
    assert [p.read_bytes() for p in manifests] == original
    prep = json.loads((path/"preparation.json").read_text())
    assert len(prep["focus"]["curve"]) >= condition.focus_samples
    assert prep["levels"]["bright_fraction"] == pytest.approx(.75,abs=.02)
    # Last four moves are the identical park/focus cycles, including m001.
    assert io.moves[-4:] == [condition.park_position_mm,prep["focus_position_mm"]]*2


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
    io.set_exposure = lambda value: pytest.fail("Resume must not change exposure")
    result = MeasurementEngine(condition,io).run("test",engine.store.run_id)
    assert result["captured_frames"] == 4


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
    rows = screening["conditions"]+components["conditions"]
    assert len({r["condition_id"] for r in rows}) == 146
    assert sum(r["measurement_count"]*r["frames_per_measurement"] for r in rows) == 73000
    assert len([r for r in rows if r["experiment_id"] == "V054"]) == 3
    assert {r["objective_id"] for r in screening["conditions"]} >= {"budget-4gx","myutron-4x"}
    with pytest.raises(ValueError,match="unresolved"):
        load_plan(root/"screening_green_v5.yaml","n003-v003")
