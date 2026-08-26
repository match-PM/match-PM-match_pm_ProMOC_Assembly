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
from .tilt_roi_selection import (
    SUPPORTED_SELECTION_MODES,
    check_observability,
    detect_support,
    select_spatially_distributed,
    validate_bbox,
)

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
    roi_selection_mode: str = "auto_texture"
    manual_target_bbox: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)
    minimum_structured_pixel_fraction: float = 0.01
    structure_mad_multiplier: float = 3.0
    structure_energy_quantile: float = 0.90
    analysis_max_dimension_px: int = 2048
    sparse_contrast_quantile: float = 0.999
    sparse_energy_quantile: float = 0.995
    minimum_gradient_snr: float = 6.0
    minimum_connected_edge_pixels: int = 6
    minimum_connected_edge_span_fraction: float = 0.12
    support_closing_radius: int = 1
    minimum_target_coverage_fraction: float = 0.05
    minimum_baseline_x_mm: float = 0.25
    minimum_baseline_y_mm: float = 0.25
    minimum_spatial_bins_x: int = 3
    minimum_spatial_bins_y: int = 3
    minimum_selected_rois: int = 10
    maximum_selected_rois: int = 30
    minimum_quality_weight: float = 0.05
    maximum_quality_weight: float = 20.0
    maximum_standardized_residual: float = 3.5

    def __post_init__(self):
        if self.object_um_per_pixel <= 0:
            raise ValueError("object_um_per_pixel must be positive")
        unknown = set((self.focus_metric,) + tuple(self.evaluation_focus_metrics)) - set(SUPPORTED_FOCUS_METRICS)
        if unknown:
            raise ValueError(f"unsupported focus metrics: {sorted(unknown)}")
        if self.weight_sigma_floor_um <= 0 or self.weight_sigma_ceiling_um < self.weight_sigma_floor_um:
            raise ValueError("invalid peak-uncertainty weight bounds")
        if self.roi_selection_mode not in SUPPORTED_SELECTION_MODES:
            raise ValueError(f"unsupported ROI selection mode '{self.roi_selection_mode}'")
        validate_bbox(self.manual_target_bbox)
        if not (0.0 <= self.minimum_structured_pixel_fraction <= 1.0):
            raise ValueError("minimum_structured_pixel_fraction must be in [0, 1]")
        if self.structure_mad_multiplier < 0.0:
            raise ValueError("structure_mad_multiplier must be non-negative")
        if not (0.0 < self.structure_energy_quantile < 1.0):
            raise ValueError("structure_energy_quantile must be in (0, 1)")
        if self.analysis_max_dimension_px < 128:
            raise ValueError("analysis_max_dimension_px must be at least 128")
        if not (0.5 < self.sparse_contrast_quantile < 1.0):
            raise ValueError("sparse_contrast_quantile must be in (0.5, 1)")
        if not (0.5 < self.sparse_energy_quantile < 1.0):
            raise ValueError("sparse_energy_quantile must be in (0.5, 1)")
        if self.minimum_gradient_snr <= 0.0:
            raise ValueError("minimum_gradient_snr must be positive")
        if self.minimum_connected_edge_pixels < 2:
            raise ValueError("minimum_connected_edge_pixels must be at least two")
        if not (0.0 < self.minimum_connected_edge_span_fraction <= 1.0):
            raise ValueError("minimum_connected_edge_span_fraction must be in (0, 1]")
        if not (0.0 <= self.minimum_target_coverage_fraction <= 1.0):
            raise ValueError("minimum_target_coverage_fraction must be in [0, 1]")
        if self.minimum_spatial_bins_x < 1 or self.minimum_spatial_bins_y < 1:
            raise ValueError("minimum spatial bin counts must be positive")
        if self.minimum_baseline_x_mm < 0.0 or self.minimum_baseline_y_mm < 0.0:
            raise ValueError("minimum physical baselines must be non-negative")
        if self.minimum_selected_rois < 3 or self.maximum_selected_rois < self.minimum_selected_rois:
            raise ValueError("invalid selected ROI count limits")
        if self.minimum_quality_weight <= 0 or self.maximum_quality_weight < self.minimum_quality_weight:
            raise ValueError("invalid quality-weight limits")
        if self.maximum_standardized_residual <= 0.0:
            raise ValueError("maximum_standardized_residual must be positive")


@dataclass
class RoiFocusFit:
    index: int
    valid: bool
    reason: str
    x_px: float
    y_px: float
    x0_px: int = 0
    y0_px: int = 0
    x1_px: int = 0
    y1_px: int = 0
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
    local_contrast: float = math.nan
    sparse_contrast: float = math.nan
    structured_pixel_fraction: float = math.nan
    gradient_energy_quantile: float = math.nan
    gradient_snr: float = math.nan
    connected_edge_pixels: int = 0
    connected_edge_span_fraction: float = 0.0
    sparse_edge_valid: bool = False
    structurally_valid: bool = False
    support_member: bool = False
    selected: bool = False
    target_bin: str = ""
    nearest_selected_distance_px: float = math.nan
    quality_score: float = math.nan
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
    roi_rejected_spatial: int = 0
    roi_rejected_surface: int = 0
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
    target_bbox_normalized: tuple[float, float, float, float] = (
        math.nan, math.nan, math.nan, math.nan
    )
    target_coverage_fraction: float = 0.0
    baseline_x_mm: float = 0.0
    baseline_y_mm: float = 0.0
    candidate_roi_count: int = 0
    structurally_valid_candidate_count: int = 0
    selected_roi_count: int = 0
    focus_valid_roi_count: int = 0
    surface_inlier_count: int = 0
    design_condition_number: float = math.inf


@dataclass
class _PositionData:
    z_mm: float
    focus: dict[str, np.ndarray]
    frame_mean: dict[str, np.ndarray]
    frame_std: dict[str, np.ndarray]
    frame_cv: dict[str, np.ndarray]
    raw_focus: dict[str, np.ndarray]
    contrast: np.ndarray
    sparse_contrast: np.ndarray
    black: np.ndarray
    saturated: np.ndarray
    structured_fraction: np.ndarray
    gradient_quantile: np.ndarray
    gradient_snr: np.ndarray
    connected_edge_pixels: np.ndarray
    connected_edge_span_fraction: np.ndarray


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
    result = np.ascontiguousarray(gray, dtype=np.float32)
    result *= np.float32(1.0 / scale)
    return result


class RoiTiltEstimator:
    def __init__(self, rois: Sequence[NormalizedRoi], config: TiltEstimatorConfig):
        if not rois: raise ValueError("at least one ROI is required")
        self.rois, self.config = list(rois), config
        self._positions, self._signature, self._pixel_rois = [], None, []

    @property
    def image_signature(self): return self._signature

    @property
    def positions(self): return tuple(self._positions)

    def diagnostic_image(self, estimate, max_dimension=1600):
        """Create a compact ROI-state overlay without retaining a source frame."""
        if not self._signature:
            raise ValueError("no image geometry available")
        height,width=self._signature[0]; scale=min(1.0,float(max_dimension)/max(height,width))
        canvas=np.full((max(1,int(round(height*scale))),max(1,int(round(width*scale))),3),32,dtype=np.uint8)
        for fit in estimate.roi_fits:
            color=(180,40,220) if fit.selected and not fit.surface_inlier else (40,210,40) if fit.selected else (0,190,240) if fit.structurally_valid else (40,40,210)
            p0=(int(fit.x0_px*scale),int(fit.y0_px*scale)); p1=(int(fit.x1_px*scale),int(fit.y1_px*scale))
            cv2.rectangle(canvas,p0,p1,color,2 if fit.selected else 1)
            if fit.selected:
                label=f"{fit.index} {fit.surface_residual_um:.1f}um" if np.isfinite(fit.surface_residual_um) else str(fit.index)
                cv2.putText(canvas,label,p0,cv2.FONT_HERSHEY_SIMPLEX,.35,color,1,cv2.LINE_AA)
        bbox=estimate.target_bbox_normalized
        if len(bbox)==4 and np.all(np.isfinite(bbox)):
            cv2.rectangle(canvas,(int(bbox[0]*width*scale),int(bbox[1]*height*scale)),(int(bbox[2]*width*scale),int(bbox[3]*height*scale)),(255,180,0),3)
        return canvas

    def add_position(self, z_mm, frames: Iterable, *, default_encoding="mono8"):
        metrics = tuple(dict.fromkeys((self.config.focus_metric,) + tuple(self.config.evaluation_focus_metrics)))
        rows = {m: [] for m in metrics}; contrast_rows=[]; sparse_contrast_rows=[]
        black_rows=[]; saturated_rows=[]; structured_rows=[]; gradient_quantile_rows=[]
        gradient_snr_rows=[]; edge_pixels_rows=[]; edge_span_rows=[]
        for item in frames:
            raw, encoding = item if isinstance(item, tuple) else (item, default_encoding)
            gray = image_to_float32(np.asarray(raw), encoding)
            signature = (tuple(gray.shape), str(encoding).lower())
            if self._signature is None:
                self._signature = signature
                self._pixel_rois = [r.pixels(gray.shape) for r in self.rois]
            elif signature != self._signature:
                raise ValueError(f"image size or encoding changed during scan: {self._signature} -> {signature}")
            analysis_gray = _analysis_image(gray, self.config.analysis_max_dimension_px)
            analysis_energy = _focus_map(analysis_gray, "tenengrad")
            threshold_sample = _bounded_sample(analysis_energy, 262144)
            energy_median = float(np.median(threshold_sample))
            energy_deviation = np.abs(threshold_sample - np.float32(energy_median))
            energy_mad = float(np.median(energy_deviation))
            del energy_deviation, threshold_sample
            significant_threshold = max(
                self.config.min_gradient_energy,
                energy_median + self.config.structure_mad_multiplier * 1.4826 * energy_mad,
            )
            analysis_rois = [
                _scale_roi(pixel_roi, gray.shape, analysis_gray.shape)
                for pixel_roi in self._pixel_rois
            ]
            fc=[]; fsc=[]; fb=[]; fs=[]; fstructured=[]; fquantile=[]
            fsnr=[]; fedgepixels=[]; fedgespan=[]
            for analysis_roi in analysis_rois:
                metrics_for_roi = _candidate_image_metrics(
                    analysis_gray,
                    analysis_energy,
                    analysis_roi,
                    significant_threshold,
                    structure_quantile=self.config.structure_energy_quantile,
                    sparse_contrast_quantile=self.config.sparse_contrast_quantile,
                    sparse_energy_quantile=self.config.sparse_energy_quantile,
                )
                fc.append(metrics_for_roi["contrast"])
                fsc.append(metrics_for_roi["sparse_contrast"])
                fb.append(metrics_for_roi["black_fraction"])
                fs.append(metrics_for_roi["saturated_fraction"])
                fstructured.append(metrics_for_roi["structured_fraction"])
                fquantile.append(metrics_for_roi["gradient_quantile"])
                fsnr.append(metrics_for_roi["gradient_snr"])
                fedgepixels.append(metrics_for_roi["connected_edge_pixels"])
                fedgespan.append(metrics_for_roi["connected_edge_span_fraction"])
            cached_tenengrad = analysis_energy if analysis_gray is gray and "tenengrad" in metrics else None
            if analysis_gray is not gray:
                del analysis_energy
            del analysis_gray

            per = {m: [] for m in metrics}
            for metric in metrics:
                focus_map = cached_tenengrad if metric == "tenengrad" and cached_tenengrad is not None else _focus_map(gray, metric)
                per[metric] = [
                    _roi_focus_score(focus_map, pixel_roi, metric)
                    for pixel_roi in self._pixel_rois
                ]
                del focus_map
                if metric == "tenengrad": cached_tenengrad = None
            for m in metrics: rows[m].append(np.asarray(per[m]))
            contrast_rows.append(fc); sparse_contrast_rows.append(fsc)
            black_rows.append(fb); saturated_rows.append(fs)
            structured_rows.append(fstructured); gradient_quantile_rows.append(fquantile)
            gradient_snr_rows.append(fsnr); edge_pixels_rows.append(fedgepixels)
            edge_span_rows.append(fedgespan)
        if not contrast_rows: raise ValueError("no frames supplied for scan position")
        stacks={m:np.vstack(v) for m,v in rows.items()}
        means={m:np.mean(v,axis=0) for m,v in stacks.items()}
        stds={m:np.std(v,axis=0,ddof=1 if v.shape[0]>1 else 0) for m,v in stacks.items()}
        cvs={m:stds[m]/np.maximum(np.abs(means[m]),1e-12) for m in metrics}
        retain=self.config.retain_frame_scores or self.config.bootstrap_iterations>0 or len(metrics)>1
        self._positions.append(_PositionData(
            float(z_mm), {m:np.median(v,axis=0) for m,v in stacks.items()},
            means, stds, cvs, stacks if retain else {},
            np.median(contrast_rows,axis=0), np.median(sparse_contrast_rows,axis=0),
            np.median(black_rows,axis=0),
            np.median(saturated_rows,axis=0), np.median(structured_rows,axis=0),
            np.median(gradient_quantile_rows,axis=0), np.median(gradient_snr_rows,axis=0),
            np.median(edge_pixels_rows,axis=0), np.median(edge_span_rows,axis=0)))

    def preliminary_valid_rois(self):
        if not self._positions: return 0
        contrast=np.max(np.vstack([p.contrast for p in self._positions]),axis=0)
        sparse_contrast=np.max(np.vstack([p.sparse_contrast for p in self._positions]),axis=0)
        structure=np.max(np.vstack([p.structured_fraction for p in self._positions]),axis=0)
        snr=np.max(np.vstack([p.gradient_snr for p in self._positions]),axis=0)
        edge_pixels=np.max(np.vstack([p.connected_edge_pixels for p in self._positions]),axis=0)
        edge_span=np.max(np.vstack([p.connected_edge_span_fraction for p in self._positions]),axis=0)
        dense=(contrast>=self.config.min_contrast)&(structure>=self.config.minimum_structured_pixel_fraction)
        sparse=(sparse_contrast>=self.config.min_contrast)&(snr>=self.config.minimum_gradient_snr)&(edge_pixels>=self.config.minimum_connected_edge_pixels)&(edge_span>=self.config.minimum_connected_edge_span_fraction)
        return int(np.sum(dense|sparse))

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
        contrast=np.vstack([p.contrast for p in positions]); sparse_contrast=np.vstack([p.sparse_contrast for p in positions])
        black=np.vstack([p.black for p in positions]); saturated=np.vstack([p.saturated for p in positions])
        structured=np.vstack([p.structured_fraction for p in positions]); quantile=np.vstack([p.gradient_quantile for p in positions])
        gradient_snr=np.vstack([p.gradient_snr for p in positions]); edge_pixels=np.vstack([p.connected_edge_pixels for p in positions]); edge_span=np.vstack([p.connected_edge_span_fraction for p in positions])
        means=np.vstack([p.frame_mean[metric] for p in positions]); stds=np.vstack([p.frame_std[metric] for p in positions]); cvs=np.vstack([p.frame_cv[metric] for p in positions])
        shape=self._signature[0] if self._signature else (1,1)
        fits=[self._fit_roi(i,z,focus[:,i],contrast[:,i],sparse_contrast[:,i],black[:,i],saturated[:,i],structured[:,i],quantile[:,i],gradient_snr[:,i],edge_pixels[:,i],edge_span[:,i],means[:,i],stds[:,i],cvs[:,i],half_window,shape) for i in range(len(self.rois))]
        support=detect_support(fits,shape,mode=self.config.roi_selection_mode,manual_bbox=self.config.manual_target_bbox,closing_radius=self.config.support_closing_radius)
        for fit in fits: fit.support_member=fit.index in support.member_indices
        structural_count=sum(fit.structurally_valid for fit in fits)
        if not support.valid or support.coverage_fraction < self.config.minimum_target_coverage_fraction:
            return self._failure(TiltStatus.INSUFFICIENT_TEXTURE,f"no stable target support; structured={structural_count}/{len(fits)}, coverage={support.coverage_fraction:.3f}",fits,0,target_bbox=support.bbox_normalized,target_coverage=support.coverage_fraction,structural_count=structural_count)
        quality_candidates=[fit for fit in fits if fit.valid and fit.support_member]
        if quality_candidates:
            quality_median=max(float(np.median([fit.quality_score for fit in quality_candidates])),1e-18)
            for fit in quality_candidates:
                fit.quality_score=float(np.clip(fit.quality_score/quality_median,self.config.minimum_quality_weight,self.config.maximum_quality_weight))
        if self.config.roi_selection_mode == "fixed_grid":
            selected=[fit for fit in fits if fit.valid]
            for fit in selected: fit.selected=True
        else:
            selected=select_spatially_distributed(
                fits,
                support,
                shape,
                self.config.maximum_selected_rois,
                minimum_bins_x=self.config.minimum_spatial_bins_x,
                minimum_bins_y=self.config.minimum_spatial_bins_y,
            )
        counts={}
        for f in fits: counts[f.reason]=counts.get(f.reason,0)+1
        required=max(self.config.min_valid_rois,self.config.minimum_selected_rois)
        if len(selected)<required:
            boundary=counts.get("peak_outside_scan",0)
            status=(TiltStatus.FOCUS_OUTSIDE_SCAN if boundary>=max(1,structural_count//3)
                    else TiltStatus.INSUFFICIENT_COVERAGE if len(selected)>=self.config.min_valid_rois
                    else TiltStatus.FIT_UNSTABLE)
            return self._failure(status,f"only {len(selected)}/{len(fits)} ROIs selected; diagnostics={counts}",fits,len(selected),target_bbox=support.bbox_normalized,target_coverage=support.coverage_fraction,structural_count=structural_count)
        observable=check_observability(selected,support,shape,self.config.object_um_per_pixel,minimum_baseline_x_mm=self.config.minimum_baseline_x_mm,minimum_baseline_y_mm=self.config.minimum_baseline_y_mm,minimum_bins_x=self.config.minimum_spatial_bins_x,minimum_bins_y=self.config.minimum_spatial_bins_y,minimum_quadrants=self.config.min_quadrants,maximum_condition=self.config.max_design_condition)
        if (not observable.valid or observable.coverage_x_fraction<self.config.min_span_fraction
                or observable.coverage_y_fraction<self.config.min_span_fraction):
            return self._failure(TiltStatus.INSUFFICIENT_COVERAGE,f"target-relative coverage not observable: baseline=({observable.baseline_x_mm:.3f}, {observable.baseline_y_mm:.3f}) mm, bins=({observable.bins_x}, {observable.bins_y}), quadrants={observable.quadrants}, condition={observable.condition_number:.2f}",fits,len(selected),observable.coverage_x_fraction,observable.coverage_y_fraction,target_bbox=support.bbox_normalized,target_coverage=support.coverage_fraction,structural_count=structural_count,observable=observable)
        h,w=shape; xs=np.asarray([f.x_px for f in selected]); ys=np.asarray([f.y_px for f in selected])
        xspan,yspan=observable.coverage_x_fraction,observable.coverage_y_fraction
        xmm=(xs-w/2)*self.config.object_um_per_pixel/1000; ymm=(ys-h/2)*self.config.object_um_per_pixel/1000
        values=np.asarray([f.focus_z_mm for f in selected]); reference_applied=False
        reference_values=np.zeros_like(values); reference_center_mm=0.0
        if self.config.reference_surface_path:
            try:
                ref=ReferenceSurface.load(Path(self.config.reference_surface_path)); ref.validate_profile(object_um_per_pixel=self.config.object_um_per_pixel,image_shape=shape)
                reference_values=ref.evaluate(xmm,ymm)
                reference_center_mm=float(ref.evaluate(np.asarray([0.]),np.asarray([0.]))[0])
                values=values-reference_values; reference_applied=True
            except (OSError,ValueError,KeyError) as exc:
                return self._failure(TiltStatus.FIT_UNSTABLE,f"invalid reference surface: {exc}",fits,len(selected),xspan,yspan,target_bbox=support.bbox_normalized,target_coverage=support.coverage_fraction,structural_count=structural_count,observable=observable)
        design=build_surface_design(xmm,ymm,quadratic=quadratic)
        uncertainties=np.asarray([f.focus_uncertainty_mm for f in selected])
        quality_weights=np.asarray([f.quality_score for f in selected])
        quality_weights/=max(float(np.median(quality_weights)),1e-18)
        quality_weights=np.clip(quality_weights,self.config.minimum_quality_weight,self.config.maximum_quality_weight)
        for fit,weight in zip(selected,quality_weights): fit.quality_score=float(weight)
        weights=quality_weights if (self.config.surface_weighted or self.config.roi_selection_mode != "fixed_grid") else None
        try: surface=fit_surface(design,values,base_weights=weights,robust=self.config.surface_robust,huber_k=self.config.huber_k)
        except (ValueError,np.linalg.LinAlgError) as exc: return self._failure(TiltStatus.FIT_UNSTABLE,f"surface fit unstable: {exc}",fits,len(selected),xspan,yspan,target_bbox=support.bbox_normalized,target_coverage=support.coverage_fraction,structural_count=structural_count,observable=observable)
        robust_scale=1.4826*float(np.median(np.abs(surface.residuals-np.median(surface.residuals))))
        for i,f in enumerate(selected):
            f.x_mm,f.y_mm=float(xmm[i]),float(ymm[i]); f.surface_z_mm=float(surface.predicted[i]+reference_values[i]); f.surface_residual_um=float(surface.residuals[i]*1000)
            f.base_weight=float(surface.base_weights[i]); f.robust_weight=float(surface.robust_weights[i]); f.final_weight=float(surface.final_weights[i])
            standardized=abs(float(surface.residuals[i]))/max(robust_scale,1e-12)
            f.surface_inlier=f.robust_weight>=self.config.robust_outlier_weight_threshold and standardized<=self.config.maximum_standardized_residual
            if not f.surface_inlier: f.reason="surface_outlier"
        inliers=[fit for fit in selected if fit.surface_inlier]
        inlier_observable=check_observability(inliers,support,shape,self.config.object_um_per_pixel,minimum_baseline_x_mm=self.config.minimum_baseline_x_mm,minimum_baseline_y_mm=self.config.minimum_baseline_y_mm,minimum_bins_x=self.config.minimum_spatial_bins_x,minimum_bins_y=self.config.minimum_spatial_bins_y,minimum_quadrants=self.config.min_quadrants,maximum_condition=self.config.max_design_condition)
        if (len(inliers)<self.config.minimum_selected_rois or not inlier_observable.valid
                or inlier_observable.coverage_x_fraction<self.config.min_span_fraction
                or inlier_observable.coverage_y_fraction<self.config.min_span_fraction):
            return self._failure(TiltStatus.INSUFFICIENT_COVERAGE,"surface outliers leave insufficient physical coverage",fits,len(selected),xspan,yspan,target_bbox=support.bbox_normalized,target_coverage=support.coverage_fraction,structural_count=structural_count,observable=inlier_observable,surface_evaluated=True)
        c,cov=surface.coefficients,surface.covariance; sx,sy=float(c[1]),float(c[2]); tx,ty=math.degrees(math.atan(sx)),math.degrees(math.atan(sy))
        ux=max(math.degrees(math.sqrt(max(0.,cov[1,1]))/(1+sx*sx)),self.config.repeatability_x_deg); uy=max(math.degrees(math.sqrt(max(0.,cov[2,2]))/(1+sy*sy)),self.config.repeatability_y_deg)
        lx,ly=1.96*ux,1.96*uy; residual_um=surface.residuals*1000; finite_u=uncertainties[np.isfinite(uncertainties)]*1000
        focus_valid_count=sum(f.valid for f in fits)
        surface_inlier_count=len(inliers)
        return TiltEstimate(status=TiltStatus.OK,status_message="tilt estimated from adaptive target support; PASS/FAIL uses the complete 95% interval",tilt_x_deg=tx,tilt_y_deg=ty,uncertainty_x_deg=ux,uncertainty_y_deg=uy,detection_limit_x_deg=lx,detection_limit_y_deg=ly,center_focus_z_mm=float(c[0]+reference_center_mm),surface_rms_um=float(np.sqrt(np.mean(residual_um**2))),surface_mae_um=float(np.mean(np.abs(residual_um))),surface_median_abs_um=float(np.median(np.abs(residual_um))),surface_max_abs_um=float(np.max(np.abs(residual_um))),roi_total=len(fits),roi_valid=focus_valid_count,roi_surface_inliers=surface_inlier_count,roi_rejected_focus=len(fits)-focus_valid_count,roi_rejected_spatial=focus_valid_count-len(selected),roi_rejected_surface=len(selected)-surface_inlier_count,roi_robust_outliers=len(selected)-surface_inlier_count,x_span_fraction=inlier_observable.coverage_x_fraction,y_span_fraction=inlier_observable.coverage_y_fraction,tilt_x_detectable=abs(tx)>=lx,tilt_y_detectable=abs(ty)>=ly,within_tolerance_x=abs(tx)<=self.config.tolerance_x_deg,within_tolerance_y=abs(ty)<=self.config.tolerance_y_deg,resolution_limited_x=abs(tx)<lx,resolution_limited_y=abs(ty)<ly,decision_x=_decision(tx,lx,self.config.tolerance_x_deg),decision_y=_decision(ty,ly,self.config.tolerance_y_deg),mean_peak_uncertainty_um=float(np.mean(finite_u)) if finite_u.size else math.nan,median_peak_uncertainty_um=float(np.median(finite_u)) if finite_u.size else math.nan,surface_model="quadratic" if quadratic else "plane",surface_coefficients=[float(v) for v in c],reference_applied=reference_applied,roi_fits=fits,target_bbox_normalized=support.bbox_normalized,target_coverage_fraction=support.coverage_fraction,baseline_x_mm=inlier_observable.baseline_x_mm,baseline_y_mm=inlier_observable.baseline_y_mm,candidate_roi_count=len(fits),structurally_valid_candidate_count=structural_count,selected_roi_count=len(selected),focus_valid_roi_count=focus_valid_count,surface_inlier_count=surface_inlier_count,design_condition_number=inlier_observable.condition_number)

    def _fit_roi(self,index,z,curve,contrast,sparse_contrast,black,saturated,structured,gradient_quantile,gradient_snr,edge_pixels,edge_span,means,stds,cvs,half_window,shape):
        x0,y0,x1,y1=self._pixel_rois[index]; peak_i=int(np.argmax(curve))
        h,w=shape; xpx=(x0+x1)/2; ypx=(y0+y1)/2
        dense_structure=structured>=self.config.minimum_structured_pixel_fraction
        sparse_structure=(gradient_snr>=self.config.minimum_gradient_snr)&(edge_pixels>=self.config.minimum_connected_edge_pixels)&(edge_span>=self.config.minimum_connected_edge_span_fraction)
        contrast_ok=(contrast>=self.config.min_contrast)|(sparse_contrast>=self.config.min_contrast)
        energy_ok=(curve>=self.config.min_gradient_energy)|(gradient_quantile>=self.config.min_gradient_energy)
        structural_positions=(dense_structure|sparse_structure)&contrast_ok&energy_ok
        sparse_valid=bool(np.any(sparse_structure&contrast_ok&energy_ok))
        base=dict(index=index,x_px=xpx,y_px=ypx,x0_px=x0,y0_px=y0,x1_px=x1,y1_px=y1,x_mm=(xpx-w/2)*self.config.object_um_per_pixel/1000,y_mm=(ypx-h/2)*self.config.object_um_per_pixel/1000,peak_fit_method=self.config.peak_fit_method,discrete_peak_z_mm=float(z[peak_i]),frame_score_mean=float(means[peak_i]),frame_score_std=float(stds[peak_i]),frame_score_cv=float(cvs[peak_i]),local_contrast=float(np.max(contrast)),sparse_contrast=float(np.max(sparse_contrast)),structured_pixel_fraction=float(np.max(structured)),gradient_energy_quantile=float(np.max(gradient_quantile)),gradient_snr=float(np.max(gradient_snr)),connected_edge_pixels=int(np.max(edge_pixels)),connected_edge_span_fraction=float(np.max(edge_span)),sparse_edge_valid=sparse_valid,curve_z_mm=z.tolist(),curve_values=curve.tolist())
        if self.config.roi_selection_mode=="manual_bbox":
            xmin,ymin,xmax,ymax=self.config.manual_target_bbox; roi=self.rois[index]
            if roi.x0<xmin-1e-9 or roi.y0<ymin-1e-9 or roi.x1>xmax+1e-9 or roi.y1>ymax+1e-9:
                return RoiFocusFit(valid=False,reason="outside_manual_target",**base)
        if float(black[peak_i])>self.config.max_black_fraction: return RoiFocusFit(valid=False,reason="mostly_black",**base)
        if float(saturated[peak_i])>self.config.max_saturated_fraction: return RoiFocusFit(valid=False,reason="mostly_saturated",**base)
        if not np.any(contrast_ok): return RoiFocusFit(valid=False,reason="insufficient_contrast",**base)
        if not np.any(structural_positions): return RoiFocusFit(valid=False,reason="insufficient_structure",**base)
        base["structurally_valid"]=True
        if float(cvs[peak_i])>self.config.max_frame_cv: return RoiFocusFit(valid=False,reason="unstable_frames",**base)
        if peak_i in {0,len(z)-1}: return RoiFocusFit(valid=False,reason="peak_outside_scan",**base)
        peak=fit_focus_peak(z,curve,method=self.config.peak_fit_method,half_window=half_window)
        fields=dict(focus_z_mm=peak.z_peak_mm,focus_uncertainty_mm=peak.uncertainty_mm,peak_value=peak.peak_value,peak_width_mm=peak.width_mm,peak_prominence=peak.prominence,curvature=peak.curvature,fit_r2=peak.fit_r2,fit_rmse=peak.fit_rmse,local_fit_z_mm=peak.local_z_mm.tolist(),local_fit_values=peak.local_predicted.tolist())
        if not peak.valid: return RoiFocusFit(valid=False,reason="peak_outside_scan" if peak.reject_reason=="peak_at_scan_boundary" else "non_concave_peak",**base,**fields)
        if peak.prominence<self.config.min_peak_prominence: return RoiFocusFit(valid=False,reason="weak_peak",**base,**fields)
        if peak.curvature<self.config.min_peak_curvature: return RoiFocusFit(valid=False,reason="non_concave_peak",**base,**fields)
        if peak.fit_r2<self.config.min_fit_r2: return RoiFocusFit(valid=False,reason="poor_peak_fit",**base,**fields)
        if np.isfinite(peak.uncertainty_mm) and peak.uncertainty_mm*1000>self.config.max_peak_uncertainty_um: return RoiFocusFit(valid=False,reason="excessive_focus_uncertainty",**base,**fields)
        quality=self._quality_weight(peak,float(cvs[peak_i]),float(np.max(structured)))
        return RoiFocusFit(valid=True,reason="ok",quality_score=quality,**base,**fields)

    def _quality_weight(self,peak,frame_cv,structure_fraction):
        sigma_um=peak.uncertainty_mm*1000 if np.isfinite(peak.uncertainty_mm) else self.config.weight_sigma_ceiling_um
        sigma_um=float(np.clip(sigma_um,self.config.weight_sigma_floor_um,self.config.weight_sigma_ceiling_um))
        uncertainty=1.0/(sigma_um*sigma_um)
        prominence=np.clip(peak.prominence/max(self.config.min_peak_prominence,1e-9),0.25,4.0)
        fit_quality=np.clip((peak.fit_r2-self.config.min_fit_r2)/max(1-self.config.min_fit_r2,1e-9),0.1,1.0)
        curvature=np.clip(peak.curvature/max(self.config.min_peak_curvature,1e-12),0.25,4.0)
        stability=np.clip(1-frame_cv/max(self.config.max_frame_cv,1e-9),0.1,1.0)
        structure=np.clip(structure_fraction/max(self.config.minimum_structured_pixel_fraction,1e-9),0.25,4.0)
        weight=uncertainty*prominence*fit_quality*math.sqrt(curvature)*stability*math.sqrt(structure)
        return float(max(weight,1e-18))

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

    def _failure(self,status,message,roi_fits=None,selected_count=0,x_span=0.,y_span=0.,*,target_bbox=(math.nan,math.nan,math.nan,math.nan),target_coverage=0.,structural_count=0,observable=None,surface_evaluated=False):
        fits=roi_fits or []
        focus_valid=sum(fit.valid for fit in fits)
        surface_inliers=sum(fit.surface_inlier for fit in fits) if surface_evaluated else 0
        rejected_surface=max(0,selected_count-surface_inliers) if surface_evaluated else 0
        return TiltEstimate(status=status,status_message=message,roi_total=len(self.rois),roi_valid=focus_valid,roi_surface_inliers=surface_inliers,roi_rejected_focus=len(self.rois)-focus_valid,roi_rejected_spatial=max(0,focus_valid-selected_count),roi_rejected_surface=rejected_surface,roi_robust_outliers=rejected_surface,x_span_fraction=x_span,y_span_fraction=y_span,roi_fits=fits,target_bbox_normalized=tuple(target_bbox),target_coverage_fraction=target_coverage,baseline_x_mm=observable.baseline_x_mm if observable else 0.,baseline_y_mm=observable.baseline_y_mm if observable else 0.,candidate_roi_count=len(self.rois),structurally_valid_candidate_count=structural_count,selected_roi_count=selected_count,focus_valid_roi_count=focus_valid,surface_inlier_count=surface_inliers,design_condition_number=observable.condition_number if observable else math.inf)


def _focus_map(gray, metric):
    """Build one float32 focus map while keeping at most two Sobel arrays live."""
    if metric == "tenengrad":
        energy = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        other = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        cv2.multiply(energy, energy, dst=energy)
        cv2.multiply(other, other, dst=other)
        cv2.add(energy, other, dst=energy)
        del other
        return energy
    if metric == "modified_laplacian":
        energy = cv2.Sobel(gray, cv2.CV_32F, 2, 0, ksize=3)
        other = cv2.Sobel(gray, cv2.CV_32F, 0, 2, ksize=3)
        np.abs(energy, out=energy)
        np.abs(other, out=other)
        cv2.add(energy, other, dst=energy)
        del other
        return energy
    if metric == "variance_laplacian":
        return cv2.Laplacian(gray, cv2.CV_32F, ksize=3)
    raise ValueError(f"unsupported focus metric '{metric}'")


def _focus_maps(gray, metrics):
    """Compatibility helper; the estimator itself processes maps sequentially."""
    return {metric: _focus_map(gray, metric) for metric in metrics}


def _analysis_image(gray, maximum_dimension):
    scale = min(1.0, float(maximum_dimension) / max(gray.shape))
    if scale >= 1.0:
        return gray
    width = max(1, int(round(gray.shape[1] * scale)))
    height = max(1, int(round(gray.shape[0] * scale)))
    return cv2.resize(gray, (width, height), interpolation=cv2.INTER_AREA)


def _scale_roi(pixel_roi, source_shape, target_shape):
    x0,y0,x1,y1=pixel_roi
    sy=target_shape[0]/source_shape[0]; sx=target_shape[1]/source_shape[1]
    ax0=max(0,min(target_shape[1]-1,int(math.floor(x0*sx))))
    ay0=max(0,min(target_shape[0]-1,int(math.floor(y0*sy))))
    ax1=max(ax0+1,min(target_shape[1],int(math.ceil(x1*sx))))
    ay1=max(ay0+1,min(target_shape[0],int(math.ceil(y1*sy))))
    return ax0,ay0,ax1,ay1


def _bounded_sample(array, maximum_values):
    step=max(1,int(math.ceil(math.sqrt(array.size/max(float(maximum_values),1.0)))))
    return np.ravel(array[::step,::step]).astype(np.float32,copy=False)


def _candidate_image_metrics(gray, energy, pixel_roi, significant_threshold, *,
                             structure_quantile, sparse_contrast_quantile,
                             sparse_energy_quantile):
    x0,y0,x1,y1=pixel_roi
    intensity=gray[y0:y1,x0:x1]
    gradient=energy[y0:y1,x0:x1]
    intensity_sample=_bounded_sample(intensity,16384)
    gradient_sample=_bounded_sample(gradient,16384)
    p01,p99=np.quantile(intensity_sample,(.01,.99))
    tail=1.0-sparse_contrast_quantile
    sparse_low,sparse_high=np.quantile(intensity_sample,(tail,sparse_contrast_quantile))
    noise_floor=float(np.median(gradient_sample))
    noise_deviation=np.abs(gradient_sample-np.float32(noise_floor))
    noise_mad=float(np.median(noise_deviation))
    del noise_deviation
    top_energy=float(np.quantile(gradient_sample,sparse_energy_quantile))
    gradient_snr=max(0.0,top_energy-noise_floor)/max(1.4826*noise_mad,1.0e-12)
    structure_mask=np.asarray(gradient>=significant_threshold,dtype=np.uint8)
    structured_fraction=float(np.count_nonzero(structure_mask))/max(structure_mask.size,1)
    component_pixels=0; component_span=0.0
    if np.count_nonzero(structure_mask)>=2:
        structure_mask=cv2.morphologyEx(structure_mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
        count,_,stats,_=cv2.connectedComponentsWithStats(structure_mask,connectivity=8)
        if count>1:
            label=int(np.argmax(stats[1:,cv2.CC_STAT_AREA]))+1
            component_pixels=int(stats[label,cv2.CC_STAT_AREA])
            component_span=max(
                float(stats[label,cv2.CC_STAT_WIDTH])/max(structure_mask.shape[1],1),
                float(stats[label,cv2.CC_STAT_HEIGHT])/max(structure_mask.shape[0],1),
            )
    return {
        "contrast":float(p99-p01),
        "sparse_contrast":float(sparse_high-sparse_low),
        "black_fraction":float(np.count_nonzero(intensity<=.005))/max(intensity.size,1),
        "saturated_fraction":float(np.count_nonzero(intensity>=.995))/max(intensity.size,1),
        "structured_fraction":structured_fraction,
        "gradient_quantile":float(np.quantile(gradient_sample,structure_quantile)),
        "gradient_snr":float(gradient_snr),
        "connected_edge_pixels":component_pixels,
        "connected_edge_span_fraction":float(component_span),
    }


def _roi_focus_score(focus_map,pixel_roi,metric):
    x0,y0,x1,y1=pixel_roi
    crop=focus_map[y0:y1,x0:x1]
    if metric=="variance_laplacian":
        return float(np.var(crop,dtype=np.float64))
    return float(np.sum(crop,dtype=np.float64)/max(crop.size,1))


def _decision(angle,limit95,tolerance):
    low,high=angle-limit95,angle+limit95
    if low>=-tolerance and high<=tolerance: return "PASS"
    if low>tolerance or high<-tolerance: return "FAIL"
    return "INCONCLUSIVE"


def _robust_huber_fit(design,values,*,max_iterations=30,huber_k=1.345):
    """Compatibility wrapper for the original public test helper."""
    fit=fit_surface(design,values,robust=True,huber_k=huber_k,max_iterations=max_iterations)
    return fit.coefficients,fit.covariance,fit.residuals
