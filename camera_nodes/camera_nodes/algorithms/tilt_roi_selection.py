"""Pattern-independent candidate ROI support detection and spatial selection."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import cv2
import numpy as np


SUPPORTED_SELECTION_MODES = ("fixed_grid", "manual_bbox", "auto_texture")


@dataclass(frozen=True)
class SupportRegion:
    valid: bool
    bbox_normalized: tuple[float, float, float, float]
    coverage_fraction: float
    member_indices: frozenset[int]


@dataclass(frozen=True)
class Observability:
    valid: bool
    baseline_x_mm: float
    baseline_y_mm: float
    coverage_x_fraction: float
    coverage_y_fraction: float
    bins_x: int
    bins_y: int
    quadrants: int
    condition_number: float
    spatial_aspect_ratio: float


def validate_bbox(bbox: Sequence[float]) -> tuple[float, float, float, float]:
    if len(bbox) != 4:
        raise ValueError("manual_target_bbox must contain [xmin, ymin, xmax, ymax]")
    xmin, ymin, xmax, ymax = (float(value) for value in bbox)
    if not all(math.isfinite(value) for value in (xmin, ymin, xmax, ymax)):
        raise ValueError("manual_target_bbox values must be finite")
    if not (0.0 <= xmin < xmax <= 1.0 and 0.0 <= ymin < ymax <= 1.0):
        raise ValueError("manual_target_bbox must satisfy 0 <= min < max <= 1")
    return xmin, ymin, xmax, ymax


def make_overlapping_rois(
    roi_width_fraction: float,
    roi_height_fraction: float,
    step_x_fraction: float,
    step_y_fraction: float,
    *,
    bbox: Sequence[float] = (0.0, 0.0, 1.0, 1.0),
):
    """Return normalized overlapping ROIs and their deterministic grid shape."""
    xmin, ymin, xmax, ymax = validate_bbox(bbox)
    if not (0.0 < roi_width_fraction <= xmax - xmin):
        raise ValueError("candidate_roi_width_fraction does not fit target bbox")
    if not (0.0 < roi_height_fraction <= ymax - ymin):
        raise ValueError("candidate_roi_height_fraction does not fit target bbox")
    if step_x_fraction <= 0.0 or step_y_fraction <= 0.0:
        raise ValueError("candidate ROI steps must be positive")

    xs = _centers(xmin, xmax, roi_width_fraction, step_x_fraction)
    ys = _centers(ymin, ymax, roi_height_fraction, step_y_fraction)
    # Imported lazily to avoid a circular dependency at module import time.
    from .target_tilt import NormalizedRoi
    rois = [
        NormalizedRoi(
            x - roi_width_fraction / 2.0,
            y - roi_height_fraction / 2.0,
            x + roi_width_fraction / 2.0,
            y + roi_height_fraction / 2.0,
        )
        for y in ys
        for x in xs
    ]
    return rois, (len(ys), len(xs))


def _centers(start: float, stop: float, size: float, step: float) -> list[float]:
    first = start + size / 2.0
    last = stop - size / 2.0
    if first > last:
        return []
    count = int(math.floor((last - first) / step + 1.0e-9)) + 1
    values = [first + index * step for index in range(count)]
    if last - values[-1] > step * 0.25:
        values.append(last)
    return values


def detect_support(fits, image_shape, *, mode: str, manual_bbox, closing_radius: int = 1):
    """Remove isolated candidates and return target-relative support geometry."""
    height, width = image_shape
    if mode == "fixed_grid":
        members = frozenset(fit.index for fit in fits if fit.structurally_valid)
        return SupportRegion(bool(members), (0.0, 0.0, 1.0, 1.0), 1.0, members)
    if mode == "manual_bbox":
        bbox = validate_bbox(manual_bbox)
        members = frozenset(fit.index for fit in fits if fit.structurally_valid)
        return SupportRegion(bool(members), bbox, len(members) / max(len(fits), 1), members)

    candidates = [fit for fit in fits if fit.structurally_valid]
    if not candidates:
        return SupportRegion(False, (0.0, 0.0, 0.0, 0.0), 0.0, frozenset())
    xs = sorted(set(round(fit.x_px, 6) for fit in fits))
    ys = sorted(set(round(fit.y_px, 6) for fit in fits))
    x_lookup = {value: index for index, value in enumerate(xs)}
    y_lookup = {value: index for index, value in enumerate(ys)}
    mask = np.zeros((len(ys), len(xs)), dtype=np.uint8)
    index_at = {}
    for fit in candidates:
        gx = x_lookup[round(fit.x_px, 6)]
        gy = y_lookup[round(fit.y_px, 6)]
        mask[gy, gx] = 1
        index_at[(gy, gx)] = fit.index
    radius = max(0, int(closing_radius))
    cleaned = mask
    if radius:
        kernel = np.ones((2 * radius + 1, 2 * radius + 1), np.uint8)
        cleaned = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(cleaned, connectivity=8)
    if count <= 1:
        return SupportRegion(False, (0.0, 0.0, 0.0, 0.0), 0.0, frozenset())
    component_sizes = stats[1:, cv2.CC_STAT_AREA]
    largest_label = int(np.argmax(component_sizes)) + 1
    largest_stats = stats[largest_label]
    lx, ly, lw, lh = (int(value) for value in largest_stats[:4])
    accepted_labels = {largest_label}
    # Inner components of ring targets are retained when their centre lies in
    # the principal component's bounding box. Tiny exterior islands are not.
    for label in range(1, count):
        if label == largest_label:
            continue
        x, y, w, h, area = (int(value) for value in stats[label])
        cx, cy = x + w / 2.0, y + h / 2.0
        if area >= 2 and lx - 1 <= cx <= lx + lw and ly - 1 <= cy <= ly + lh:
            accepted_labels.add(label)
    members = {
        candidate.index
        for candidate in candidates
        if labels[
            y_lookup[round(candidate.y_px, 6)],
            x_lookup[round(candidate.x_px, 6)],
        ] in accepted_labels
    }
    if not members:
        return SupportRegion(False, (0.0, 0.0, 0.0, 0.0), 0.0, frozenset())
    member_fits = [fit for fit in fits if fit.index in members]
    half_width = np.median([(fit.x1_px - fit.x0_px) / 2.0 for fit in member_fits])
    half_height = np.median([(fit.y1_px - fit.y0_px) / 2.0 for fit in member_fits])
    xmin = max(0.0, (min(fit.x_px for fit in member_fits) - half_width) / width)
    xmax = min(1.0, (max(fit.x_px for fit in member_fits) + half_width) / width)
    ymin = max(0.0, (min(fit.y_px for fit in member_fits) - half_height) / height)
    ymax = min(1.0, (max(fit.y_px for fit in member_fits) + half_height) / height)
    bbox = (xmin, ymin, xmax, ymax)
    return SupportRegion(True, bbox, len(members) / max(len(fits), 1), frozenset(members))


def select_spatially_distributed(fits, support: SupportRegion, image_shape,
                                 maximum_selected: int, *, minimum_bins_x=3,
                                 minimum_bins_y=3):
    """Guarantee a spatial skeleton, then fill it by quality and distance."""
    height, width = image_shape
    eligible = [fit for fit in fits if fit.valid and fit.index in support.member_indices]
    if not eligible:
        return []
    xmin, ymin, xmax, ymax = support.bbox_normalized
    bins_x=max(1,int(minimum_bins_x)); bins_y=max(1,int(minimum_bins_y))
    normalized={}
    bin_winners={}
    for fit in eligible:
        nx=float(np.clip((fit.x_px/width-xmin)/max(xmax-xmin,1.0e-12),0.0,1.0))
        ny=float(np.clip((fit.y_px/height-ymin)/max(ymax-ymin,1.0e-12),0.0,1.0))
        normalized[fit.index]=(nx,ny)
        bx = min(bins_x - 1, max(0, int(nx * bins_x)))
        by = min(bins_y - 1, max(0, int(ny * bins_y)))
        fit.target_bin = f"{bx},{by}"
        key = (bx, by)
        previous = bin_winners.get(key)
        if previous is None or (-fit.quality_score, fit.index) < (-previous.quality_score, previous.index):
            bin_winners[key] = fit

    selected=[]; selected_indices=set()
    def add(candidate):
        if candidate is not None and candidate.index not in selected_indices and len(selected)<maximum_selected:
            selected.append(candidate); selected_indices.add(candidate.index)

    def best_at_extreme(axis, choose_min):
        position=lambda fit: normalized[fit.index][axis]
        extreme=(min if choose_min else max)(position(fit) for fit in eligible)
        candidates=[fit for fit in eligible if abs(position(fit)-extreme)<1.0e-9]
        return min(candidates,key=lambda fit:(-fit.quality_score,fit.index))

    # Preserve the physical baseline before any global quality ranking.
    for candidate in (
        best_at_extreme(0,True),best_at_extreme(0,False),
        best_at_extreme(1,True),best_at_extreme(1,False),
    ):
        add(candidate)

    # Preserve all available target quadrants.
    for qx,qy in ((False,False),(True,False),(False,True),(True,True)):
        candidates=[fit for fit in eligible if (normalized[fit.index][0]>=.5)==qx and (normalized[fit.index][1]>=.5)==qy]
        if candidates:
            add(min(candidates,key=lambda fit:(-fit.quality_score,fit.index)))

    def distance_to_selection(candidate):
        if not selected: return math.inf
        x,y=normalized[candidate.index]
        return min(math.hypot(x-normalized[chosen.index][0],y-normalized[chosen.index][1]) for chosen in selected)

    # Add one quality winner from each required coarse bin. When capacity is
    # tight, farthest bins win instead of globally strongest central bins.
    remaining_bins=[fit for fit in bin_winners.values() if fit.index not in selected_indices]
    while remaining_bins and len(selected)<maximum_selected:
        candidate=min(remaining_bins,key=lambda fit:(-distance_to_selection(fit),-fit.quality_score,fit.index))
        add(candidate); remaining_bins.remove(candidate)

    qualities=np.asarray([max(float(fit.quality_score),1.0e-18) for fit in eligible])
    log_quality=np.log(qualities); qmin=float(np.min(log_quality)); qspan=max(float(np.ptp(log_quality)),1.0e-12)
    quality_unit={fit.index:float((value-qmin)/qspan) for fit,value in zip(eligible,log_quality)}
    remaining=[fit for fit in eligible if fit.index not in selected_indices]
    while remaining and len(selected)<maximum_selected:
        candidate=min(
            remaining,
            key=lambda fit:(
                -(0.70*distance_to_selection(fit)/math.sqrt(2.0)+0.30*quality_unit[fit.index]),
                -fit.quality_score,
                fit.index,
            ),
        )
        add(candidate); remaining.remove(candidate)

    selected_indices = {fit.index for fit in selected}
    for fit in eligible:
        fit.selected = fit.index in selected_indices
        if not fit.selected:
            fit.reason = "spatially_redundant"
        if selected:
            fit.nearest_selected_distance_px = min(
                math.hypot(fit.x_px - chosen.x_px, fit.y_px - chosen.y_px)
                for chosen in selected if chosen.index != fit.index
            ) if len(selected) > 1 else math.inf
    return sorted(selected, key=lambda fit: fit.index)


def check_observability(fits, support, image_shape, object_um_per_pixel, *,
                        minimum_baseline_x_mm, minimum_baseline_y_mm,
                        minimum_bins_x, minimum_bins_y, minimum_quadrants,
                        maximum_condition):
    if not fits:
        return Observability(False, 0.0, 0.0, 0.0, 0.0, 0, 0, 0, math.inf, 0.0)
    height, width = image_shape
    xs = np.asarray([fit.x_px for fit in fits]); ys = np.asarray([fit.y_px for fit in fits])
    baseline_x = float(np.ptp(xs) * object_um_per_pixel / 1000.0)
    baseline_y = float(np.ptp(ys) * object_um_per_pixel / 1000.0)
    xmin, ymin, xmax, ymax = support.bbox_normalized
    support_width = max((xmax - xmin) * width, 1.0)
    support_height = max((ymax - ymin) * height, 1.0)
    coverage_x = float(np.ptp(xs) / support_width)
    coverage_y = float(np.ptp(ys) / support_height)
    normalized_x = (xs / width - xmin) / max(xmax - xmin, 1.0e-12)
    normalized_y = (ys / height - ymin) / max(ymax - ymin, 1.0e-12)
    bx = np.clip((normalized_x * minimum_bins_x).astype(int), 0, minimum_bins_x - 1)
    by = np.clip((normalized_y * minimum_bins_y).astype(int), 0, minimum_bins_y - 1)
    occupied_x, occupied_y = len(set(bx.tolist())), len(set(by.tolist()))
    quadrants = len({(x >= 0.5, y >= 0.5) for x, y in zip(normalized_x, normalized_y)})
    xmm = (xs - width / 2.0) * object_um_per_pixel / 1000.0
    ymm = (ys - height / 2.0) * object_um_per_pixel / 1000.0
    design = np.column_stack((np.ones(len(fits)), xmm, ymm))
    scaled = design.copy()
    scaled[:, 1] /= max(np.std(xmm), 1.0e-12)
    scaled[:, 2] /= max(np.std(ymm), 1.0e-12)
    condition = float(np.linalg.cond(scaled))
    covariance = np.cov(np.column_stack((xmm, ymm)), rowvar=False)
    eigenvalues = np.linalg.eigvalsh(covariance) if len(fits) > 1 else np.asarray([0.0, 0.0])
    aspect_ratio = float(eigenvalues[0] / max(eigenvalues[-1], 1.0e-18))
    valid = (
        len(fits) >= 3
        and baseline_x >= minimum_baseline_x_mm
        and baseline_y >= minimum_baseline_y_mm
        and occupied_x >= minimum_bins_x
        and occupied_y >= minimum_bins_y
        and quadrants >= minimum_quadrants
        and np.linalg.matrix_rank(scaled) >= 3
        and math.isfinite(condition)
        and condition <= maximum_condition
        and aspect_ratio > 1.0e-4
    )
    return Observability(valid, baseline_x, baseline_y, coverage_x, coverage_y,
                         occupied_x, occupied_y, quadrants, condition, aspect_ratio)


def _bbox_area(bbox):
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])
