"""Linear raw-intensity measurements shared by exposure and measurement runs."""

from __future__ import annotations

import re

import numpy as np


SUPPORTED_SENSOR_BITS = {8, 10, 12, 14, 16}


def native_max_value(pixel_format: str, image: np.ndarray) -> float:
    """Resolve native sensor maximum, including left-aligned integer containers."""
    match = re.search(r"(?:mono|bayer[a-z]*)(8|10|12|14|16)", str(pixel_format), re.I)
    if match:
        bits = int(match.group(1))
        if bits in SUPPORTED_SENSOR_BITS:
            native_max = (1 << bits) - 1
            if np.issubdtype(image.dtype, np.integer):
                container_bits = int(np.iinfo(image.dtype).bits)
                shift = container_bits - bits
                if shift > 0:
                    values = image.reshape(-1)
                    nonzero = values[values != 0]
                    looks_left_aligned = (
                        nonzero.size > 0
                        # Values above the native code range are an
                        # unambiguous left-alignment signal. Merely observing
                        # zero low bits is not: valid right-aligned scenes can
                        # contain only multiples of 2**shift.
                        and int(np.max(nonzero)) > native_max
                    )
                    if looks_left_aligned:
                        return float(native_max << shift)
            return float(native_max)
    if np.issubdtype(image.dtype, np.integer):
        return float(np.iinfo(image.dtype).max)
    return 1.0


def clip_roi(
    image: np.ndarray,
    roi: tuple[int, int, int, int] | None,
) -> tuple[np.ndarray, tuple[int, int]]:
    """Return a valid crop and its absolute image origin."""
    if image is None or image.size == 0:
        raise ValueError("empty camera frame")
    if roi is None:
        return image, (0, 0)
    x, y, width, height = (int(value) for value in roi)
    image_height, image_width = image.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(image_width, x + width), min(image_height, y + height)
    if width <= 0 or height <= 0 or x1 <= x0 or y1 <= y0:
        raise ValueError("ROI does not overlap the camera image")
    return image[y0:y1, x0:x1], (x0, y0)


def analysis_plane(
    image: np.ndarray,
    roi: tuple[int, int, int, int] | None,
    *,
    pixel_format: str,
) -> np.ndarray:
    """Return a 2-D linear plane; Bayer RGGB uses only native green sensels."""
    cropped, (origin_x, origin_y) = clip_roi(image, roi)
    if cropped.ndim == 3:
        channel = 1 if cropped.shape[2] >= 2 else 0
        return cropped[:, :, channel].astype(np.float64, copy=False)

    if "bayer" not in str(pixel_format).lower():
        return cropped.astype(np.float64, copy=False)

    # Restrict to complete absolute 2x2 RGGB cells and pack G1/G2 into one
    # half-height plane. Every native green sensel remains an independent
    # sample; red and blue values never enter exposure statistics.
    row_start = origin_y & 1
    col_start = origin_x & 1
    usable = cropped[row_start:, col_start:]
    height = usable.shape[0] - usable.shape[0] % 2
    width = usable.shape[1] - usable.shape[1] % 2
    usable = usable[:height, :width]
    if height < 2 or width < 2:
        raise ValueError("Bayer ROI contains no complete RGGB cell")
    green_plane = np.empty((height // 2, width), dtype=np.float64)
    green_plane[:, 0::2] = usable[0::2, 1::2]
    green_plane[:, 1::2] = usable[1::2, 0::2]
    return green_plane


def analysis_values(
    image: np.ndarray,
    roi: tuple[int, int, int, int] | None,
    *,
    pixel_format: str,
) -> np.ndarray:
    """Return flattened linear intensity samples."""
    return analysis_plane(image, roi, pixel_format=pixel_format).reshape(-1)


def _otsu_threshold(values: np.ndarray, maximum: float) -> float | None:
    """Compute an Otsu threshold without converting scientific data in-place."""
    if values.size < 2 or maximum <= 0:
        return None
    scaled = np.clip(np.rint(values * 255.0 / maximum), 0, 255).astype(np.uint8)
    histogram = np.bincount(scaled.reshape(-1), minlength=256).astype(np.float64)
    if np.count_nonzero(histogram) < 2:
        return None
    probabilities = histogram / histogram.sum()
    cumulative_weight = np.cumsum(probabilities)
    cumulative_mean = np.cumsum(probabilities * np.arange(256, dtype=np.float64))
    total_mean = cumulative_mean[-1]
    denominator = cumulative_weight * (1.0 - cumulative_weight)
    variance = np.zeros(256, dtype=np.float64)
    valid = denominator > 0
    variance[valid] = (
        (total_mean * cumulative_weight[valid] - cumulative_mean[valid]) ** 2
        / denominator[valid]
    )
    return float(np.argmax(variance)) * maximum / 255.0


def _erode_once(mask: np.ndarray) -> np.ndarray:
    """Binary 3x3 erosion with a false border."""
    padded = np.pad(np.asarray(mask, dtype=bool), 1, mode="constant")
    return np.logical_and.reduce(
        [padded[y : y + mask.shape[0], x : x + mask.shape[1]] for y in range(3) for x in range(3)]
    )


def measure_intensity(
    image: np.ndarray,
    roi: tuple[int, int, int, int] | None,
    *,
    pixel_format: str,
    saturation_threshold_fraction: float = 0.98,
    clipping_level_fraction: float = 0.95,
    max_saturated_fraction: float = 0.001,
) -> dict[str, float | str | bool]:
    """Measure robust black/white plateaus and clipping on one linear frame."""
    maximum = native_max_value(pixel_format, image)
    plane = analysis_plane(image, roi, pixel_format=pixel_format)
    values = plane.reshape(-1)
    if values.size == 0:
        raise ValueError("ROI contains no usable pixels")

    p5 = float(np.percentile(values, 5.0))
    p95 = float(np.percentile(values, 95.0))
    p99_9 = float(np.percentile(values, 99.9))
    saturation_fraction = float(
        np.mean(values >= float(saturation_threshold_fraction) * maximum)
    )

    method = "p95_fallback"
    white_level, black_level = p95, p5
    threshold = _otsu_threshold(values, maximum)
    if threshold is not None:
        white_mask = _erode_once(plane > threshold)
        black_mask = _erode_once(plane <= threshold)
        minimum_count = max(64, int(np.ceil(0.01 * values.size)))
        if np.count_nonzero(white_mask) >= minimum_count and np.count_nonzero(black_mask) >= minimum_count:
            candidate_white = float(np.median(plane[white_mask]))
            candidate_black = float(np.median(plane[black_mask]))
            if candidate_white - candidate_black >= 0.05 * maximum:
                white_level, black_level = candidate_white, candidate_black
                method = "segmented_plateau_median"

    white_norm = white_level / maximum
    black_norm = black_level / maximum
    p95_norm = p95 / maximum
    p99_9_norm = p99_9 / maximum
    clipping = (
        p99_9_norm >= float(clipping_level_fraction)
        or saturation_fraction > float(max_saturated_fraction)
    )
    return {
        "white_level": white_level,
        "white_level_norm": white_norm,
        "black_level": black_level,
        "black_level_norm": black_norm,
        "p95": p95,
        "p95_norm": p95_norm,
        "p99_9": p99_9,
        "p99_9_norm": p99_9_norm,
        "saturation_fraction": saturation_fraction,
        "native_max": maximum,
        "intensity_method": method,
        "clipping_detected": bool(clipping),
    }


def aggregate_intensity(rows: list[dict[str, object]]) -> dict[str, object]:
    """Median-combine per-frame intensity diagnostics."""
    if not rows:
        raise ValueError("no intensity measurements")
    numeric = (
        "white_level",
        "white_level_norm",
        "black_level",
        "black_level_norm",
        "p95",
        "p95_norm",
        "p99_9",
        "p99_9_norm",
        "saturation_fraction",
        "native_max",
    )
    result: dict[str, object] = {
        key: float(np.median([float(row[key]) for row in rows])) for key in numeric
    }
    methods = [str(row.get("intensity_method", "p95_fallback")) for row in rows]
    result["intensity_method"] = (
        "segmented_plateau_median"
        if methods.count("segmented_plateau_median") > len(methods) / 2
        else "p95_fallback"
    )
    result["clipping_detected"] = any(bool(row.get("clipping_detected")) for row in rows)
    return result


def exposure_ratio(
    diagnostics: dict[str, object],
    target_white_norm: float,
    *,
    minimum_signal_fraction: float = 1.0e-6,
) -> float:
    """Return the damped, bounded exposure multiplier for one measurement."""
    white = float(diagnostics["white_level_norm"])
    black = float(diagnostics["black_level_norm"])
    numerator = max(float(target_white_norm) - black, minimum_signal_fraction)
    denominator = max(white - black, minimum_signal_fraction)
    ratio = float(np.clip(numerator / denominator, 0.5, 2.0)) ** 0.7
    if bool(diagnostics.get("clipping_detected")):
        ratio = min(ratio, 0.8)
    return ratio
