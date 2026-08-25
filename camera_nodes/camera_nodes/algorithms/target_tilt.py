"""Focus-stack based planar-target tilt estimation, independent of ROS.

Images are discarded after scalar ROI metrics have been extracted. Image x
points right and image y down; positive tilt means best-focus Z increases in
the corresponding image direction.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
import math
from pathlib import Path
from typing import Iterable, Sequence

import cv2
import numpy as np

from .tilt_peak import fit_focus_peak
from .tilt_surface import ReferenceSurface, build_surface_design, fit_surface

SUPPORTED_FOCUS_METRICS = ("tenengrad", "modified_laplacian", "variance_laplacian")


class TiltStatus(IntEnum):
    OK = 0
    INSUFFICIENT_TEXTURE = 1
    INSUFFICIENT_COVERAGE = 2
    FOCUS_OUTSIDE_SCAN = 3
    FIT_UNSTABLE = 4
    CANCELLED = 5
    HARDWARE_TIMEOUT = 6
    IMAGE_TIMEOUT = 7


@dataclass(frozen=True)
class NormalizedRoi:
    x0: float
    y0: float
    x1: float
    y1: float

    def pixels(self, shape: tuple[int, int]) -> tuple[int, int, int, int]:
        h, w = shape
        x0 = max(0, min(w - 1, int(round(self.x0 * w))))
        y0 = max(0, min(h - 1, int(round(self.y0 * h))))
        x1 = max(x0 + 1, min(w, int(round(self.x1 * w))))
        y1 = max(y0 + 1, min(h, int(round(self.y1 * h))))
        return x0, y0, x1, y1


def make_grid_rois(rows=7, cols=7, *, roi_width_fraction=.10,
                   roi_height_fraction=.10, margin_fraction=.08):
    if rows < 2 or cols < 2:
        raise ValueError("ROI grid requires at least two rows and columns")
    if not (0 < roi_width_fraction < 1 and 0 < roi_height_fraction < 1):
        raise ValueError("ROI width and height fractions must be in (0, 1)")
    if not (0 <= margin_fraction < .5):
        raise ValueError("margin_fraction must be in [0, 0.5)")
    xs = np.linspace(margin_fraction, 1-margin_fraction, cols)
    ys = np.linspace(margin_fraction, 1-margin_fraction, rows)
    return [NormalizedRoi(max(0, float(x-roi_width_fraction/2)),
                          max(0, float(y-roi_height_fraction/2)),
                          min(1, float(x+roi_width_fraction/2)),
                          min(1, float(y+roi_height_fraction/2)))
            for y in ys for x in xs]


@dataclass(frozen=True)
class TiltEstimatorConfig:
    object_um_per_pixel: float
    use_integral_image: bool = True
    focus_metric: str = "tenengrad"
    evaluation_focus_metrics: tuple[str, ...] = ()
    peak_fit_method: str = "quadratic"
    surface_weighted: bool = False
    surface_robust: bool = True
    huber_k: float = 1.345
    min_contrast: float = .015
    max_black_fraction: float = .98
    max_saturated_fraction: float = .98
    min_gradient_energy: float = 1e-5
    max_frame_cv: float = .35
    min_peak_prominence: float = .03
    min_peak_curvature: float = 1e-6
    min_fit_r2: float = .40
    max_peak_uncertainty_um: float = 100.
    weight_sigma_floor_um: float = .5
    weight_sigma_ceiling_um: float = 100.
    robust_outlier_weight_threshold: float = .25
    min_valid_rois: int = 10
    min_span_fraction: float = .50
    min_quadrants: int = 4
    max_design_condition: float = 100.
    repeatability_x_deg: float = .002
    repeatability_y_deg: float = .002
    tolerance_x_deg: float = .05
    tolerance_y_deg: float = .05
    retain_frame_scores: bool = False
    bootstrap_iterations: int = 0
    bootstrap_seed: int = 1729
    reference_surface_path: str = ""

    def __post_init__(self):
        if self.object_um_per_pixel <= 0:
            raise ValueError("object_um_per_pixel must be positive")
        unknown = set((self.focus_metric,) + tuple(self.evaluation_focus_metrics)) - set(SUPPORTED_FOCUS_METRICS)
        if unknown:
            raise ValueError(f"unsupported focus metrics: {sorted(unknown)}")
        if self.weight_sigma_floor_um <= 0 or self.weight_sigma_ceiling_um < self.weight_sigma_floor_um:
            raise ValueError("invalid peak-uncertainty weight bounds")


@dataclass
class RoiFocusFit:
    index: int
    valid: bool
    reason: str
    x_px: float
    y_px: float
    x_mm: float = math.nan
    y_mm: float = math.nan
    peak_fit_method: str = ""
    discrete_peak_z_mm: float = math.nan
    focus_z_mm: float = math.nan
    focus_uncertainty_mm: float = math.nan
    peak_value: float = math.nan
    peak_width_mm: float = math.nan
    peak_prominence: float = math.nan
    curvature: float = math.nan
    fit_r2: float = math.nan
    fit_rmse: float = math.nan
    frame_score_mean: float = math.nan
    frame_score_std: float = math.nan
    frame_score_cv: float = math.nan
    surface_z_mm: float = math.nan
    surface_residual_um: float = math.nan
    base_weight: float = math.nan
    robust_weight: float = math.nan
    final_weight: float = math.nan
    surface_inlier: bool = False
    curve_z_mm: list[float] = field(default_factory=list)
    curve_values: list[float] = field(default_factory=list)
    local_fit_z_mm: list[float] = field(default_factory=list)
    local_fit_values: list[float] = field(default_factory=list)

    @property
    def reject_reason(self):
        return "" if self.valid else self.reason


@dataclass
class BootstrapSummary:
    successful_iterations: int = 0
    tilt_x_std_deg: float = math.nan
    tilt_y_std_deg: float = math.nan
    center_z_std_um: float = math.nan
    tilt_x_ci95_deg: tuple[float, float] = (math.nan, math.nan)
    tilt_y_ci95_deg: tuple[float, float] = (math.nan, math.nan)
    center_z_ci95_mm: tuple[float, float] = (math.nan, math.nan)


@dataclass
class TiltEstimate:
    status: TiltStatus
    status_message: str
    tilt_x_deg: float = math.nan
    tilt_y_deg: float = math.nan
    uncertainty_x_deg: float = math.nan
    uncertainty_y_deg: float = math.nan
    detection_limit_x_deg: float = math.nan
    detection_limit_y_deg: float = math.nan
    center_focus_z_mm: float = math.nan
    surface_rms_um: float = math.nan
    surface_mae_um: float = math.nan
    surface_median_abs_um: float = math.nan
    surface_max_abs_um: float = math.nan
    roi_total: int = 0
    roi_valid: int = 0
    roi_surface_inliers: int = 0
    roi_rejected_focus: int = 0
    roi_robust_outliers: int = 0
    x_span_fraction: float = 0.
    y_span_fraction: float = 0.
    tilt_x_detectable: bool = False
    tilt_y_detectable: bool = False
    within_tolerance_x: bool = False
    within_tolerance_y: bool = False
    resolution_limited_x: bool = True
    resolution_limited_y: bool = True
    decision_x: str = "INVALID"
    decision_y: str = "INVALID"
    mean_peak_uncertainty_um: float = math.nan
    median_peak_uncertainty_um: float = math.nan
    surface_model: str = "plane"
    surface_coefficients: list[float] = field(default_factory=list)
    reference_applied: bool = False
    evaluation_directory: str = ""
    bootstrap: BootstrapSummary = field(default_factory=BootstrapSummary)
    roi_fits: list[RoiFocusFit] = field(default_factory=list)


@dataclass
class _PositionData:
    z_mm: float
    focus: dict[str, np.ndarray]
    frame_mean: dict[str, np.ndarray]
    frame_std: dict[str, np.ndarray]
    frame_cv: dict[str, np.ndarray]
    raw_focus: dict[str, np.ndarray]
    contrast: np.ndarray
    black: np.ndarray
    saturated: np.ndarray


_BAYER_TO_RGB = {"bayer_rggb": cv2.COLOR_BayerRG2RGB,
                 "bayer_bggr": cv2.COLOR_BayerBG2RGB,
                 "bayer_gbrg": cv2.COLOR_BayerGB2RGB,
                 "bayer_grbg": cv2.COLOR_BayerGR2RGB}


def image_to_float32(image, encoding):
    if image is None or image.size == 0:
        raise ValueError("empty image")
    enc, array = str(encoding).strip().lower(), np.asarray(image)
    if enc == "mono8": gray, scale = array, 255.
    elif enc == "mono16": gray, scale = array, 65535.
    elif enc in {"rgb8", "bgr8"}:
        if array.ndim != 3 or array.shape[2] < 3:
            raise ValueError(f"{encoding} requires a three-channel image")
        gray, scale = array[:, :, 1], 255.
    else:
        bits = next((int(s) for s in ("8", "16") if enc.endswith(s)), 0)
        base = enc[:-len(str(bits))] if bits else ""
        if base not in _BAYER_TO_RGB or bits not in {8, 16} or array.ndim != 2:
            raise ValueError(
                f"unsupported encoding '{encoding}'; packed Bayer12 must be "
                "unpacked by the camera node"
            )
        gray = cv2.cvtColor(array, _BAYER_TO_RGB[base])[:, :, 1]
        scale = 255. if bits == 8 else 65535.
    if gray.ndim != 2:
        raise ValueError(f"encoding '{encoding}' produced a non-planar image")
    return np.ascontiguousarray(gray, dtype=np.float32)/np.float32(scale)


class RoiTiltEstimator:
    def __init__(self, rois: Sequence[NormalizedRoi], config: TiltEstimatorConfig):
        if not rois: raise ValueError("at least one ROI is required")
        self.rois, self.config = list(rois), config
        self._positions, self._signature, self._pixel_rois = [], None, []

    @property
    def image_signature(self): return self._signature

    @property
    def positions(self): return tuple(self._positions)

    def add_position(self, z_mm, frames: Iterable, *, default_encoding="mono8"):
        metrics = tuple(dict.fromkeys((self.config.focus_metric,) + tuple(self.config.evaluation_focus_metrics)))
        rows = {m: [] for m in metrics}; contrast_rows=[]; black_rows=[]; saturated_rows=[]
        for item in frames:
            raw, encoding = item if isinstance(item, tuple) else (item, default_encoding)
            gray = image_to_float32(np.asarray(raw), encoding)
            signature = (tuple(gray.shape), str(encoding).lower())
            if self._signature is None:
                self._signature = signature
                self._pixel_rois = [r.pixels(gray.shape) for r in self.rois]
            elif signature != self._signature:
                raise ValueError(f"image size or encoding changed during scan: {self._signature} -> {signature}")
            maps = _focus_maps(gray, metrics)
            integrals = {n: cv2.integral(v, sdepth=cv2.CV_64F) for n,v in maps.items()
                         if self.config.use_integral_image and n != "variance_laplacian"}
            per = {m: [] for m in metrics}; fc=[]; fb=[]; fs=[]
            for x0,y0,x1,y1 in self._pixel_rois:
                crop = gray[y0:y1,x0:x1]
                for m in metrics:
                    if m == "variance_laplacian": score=float(np.var(maps[m][y0:y1,x0:x1]))
                    elif m in integrals:
                        ii=integrals[m]; score=float((ii[y1,x1]-ii[y0,x1]-ii[y1,x0]+ii[y0,x0])/((x1-x0)*(y1-y0)))
                    else: score=float(np.mean(maps[m][y0:y1,x0:x1]))
                    per[m].append(score)
                p05,p95=np.percentile(crop,[5,95]); fc.append(float(p95-p05))
                fb.append(float(np.mean(crop<=.005))); fs.append(float(np.mean(crop>=.995)))
            for m in metrics: rows[m].append(np.asarray(per[m]))
            contrast_rows.append(fc); black_rows.append(fb); saturated_rows.append(fs)
        if not contrast_rows: raise ValueError("no frames supplied for scan position")
        stacks={m:np.vstack(v) for m,v in rows.items()}
        means={m:np.mean(v,axis=0) for m,v in stacks.items()}
        stds={m:np.std(v,axis=0,ddof=1 if v.shape[0]>1 else 0) for m,v in stacks.items()}
        cvs={m:stds[m]/np.maximum(np.abs(means[m]),1e-12) for m in metrics}
        retain=self.config.retain_frame_scores or self.config.bootstrap_iterations>0 or len(metrics)>1
        self._positions.append(_PositionData(float(z_mm),{m:np.median(v,axis=0) for m,v in stacks.items()},means,stds,cvs,stacks if retain else {},np.median(contrast_rows,axis=0),np.median(black_rows,axis=0),np.median(saturated_rows,axis=0)))

    def preliminary_valid_rois(self):
        if not self._positions: return 0
        contrast=np.max(np.vstack([p.contrast for p in self._positions]),axis=0)
        energy=np.max(np.vstack([p.focus[self.config.focus_metric] for p in self._positions]),axis=0)
        return int(np.sum((contrast>=self.config.min_contrast)&(energy>=self.config.min_gradient_energy)))

    def solve(self, *, quadratic_surface=False, peak_half_window=2):
        result=self._solve_metric(self.config.focus_metric,quadratic_surface,peak_half_window)
        if result.status==TiltStatus.OK and self.config.bootstrap_iterations>0:
            result.bootstrap=self._bootstrap(quadratic_surface,peak_half_window)
        return result

    def solve_metric(self, metric, *, quadratic_surface=False, peak_half_window=2):
        return self._solve_metric(metric,quadratic_surface,peak_half_window)

    def _solve_metric(self,metric,quadratic,half_window,focus_override=None):
        if len(self._positions)<3: return self._failure(TiltStatus.FIT_UNSTABLE,"at least three Z positions are required")
        positions=sorted(self._positions,key=lambda p:p.z_mm)
        if any(metric not in p.focus for p in positions): return self._failure(TiltStatus.FIT_UNSTABLE,f"focus metric '{metric}' was not acquired")
        z=np.asarray([p.z_mm for p in positions])
        if np.any(np.diff(z)<=0): return self._failure(TiltStatus.FIT_UNSTABLE,"Z positions must be distinct")
        focus=focus_override if focus_override is not None else np.vstack([p.focus[metric] for p in positions])
        contrast=np.vstack([p.contrast for p in positions]); black=np.vstack([p.black for p in positions]); saturated=np.vstack([p.saturated for p in positions])
        means=np.vstack([p.frame_mean[metric] for p in positions]); stds=np.vstack([p.frame_std[metric] for p in positions]); cvs=np.vstack([p.frame_cv[metric] for p in positions])
        shape=self._signature[0] if self._signature else (1,1)
        fits=[self._fit_roi(i,z,focus[:,i],contrast[:,i],black[:,i],saturated[:,i],means[:,i],stds[:,i],cvs[:,i],half_window) for i in range(len(self.rois))]
        valid=[f for f in fits if f.valid]; counts={}
        for f in fits: counts[f.reason]=counts.get(f.reason,0)+1
        if len(valid)<self.config.min_valid_rois:
            boundary=counts.get("focus_outside_scan",0)+counts.get("peak_at_scan_boundary",0)
            status=TiltStatus.INSUFFICIENT_TEXTURE if counts.get("no_texture",0)>=max(1,len(fits)//2) else TiltStatus.FOCUS_OUTSIDE_SCAN if boundary>=max(1,len(fits)//3) else TiltStatus.FIT_UNSTABLE
            return self._failure(status,f"only {len(valid)}/{len(fits)} ROIs valid; diagnostics={counts}",fits,len(valid))
        h,w=shape; xs=np.asarray([f.x_px for f in valid]); ys=np.asarray([f.y_px for f in valid])
        xspan=float(np.ptp(xs)/max(w,1)); yspan=float(np.ptp(ys)/max(h,1))
        quadrants=len({(x>=w/2,y>=h/2) for x,y in zip(xs,ys)})
        xmm=(xs-w/2)*self.config.object_um_per_pixel/1000; ymm=(ys-h/2)*self.config.object_um_per_pixel/1000
        linear=build_surface_design(xmm,ymm,quadratic=False); scaled=linear.copy(); scaled[:,1]/=max(np.std(xmm),1e-12); scaled[:,2]/=max(np.std(ymm),1e-12)
        rank=int(np.linalg.matrix_rank(scaled)); condition=float(np.linalg.cond(scaled))
        if xspan<self.config.min_span_fraction or yspan<self.config.min_span_fraction or quadrants<self.config.min_quadrants or rank<3 or not np.isfinite(condition) or condition>self.config.max_design_condition:
            return self._failure(TiltStatus.INSUFFICIENT_COVERAGE,f"coverage not observable: span=({xspan:.3f}, {yspan:.3f}), quadrants={quadrants}, rank={rank}, condition={condition:.2f}",fits,len(valid),xspan,yspan)
        values=np.asarray([f.focus_z_mm for f in valid]); reference_applied=False
        reference_values=np.zeros_like(values); reference_center_mm=0.0
        if self.config.reference_surface_path:
            try:
                ref=ReferenceSurface.load(Path(self.config.reference_surface_path)); ref.validate_profile(object_um_per_pixel=self.config.object_um_per_pixel,image_shape=shape)
                reference_values=ref.evaluate(xmm,ymm)
                reference_center_mm=float(ref.evaluate(np.asarray([0.]),np.asarray([0.]))[0])
                values=values-reference_values; reference_applied=True
            except (OSError,ValueError,KeyError) as exc:
                return self._failure(TiltStatus.FIT_UNSTABLE,f"invalid reference surface: {exc}",fits,len(valid),xspan,yspan)
        design=build_surface_design(xmm,ymm,quadratic=quadratic)
        uncertainties=np.asarray([f.focus_uncertainty_mm for f in valid])
        sigmas=np.where(np.isfinite(uncertainties),uncertainties,self.config.weight_sigma_ceiling_um/1000)
        sigmas=np.clip(sigmas,self.config.weight_sigma_floor_um/1000,self.config.weight_sigma_ceiling_um/1000)
        weights=1/sigmas**2 if self.config.surface_weighted else None
        try: surface=fit_surface(design,values,base_weights=weights,robust=self.config.surface_robust,huber_k=self.config.huber_k)
        except (ValueError,np.linalg.LinAlgError) as exc: return self._failure(TiltStatus.FIT_UNSTABLE,f"surface fit unstable: {exc}",fits,len(valid),xspan,yspan)
        for i,f in enumerate(valid):
            f.x_mm,f.y_mm=float(xmm[i]),float(ymm[i]); f.surface_z_mm=float(surface.predicted[i]+reference_values[i]); f.surface_residual_um=float(surface.residuals[i]*1000)
            f.base_weight=float(surface.base_weights[i]); f.robust_weight=float(surface.robust_weights[i]); f.final_weight=float(surface.final_weights[i])
            f.surface_inlier=f.robust_weight>=self.config.robust_outlier_weight_threshold
            if not f.surface_inlier: f.reason="robust_fit_outlier"
        c,cov=surface.coefficients,surface.covariance; sx,sy=float(c[1]),float(c[2]); tx,ty=math.degrees(math.atan(sx)),math.degrees(math.atan(sy))
        ux=max(math.degrees(math.sqrt(max(0.,cov[1,1]))/(1+sx*sx)),self.config.repeatability_x_deg); uy=max(math.degrees(math.sqrt(max(0.,cov[2,2]))/(1+sy*sy)),self.config.repeatability_y_deg)
        lx,ly=1.96*ux,1.96*uy; residual_um=surface.residuals*1000; finite_u=uncertainties[np.isfinite(uncertainties)]*1000
        return TiltEstimate(status=TiltStatus.OK,status_message="tilt estimated; PASS/FAIL uses the complete 95% interval; overlap is INCONCLUSIVE",tilt_x_deg=tx,tilt_y_deg=ty,uncertainty_x_deg=ux,uncertainty_y_deg=uy,detection_limit_x_deg=lx,detection_limit_y_deg=ly,center_focus_z_mm=float(c[0]+reference_center_mm),surface_rms_um=float(np.sqrt(np.mean(residual_um**2))),surface_mae_um=float(np.mean(np.abs(residual_um))),surface_median_abs_um=float(np.median(np.abs(residual_um))),surface_max_abs_um=float(np.max(np.abs(residual_um))),roi_total=len(fits),roi_valid=len(valid),roi_surface_inliers=sum(f.surface_inlier for f in valid),roi_rejected_focus=len(fits)-len(valid),roi_robust_outliers=sum(not f.surface_inlier for f in valid),x_span_fraction=xspan,y_span_fraction=yspan,tilt_x_detectable=abs(tx)>=lx,tilt_y_detectable=abs(ty)>=ly,within_tolerance_x=abs(tx)<=self.config.tolerance_x_deg,within_tolerance_y=abs(ty)<=self.config.tolerance_y_deg,resolution_limited_x=abs(tx)<lx,resolution_limited_y=abs(ty)<ly,decision_x=_decision(tx,lx,self.config.tolerance_x_deg),decision_y=_decision(ty,ly,self.config.tolerance_y_deg),mean_peak_uncertainty_um=float(np.mean(finite_u)) if finite_u.size else math.nan,median_peak_uncertainty_um=float(np.median(finite_u)) if finite_u.size else math.nan,surface_model="quadratic" if quadratic else "plane",surface_coefficients=[float(v) for v in c],reference_applied=reference_applied,roi_fits=fits)

    def _fit_roi(self,index,z,curve,contrast,black,saturated,means,stds,cvs,half_window):
        x0,y0,x1,y1=self._pixel_rois[index]; peak_i=int(np.argmax(curve))
        base=dict(index=index,x_px=(x0+x1)/2,y_px=(y0+y1)/2,peak_fit_method=self.config.peak_fit_method,discrete_peak_z_mm=float(z[peak_i]),frame_score_mean=float(means[peak_i]),frame_score_std=float(stds[peak_i]),frame_score_cv=float(cvs[peak_i]),curve_z_mm=z.tolist(),curve_values=curve.tolist())
        if float(np.max(contrast))<self.config.min_contrast or float(np.max(curve))<self.config.min_gradient_energy or float(black[peak_i])>self.config.max_black_fraction or float(saturated[peak_i])>self.config.max_saturated_fraction: return RoiFocusFit(valid=False,reason="no_texture",**base)
        if peak_i in {0,len(z)-1}: return RoiFocusFit(valid=False,reason="focus_outside_scan",**base)
        if float(cvs[peak_i])>self.config.max_frame_cv: return RoiFocusFit(valid=False,reason="unstable_curve",**base)
        peak=fit_focus_peak(z,curve,method=self.config.peak_fit_method,half_window=half_window)
        fields=dict(focus_z_mm=peak.z_peak_mm,focus_uncertainty_mm=peak.uncertainty_mm,peak_value=peak.peak_value,peak_width_mm=peak.width_mm,peak_prominence=peak.prominence,curvature=peak.curvature,fit_r2=peak.fit_r2,fit_rmse=peak.fit_rmse,local_fit_z_mm=peak.local_z_mm.tolist(),local_fit_values=peak.local_predicted.tolist())
        if not peak.valid: return RoiFocusFit(valid=False,reason=peak.reject_reason,**base,**fields)
        if peak.prominence<self.config.min_peak_prominence: return RoiFocusFit(valid=False,reason="ambiguous_peak",**base,**fields)
        if peak.curvature<self.config.min_peak_curvature or peak.fit_r2<self.config.min_fit_r2: return RoiFocusFit(valid=False,reason="unstable_curve",**base,**fields)
        if np.isfinite(peak.uncertainty_mm) and peak.uncertainty_mm*1000>self.config.max_peak_uncertainty_um: return RoiFocusFit(valid=False,reason="peak_uncertainty_too_large",**base,**fields)
        return RoiFocusFit(valid=True,reason="ok",**base,**fields)

    def _bootstrap(self,quadratic,half_window):
        metric=self.config.focus_metric
        if any(metric not in p.raw_focus for p in self._positions): return BootstrapSummary()
        rng=np.random.default_rng(self.config.bootstrap_seed); samples=[]
        for _ in range(self.config.bootstrap_iterations):
            rows=[]
            for p in sorted(self._positions,key=lambda p:p.z_mm):
                raw=p.raw_focus[metric]; rows.append(np.median(raw[rng.integers(0,raw.shape[0],raw.shape[0])],axis=0))
            e=self._solve_metric(metric,quadratic,half_window,np.vstack(rows))
            if e.status==TiltStatus.OK: samples.append((e.tilt_x_deg,e.tilt_y_deg,e.center_focus_z_mm))
        if len(samples)<2: return BootstrapSummary(successful_iterations=len(samples))
        v=np.asarray(samples); lo,hi=np.percentile(v,[2.5,97.5],axis=0); std=np.std(v,axis=0,ddof=1)
        return BootstrapSummary(len(samples),float(std[0]),float(std[1]),float(std[2]*1000),(float(lo[0]),float(hi[0])),(float(lo[1]),float(hi[1])),(float(lo[2]),float(hi[2])))

    def _failure(self,status,message,roi_fits=None,roi_valid=0,x_span=0.,y_span=0.):
        return TiltEstimate(status=status,status_message=message,roi_total=len(self.rois),roi_valid=roi_valid,roi_rejected_focus=len(self.rois)-roi_valid,x_span_fraction=x_span,y_span_fraction=y_span,roi_fits=roi_fits or [])


def _focus_maps(gray,metrics):
    result={}
    if "tenengrad" in metrics:
        gx=cv2.Sobel(gray,cv2.CV_32F,1,0,ksize=3); gy=cv2.Sobel(gray,cv2.CV_32F,0,1,ksize=3); result["tenengrad"]=gx*gx+gy*gy
    if "modified_laplacian" in metrics:
        result["modified_laplacian"]=np.abs(cv2.Sobel(gray,cv2.CV_32F,2,0,ksize=3))+np.abs(cv2.Sobel(gray,cv2.CV_32F,0,2,ksize=3))
    if "variance_laplacian" in metrics: result["variance_laplacian"]=cv2.Laplacian(gray,cv2.CV_32F,ksize=3)
    return result


def _decision(angle,limit95,tolerance):
    low,high=angle-limit95,angle+limit95
    if low>=-tolerance and high<=tolerance: return "PASS"
    if low>tolerance or high<-tolerance: return "FAIL"
    return "INCONCLUSIVE"


def _robust_huber_fit(design,values,*,max_iterations=30,huber_k=1.345):
    """Compatibility wrapper for the original public test helper."""
    fit=fit_surface(design,values,robust=True,huber_k=huber_k,max_iterations=max_iterations)
    return fit.coefficients,fit.covariance,fit.residuals
