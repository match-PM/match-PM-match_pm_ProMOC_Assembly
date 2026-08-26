"""Hardware-independent tests for pattern-independent adaptive ROI selection."""
from __future__ import annotations

from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from camera_nodes.algorithms.target_tilt import (
    RoiTiltEstimator,
    TiltEstimatorConfig,
    TiltStatus,
)
from camera_nodes.algorithms.tilt_roi_selection import (
    SupportRegion,
    check_observability,
    detect_support,
    make_overlapping_rois,
    select_spatially_distributed,
    validate_bbox,
)
from camera_nodes.algorithms.tilt_surface import build_surface_design, fit_surface


def _grid_fits(mask, *, valid_mask=None, quality=None, size=20):
    rows,cols=mask.shape; fits=[]
    valid_mask=mask if valid_mask is None else valid_mask
    for y in range(rows):
        for x in range(cols):
            index=y*cols+x; cx=(x+.5)*size; cy=(y+.5)*size
            fits.append(SimpleNamespace(index=index,x_px=cx,y_px=cy,x0_px=x*size,y0_px=y*size,x1_px=(x+1)*size,y1_px=(y+1)*size,structurally_valid=bool(mask[y,x]),valid=bool(valid_mask[y,x]),quality_score=float(quality[y,x] if quality is not None else index+1),support_member=False,selected=False,reason="ok",target_bin="",nearest_selected_distance_px=np.nan))
    return fits,(rows*size,cols*size)


def test_auto_support_keeps_central_target_and_removes_isolated_noise():
    mask=np.zeros((11,11),bool); mask[3:8,3:8]=True; mask[0,0]=True; mask[10,10]=True
    fits,shape=_grid_fits(mask)
    support=detect_support(fits,shape,mode="auto_texture",manual_bbox=(0,0,1,1))
    assert support.valid
    assert 0 not in support.member_indices
    assert 120 not in support.member_indices
    assert len(support.member_indices)==25
    assert support.bbox_normalized==pytest.approx((3/11,3/11,8/11,8/11))


@pytest.mark.parametrize("radii", [(4,), (2,4)])
def test_ring_support_allows_empty_center_and_concentric_rings(radii):
    yy,xx=np.mgrid[:13,:13]; distance=np.hypot(xx-6,yy-6)
    mask=np.zeros((13,13),bool)
    for radius in radii: mask|=np.abs(distance-radius)<.8
    fits,shape=_grid_fits(mask)
    support=detect_support(fits,shape,mode="auto_texture",manual_bbox=(0,0,1,1))
    assert support.valid
    assert not mask[6,6]
    assert len(support.member_indices)>=int(mask.sum()*.8)


def test_clipped_target_support_reaches_sensor_border():
    mask=np.zeros((8,10),bool); mask[2:7,0:4]=True
    support=detect_support(_grid_fits(mask)[0],(160,200),mode="auto_texture",manual_bbox=(0,0,1,1))
    assert support.valid
    assert support.bbox_normalized[0]==0.0


def test_manual_bbox_validation_and_resolution_independence():
    assert validate_bbox((.2,.25,.8,.75))==(.2,.25,.8,.75)
    with pytest.raises(ValueError,match="0 <= min"):
        validate_bbox((.8,.2,.2,.7))
    rois,_=make_overlapping_rois(.1,.1,.08,.08,bbox=(.2,.2,.8,.8))
    first_small=rois[0].pixels((100,200)); first_large=rois[0].pixels((200,400))
    assert first_large==tuple(value*2 for value in first_small)


def test_spatial_bins_prevent_overlapping_candidates_from_dominating():
    mask=np.ones((9,9),bool); quality=np.ones((9,9)); quality[4,4]=1000
    fits,shape=_grid_fits(mask,quality=quality)
    support=SupportRegion(True,(0,0,1,1),1.0,frozenset(range(81)))
    selected=select_spatially_distributed(fits,support,shape,maximum_selected=16)
    assert len(selected)<=16
    assert min(fit.x_px for fit in selected)==min(fit.x_px for fit in fits)
    assert max(fit.x_px for fit in selected)==max(fit.x_px for fit in fits)
    assert min(fit.y_px for fit in selected)==min(fit.y_px for fit in fits)
    assert max(fit.y_px for fit in selected)==max(fit.y_px for fit in fits)
    assert len({fit.target_bin for fit in selected})==9
    assert any(fit.index==40 for fit in selected)
    assert any(fit.reason=="spatially_redundant" for fit in fits)


@pytest.mark.parametrize("axis", ["horizontal", "vertical"])
def test_line_only_structure_is_not_observable_in_2d(axis):
    mask=np.zeros((9,9),bool)
    mask[4,:]=True if axis=="horizontal" else False
    if axis=="vertical": mask[:,4]=True
    fits,shape=_grid_fits(mask); chosen=[fit for fit in fits if fit.valid]
    support=SupportRegion(True,(0,0,1,1),1.0,frozenset(f.index for f in chosen))
    result=check_observability(chosen,support,shape,4.0,minimum_baseline_x_mm=.1,minimum_baseline_y_mm=.1,minimum_bins_x=3,minimum_bins_y=3,minimum_quadrants=4,maximum_condition=100)
    assert not result.valid


def test_smaller_physical_baseline_increases_slope_uncertainty():
    normalized=np.asarray([[-1,-1],[-1,1],[0,-1],[0,1],[1,-1],[1,1]],float)
    noise=np.asarray([.001,-.001,.0005,-.0005,.0008,-.0008])
    variances=[]
    for scale in (1.0,.25):
        design=build_surface_design(normalized[:,0]*scale,normalized[:,1]*scale,quadratic=False)
        values=design@np.asarray([2.,.01,-.02])+noise
        variances.append(fit_surface(design,values,robust=False).covariance[1,1])
    assert variances[1]>variances[0]*10


def test_low_quality_edge_rois_do_not_bias_plane_angle():
    xx,yy=np.meshgrid(np.linspace(-2,2,7),np.linspace(-1.5,1.5,7))
    design=build_surface_design(xx.ravel(),yy.ravel(),quadratic=False)
    expected=np.asarray([2.,.012,-.018]); values=design@expected
    edge=(np.abs(xx.ravel())>1.9)|(np.abs(yy.ravel())>1.4)
    values[edge]+=.08*np.sign(xx.ravel()[edge]+.1)
    weights=np.where(edge,.05,1.)
    result=fit_surface(design,values,base_weights=weights,robust=True)
    assert result.coefficients[1:]==pytest.approx(expected[1:],abs=.002)
    assert np.min(result.robust_weights[edge])<1


def test_central_grid_target_is_found_while_noisy_borders_are_rejected():
    rois,_=make_overlapping_rois(.12,.12,.08,.08)
    config=TiltEstimatorConfig(object_um_per_pixel=4.,roi_selection_mode="auto_texture",min_valid_rois=6,minimum_selected_rois=6,maximum_selected_rois=20,minimum_baseline_x_mm=.1,minimum_baseline_y_mm=.1,minimum_spatial_bins_x=2,minimum_spatial_bins_y=2,min_quadrants=4,min_peak_prominence=.01,min_fit_r2=.2,minimum_target_coverage_fraction=.03)
    estimator=RoiTiltEstimator(rois,config); rng=np.random.default_rng(4)
    texture=rng.integers(20,236,(100,100),dtype=np.uint8)
    for z_mm in np.linspace(-.04,.04,9):
        image=rng.integers(0,3,(200,200),dtype=np.uint8)
        image[50:150,50:150]=cv2.GaussianBlur(texture,(0,0),.5+abs(z_mm)*100)
        estimator.add_position(z_mm,[(image,"mono8")]*3)
    result=estimator.solve()
    assert result.status==TiltStatus.OK
    assert result.structurally_valid_candidate_count<result.candidate_roi_count
    assert result.selected_roi_count<=20
    assert result.roi_valid==result.focus_valid_roi_count
    assert result.roi_rejected_focus==result.candidate_roi_count-result.focus_valid_roi_count
    assert result.roi_rejected_spatial==result.focus_valid_roi_count-result.selected_roi_count
    assert result.roi_rejected_surface==result.selected_roi_count-result.surface_inlier_count
    assert result.roi_surface_inliers==result.surface_inlier_count
    assert result.target_bbox_normalized[0]>0 and result.target_bbox_normalized[2]<1


def test_hotpixel_islands_do_not_create_target_support():
    rois,_=make_overlapping_rois(.12,.12,.08,.08)
    config=TiltEstimatorConfig(object_um_per_pixel=4.,roi_selection_mode="auto_texture",min_valid_rois=4,minimum_selected_rois=4,minimum_target_coverage_fraction=.03)
    estimator=RoiTiltEstimator(rois,config)
    for z_mm in (-.02,0.,.02):
        image=np.zeros((160,160),np.uint8); image[5,5]=255; image[150,145]=255
        estimator.add_position(z_mm,[(image,"mono8")]*2)
    assert estimator.solve().status==TiltStatus.INSUFFICIENT_TEXTURE


def test_tenengrad_sobel_is_computed_once_per_frame(monkeypatch):
    rois,_=make_overlapping_rois(.2,.2,.2,.2)
    estimator=RoiTiltEstimator(rois,TiltEstimatorConfig(object_um_per_pixel=1.,roi_selection_mode="fixed_grid",minimum_selected_rois=3,min_valid_rois=3))
    calls=0; original=cv2.Sobel
    def counted(*args,**kwargs):
        nonlocal calls; calls+=1; return original(*args,**kwargs)
    monkeypatch.setattr(cv2,"Sobel",counted)
    estimator.add_position(0.,[(np.zeros((80,100),np.uint8),"mono8")])
    assert calls==2


def test_direct_roi_sums_match_previous_float64_integral_values():
    rng=np.random.default_rng(91); image=rng.integers(0,256,(240,320),dtype=np.uint8)
    rois,_=make_overlapping_rois(.18,.16,.11,.10)
    estimator=RoiTiltEstimator(rois,TiltEstimatorConfig(object_um_per_pixel=1.))
    estimator.add_position(0.,[(image,"mono8")])
    actual=estimator.positions[0].focus["tenengrad"]
    gray=image.astype(np.float32)/np.float32(255.)
    gx=cv2.Sobel(gray,cv2.CV_32F,1,0,ksize=3); gy=cv2.Sobel(gray,cv2.CV_32F,0,1,ksize=3)
    energy=gx*gx+gy*gy; integral=cv2.integral(energy,sdepth=cv2.CV_64F)
    expected=[]
    for roi in rois:
        x0,y0,x1,y1=roi.pixels(image.shape)
        total=integral[y1,x1]-integral[y0,x1]-integral[y1,x0]+integral[y0,x0]
        expected.append(total/((x1-x0)*(y1-y0)))
    assert actual==pytest.approx(expected,rel=2e-7,abs=1e-10)


def _solve_synthetic_ring(thickness, *, pattern="complete", contrast=70, noise=1.5,
                          dense_fraction=.01):
    size=384; center=(size//2,size//2); radii=(118,)
    if pattern=="clipped": center=(35,size//2); radii=(132,)
    elif pattern=="concentric": radii=(72,126)
    rois,_=make_overlapping_rois(.18,.18,.10,.10)
    config=TiltEstimatorConfig(
        object_um_per_pixel=4.0,roi_selection_mode="auto_texture",
        min_valid_rois=6,minimum_selected_rois=6,maximum_selected_rois=20,
        minimum_baseline_x_mm=.10,minimum_baseline_y_mm=.10,
        minimum_spatial_bins_x=2,minimum_spatial_bins_y=2,min_quadrants=4,
        min_span_fraction=.35,min_peak_prominence=.005,min_fit_r2=.10,
        max_frame_cv=1.0,minimum_target_coverage_fraction=.015,
        analysis_max_dimension_px=256,
        minimum_structured_pixel_fraction=dense_fraction,
    )
    estimator=RoiTiltEstimator(rois,config); rng=np.random.default_rng(1000+thickness)
    for z_mm in np.linspace(-.04,.04,9):
        sharp=np.full((size,size),90,np.uint8)
        for radius in radii:
            cv2.circle(sharp,center,radius,90+contrast,thickness,lineType=cv2.LINE_8)
        sigma=.45+abs(z_mm)*70.0
        blurred=cv2.GaussianBlur(sharp,(0,0),sigma)
        frames=[]
        for _ in range(2):
            frame=np.clip(blurred.astype(np.float32)+rng.normal(0,noise,blurred.shape),0,255).astype(np.uint8)
            hot_y=rng.integers(0,size,8); hot_x=rng.integers(0,size,8); frame[hot_y,hot_x]=255
            frames.append((frame,"mono8"))
        estimator.add_position(float(z_mm),frames)
    return estimator.solve(),estimator


@pytest.mark.parametrize("thickness",[1,2,3,5])
def test_thin_ring_images_pass_complete_end_to_end_pipeline(thickness):
    result,_=_solve_synthetic_ring(thickness)
    assert result.status==TiltStatus.OK,result.status_message
    assert result.selected_roi_count>=6
    assert result.surface_inlier_count>=6


@pytest.mark.parametrize("pattern",["clipped","concentric"])
def test_clipped_and_concentric_ring_images_pass_end_to_end(pattern):
    result,_=_solve_synthetic_ring(1,pattern=pattern,contrast=45,noise=2.0)
    assert result.status==TiltStatus.OK,result.status_message
    assert result.target_coverage_fraction>0


def test_one_pixel_ring_can_pass_explicit_sparse_connected_edge_path():
    result,_=_solve_synthetic_ring(1,dense_fraction=.20)
    assert result.status==TiltStatus.OK,result.status_message
    assert any(fit.selected and fit.sparse_edge_valid for fit in result.roi_fits)


def test_hotpixels_alone_fail_sparse_edge_path_end_to_end():
    rois,_=make_overlapping_rois(.18,.18,.10,.10)
    config=TiltEstimatorConfig(object_um_per_pixel=4.,roi_selection_mode="auto_texture",min_valid_rois=4,minimum_selected_rois=4,minimum_target_coverage_fraction=.01,analysis_max_dimension_px=256)
    estimator=RoiTiltEstimator(rois,config); rng=np.random.default_rng(77)
    for z_mm in np.linspace(-.03,.03,7):
        frames=[]
        for _ in range(2):
            image=np.full((384,384),90,np.uint8)
            image[rng.integers(0,384,20),rng.integers(0,384,20)]=255
            frames.append((image,"mono8"))
        estimator.add_position(float(z_mm),frames)
    result=estimator.solve()
    assert result.status!=TiltStatus.OK
    assert result.focus_valid_roi_count==0
    assert not any(fit.sparse_edge_valid for fit in result.roi_fits)
