"""Tests for modular peak, weighted surface and diagnostic export paths."""
from __future__ import annotations
import json
import math

import numpy as np
import pytest

from camera_nodes.algorithms.target_tilt import RoiFocusFit, TiltEstimate, TiltStatus, _decision
from camera_nodes.algorithms.tilt_evaluation import export_evaluation
from camera_nodes.algorithms.tilt_peak import fit_focus_peak
from camera_nodes.algorithms.tilt_surface import ReferenceSurface, build_surface_design, fit_surface
from camera_nodes.tilt_repeatability import main as repeatability_main


@pytest.mark.parametrize("method", ["quadratic", "gaussian"])
def test_peak_models_recover_substep_peak(method):
    z=np.linspace(-.1,.1,21)
    if method=="quadratic": values=5.-220.*(z-.013)**2
    else: values=.2+4.*np.exp(-.5*((z-.013)/.025)**2)
    result=fit_focus_peak(z,values,method=method,half_window=3)
    assert result.valid
    assert result.z_peak_mm==pytest.approx(.013,abs=5e-4)
    assert result.fit_r2>.99
    assert result.uncertainty_mm>=0


def test_peak_boundary_is_rejected_with_reason():
    result=fit_focus_peak(np.arange(5.),np.arange(5.),half_window=2)
    assert not result.valid
    assert result.reject_reason=="peak_at_scan_boundary"


def test_inverse_variance_weighting_limits_noisy_roi():
    x=np.asarray([-2.,-1.,0.,1.,2.,0.]); y=np.asarray([0.,1.,-1.,1.,0.,2.])
    design=build_surface_design(x,y,quadratic=False); expected=np.asarray([3.,.02,-.01])
    values=design@expected; values[-1]+=.8
    unweighted=fit_surface(design,values,robust=False)
    weighted=fit_surface(design,values,base_weights=np.asarray([1,1,1,1,1,1e-4]),robust=False)
    assert np.linalg.norm(weighted.coefficients-expected)<np.linalg.norm(unweighted.coefficients-expected)
    assert weighted.base_weights[-1]<weighted.base_weights[0]


def test_huber_fit_exports_outlier_weight():
    x=np.linspace(-2,2,20); y=np.sin(x); design=build_surface_design(x,y,quadratic=False)
    values=design@np.asarray([1.,.02,-.03]); values[4]+=.5
    result=fit_surface(design,values,robust=True)
    assert result.robust_weights[4]<.1
    assert result.residuals[4]>.4


def test_interval_decision_has_inconclusive_state():
    assert _decision(.0,.01,.05)=="PASS"
    assert _decision(.08,.01,.05)=="FAIL"
    assert _decision(.05,.01,.05)=="INCONCLUSIVE"


def test_reference_surface_round_trip_and_profile_guard(tmp_path):
    path=tmp_path/"reference.json"
    reference=ReferenceSurface("plane",(2.,.01,-.02),.8,(100,200),{"camera":"test"})
    reference.save(path); loaded=ReferenceSurface.load(path)
    loaded.validate_profile(object_um_per_pixel=.8,image_shape=(100,200))
    assert loaded.evaluate(np.asarray([1.]),np.asarray([2.]))[0]==pytest.approx(1.97)
    with pytest.raises(ValueError,match="image shape"):
        loaded.validate_profile(object_um_per_pixel=.8,image_shape=(101,200))


def test_evaluation_export_writes_machine_readable_artifacts(tmp_path):
    fit=RoiFocusFit(index=0,valid=True,reason="ok",x_px=10,y_px=10,
                    focus_z_mm=1.,surface_z_mm=1.,surface_residual_um=0.,
                    curve_z_mm=[.9,1.,1.1],curve_values=[1.,2.,1.])
    estimate=TiltEstimate(TiltStatus.OK,"ok",tilt_x_deg=.01,tilt_y_deg=.02,
                          roi_total=1,roi_valid=1,roi_fits=[fit])
    directory=export_evaluation(tmp_path,estimate,roi_rows=1,roi_cols=1)
    payload=json.loads((tmp_path/str(directory).split("/")[-1]/"summary.json").read_text())
    assert payload["status_name"]=="OK"
    assert (tmp_path/str(directory).split("/")[-1]/"roi_data.csv").exists()
    assert (tmp_path/str(directory).split("/")[-1]/"focus_curves.csv").exists()


def test_repeatability_report_and_reference(tmp_path):
    root=tmp_path/"runs"
    for index,angle in enumerate((.01,.02)):
        run=root/f"run_{index}"; run.mkdir(parents=True)
        summary={"tilt_x_deg":angle,"tilt_y_deg":0.,"center_focus_z_mm":1.,"surface_rms_um":2.,"roi_valid":1,"surface_model":"plane","surface_coefficients":[1.,angle,0.],"reference_applied":False,"metadata":{"image_shape":[100,200],"object_um_per_pixel":.8}}
        (run/"summary.json").write_text(json.dumps(summary))
        (run/"roi_data.csv").write_text("index,focus_z_mm,surface_residual_um\n0,1.0,0.1\n")
    output=tmp_path/"report"; reference=tmp_path/"reference.json"
    repeatability_main([str(root),"--output",str(output),"--reference-output",str(reference)])
    assert (output/"runs_summary.csv").exists()
    assert (output/"roi_repeatability.csv").exists()
    assert json.loads(reference.read_text())["coefficients"][1]==pytest.approx(.015)
