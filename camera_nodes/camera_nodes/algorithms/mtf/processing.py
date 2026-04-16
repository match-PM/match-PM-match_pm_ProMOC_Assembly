"""Core signal processing helpers for MTF."""

from typing import Optional, Tuple
import numpy as np
import cv2

from .config import MTFConfig


def compute_esf(roi: np.ndarray, edge_angle: float, oversample_factor: int) -> np.ndarray:
    """Compute ESF by projection along the edge."""
    h, w = roi.shape
    angle_rad = np.radians(edge_angle)

    # Step 1: Project every pixel onto the axis perpendicular to the edge.
    esf_points = []
    for row in range(h):
        offset = row * np.tan(angle_rad)
        for col in range(w):
            pos = (col - w / 2 - offset) * oversample_factor
            esf_points.append((pos, roi[row, col]))

    # Step 2: Sort projected samples and average them into ESF bins.
    esf_points.sort(key=lambda x: x[0])
    positions = np.array([p[0] for p in esf_points])
    values = np.array([p[1] for p in esf_points])

    bin_edges = np.arange(positions.min(), positions.max(), 1)
    bin_indices = np.digitize(positions, bin_edges)

    esf = []
    for i in range(1, len(bin_edges)):
        mask = bin_indices == i
        if np.sum(mask) > 0:
            esf.append(np.mean(values[mask]))

    return np.array(esf)


def extract_rggb_green_samples(roi: np.ndarray) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Extract G1/G2 samples and their coordinates from an RGGB Bayer ROI."""
    if roi.ndim != 2:
        raise ValueError("RGGB raw ROI must be a 2D array")

    roi_f = roi.astype(np.float64)

    g1_values = roi_f[0::2, 1::2]
    g2_values = roi_f[1::2, 0::2]

    g1_rows, g1_cols = np.indices(g1_values.shape, dtype=np.float64)
    g2_rows, g2_cols = np.indices(g2_values.shape, dtype=np.float64)

    g1_x = (2.0 * g1_cols + 1.0).ravel()
    g1_y = (2.0 * g1_rows).ravel()
    g2_x = (2.0 * g2_cols).ravel()
    g2_y = (2.0 * g2_rows + 1.0).ravel()

    return {
        "g1": (g1_x, g1_y, g1_values.ravel()),
        "g2": (g2_x, g2_y, g2_values.ravel()),
    }


def rotate_sample_coordinates_90_cw(
    sample_x: np.ndarray,
    sample_y: np.ndarray,
    width: int,
    height: int,
) -> tuple[np.ndarray, np.ndarray, int, int]:
    """Rotate sparse sample coordinates like cv2.ROTATE_90_CLOCKWISE would."""
    rotated_x = sample_y.astype(np.float64)
    rotated_y = (float(width) - 1.0) - sample_x.astype(np.float64)
    return rotated_x, rotated_y, int(height), int(width)


def compute_esf_from_samples(
    sample_x: np.ndarray,
    sample_y: np.ndarray,
    sample_values: np.ndarray,
    edge_angle: float,
    oversample_factor: int,
    width: int,
    height: int,
) -> np.ndarray:
    """Compute an ESF from sparse sample coordinates instead of a dense image grid."""
    if sample_x.size == 0 or sample_y.size == 0 or sample_values.size == 0:
        return np.array([])

    angle_rad = np.radians(edge_angle)
    positions = (sample_x - (width / 2.0) - sample_y * np.tan(angle_rad)) * oversample_factor
    sort_idx = np.argsort(positions)
    positions = positions[sort_idx]
    values = sample_values[sort_idx]

    if positions.size == 0:
        return np.array([])

    bin_edges = np.arange(positions.min(), positions.max(), 1)
    if bin_edges.size < 2:
        return np.array([])
    bin_indices = np.digitize(positions, bin_edges)

    esf = []
    for i in range(1, len(bin_edges)):
        mask = bin_indices == i
        if np.any(mask):
            esf.append(np.mean(values[mask]))

    return np.array(esf, dtype=np.float64)


def smooth_esf(esf: np.ndarray, config: MTFConfig) -> Tuple[np.ndarray, str]:
    """Optional ESF smoothing. Returns (esf_used, warning)."""
    if esf.size == 0:
        return esf, ""

    # Step 1: Decide whether smoothing is enabled at all.
    mode = config.esf_smooth_mode
    if mode == "none":
        return esf, ""

    # Step 2: Apply the configured smoothing method.
    if mode == "sg":
        try:
            from scipy.signal import savgol_filter
            window = int(config.esf_sg_window)
            if window % 2 == 0:
                window += 1
            if window < 5:
                window = 5
            if window >= esf.size:
                window = max(3, esf.size - 1)
            if window % 2 == 0:
                window = max(3, window - 1)
            poly = int(config.esf_sg_poly)
            if poly >= window:
                poly = max(1, window - 1)
            if window < 3 or window <= poly:
                return esf, "ESF smoothing skipped (invalid window/poly)"
            esf_smoothed = savgol_filter(esf, window_length=window, polyorder=poly, mode="interp")
            return esf_smoothed, ""
        except Exception as e:
            return esf, f"ESF smoothing failed: {e}"

    return esf, f"ESF smoothing skipped (unknown mode: {mode})"


def compute_lsf(esf: np.ndarray, config: MTFConfig) -> np.ndarray:
    """Compute LSF from ESF using configured derivative mode."""
    if esf.size < 2:
        return np.array([])
    # The LSF is the discrete derivative of the ESF. The configured derivative
    # mode controls whether we use a centered ISO-like stencil or a plain diff.
    if config.derivative_mode == "iso":
        if esf.size < 3:
            return np.array([])
        kernel = np.array([-0.5, 0.0, 0.5], dtype=np.float64)
        return np.convolve(esf, kernel, mode="valid")
    return np.diff(esf)


def apply_lsf_window(lsf: np.ndarray, config: MTFConfig) -> np.ndarray:
    """Apply windowing to LSF based on configuration."""
    if lsf.size == 0:
        return lsf

    mode = config.lsf_window_mode
    if mode == "none":
        return lsf

    if mode == "peak":
        if config.lsf_peak_window_size > 0:
            size = min(int(config.lsf_peak_window_size), lsf.size)
        else:
            size = min(lsf.size, max(9, lsf.size // 3))
        if size < 4:
            return lsf
        if size % 2 == 0:
            size += 1
            if size > lsf.size:
                size = lsf.size
        peak_idx = int(np.argmax(np.abs(lsf)))
        half = size // 2
        start = max(0, peak_idx - half)
        end = min(lsf.size, peak_idx + half + 1)
        if end - start < size:
            if start == 0:
                end = min(lsf.size, start + size)
            elif end == lsf.size:
                start = max(0, end - size)
        window = np.hamming(end - start)
        lsf_windowed = np.zeros_like(lsf)
        lsf_windowed[start:end] = lsf[start:end] * window
        return lsf_windowed

    window = np.hamming(lsf.size)
    return lsf * window


def compute_mtf_from_lsf(
    lsf: np.ndarray, config: MTFConfig, measure_angle: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    """Compute frequency axis and MTF from an LSF."""
    if lsf.size == 0:
        raise ValueError("LSF computation failed (empty)")

    # Step 1: Window the LSF so the FFT is less sensitive to ROI truncation.
    lsf_windowed = apply_lsf_window(lsf, config)
    fft_lsf = np.fft.fft(lsf_windowed)
    mtf = np.abs(fft_lsf[:len(fft_lsf) // 2])

    if mtf.size == 0 or mtf[0] <= 0:
        raise ValueError("Zero mean component in MTF")

    mtf_raw = mtf / mtf[0]

    # Step 2: Convert FFT bins into physical spatial frequency in lp/mm.
    n = len(lsf_windowed)
    freq_cyc_per_pixel = np.fft.fftfreq(
        n, d=1.0 / config.oversample_factor)[:n // 2]
    pixel_pitch_mm = config.pixel_size_um / 1000.0
    frequencies_raw = freq_cyc_per_pixel / pixel_pitch_mm

    # Step 3: Undo attenuation introduced by the discrete derivative filter.
    if config.apply_derivative_correction and config.derivative_mode == "iso":
        sample_spacing_mm = pixel_pitch_mm / config.oversample_factor
        omega = 2.0 * np.pi * frequencies_raw * sample_spacing_mm
        sin_omega = np.sin(omega)
        corr = np.ones_like(omega)
        mask = np.abs(sin_omega) > 1e-8
        corr[mask] = omega[mask] / sin_omega[mask]
        if config.derivative_correction_max > 0:
            corr = np.minimum(corr, config.derivative_correction_max)
        mtf_raw = mtf_raw * corr

    mtf_peak_raw = float(np.max(mtf_raw)) if mtf_raw.size > 0 else 0.0

    # Step 4: Apply optional clipping/post-processing to the raw MTF curve.
    mtf_used = mtf_raw
    if config.mtf_clip_max > 0:
        mtf_used = np.minimum(mtf_raw, config.mtf_clip_max)

    # Step 5: Correct the frequency axis for the slanted edge angle if requested.
    if config.apply_angle_correction:
        cos_theta = float(abs(np.cos(np.radians(measure_angle))))
        frequencies = frequencies_raw * cos_theta
    else:
        frequencies = frequencies_raw

    # Step 6: Clip to sensor Nyquist if the caller wants a physically bounded curve.
    if config.clip_to_nyquist:
        sensor_nyquist = 1000.0 / (2.0 * config.pixel_size_um)
        mask = frequencies <= sensor_nyquist
        if np.any(mask):
            frequencies = frequencies[mask]
            mtf_raw = mtf_raw[mask]
            mtf_used = mtf_used[mask]

    if len(frequencies) != len(mtf_used):
        min_len = min(len(frequencies), len(mtf_used))
        frequencies = frequencies[:min_len]
        mtf_raw = mtf_raw[:min_len]
        mtf_used = mtf_used[:min_len]

    return frequencies, mtf_raw, mtf_used, lsf_windowed, mtf_peak_raw


def find_mtf_frequency(frequencies: np.ndarray, mtf: np.ndarray, threshold: float) -> float:
    """Find frequency at given MTF threshold by interpolation."""
    mask = frequencies >= 0
    freq_pos = frequencies[mask]
    mtf_pos = mtf[mask]

    for i in range(len(mtf_pos) - 1):
        if mtf_pos[i] >= threshold > mtf_pos[i + 1]:
            f1, f2 = freq_pos[i], freq_pos[i + 1]
            m1, m2 = mtf_pos[i], mtf_pos[i + 1]
            if m1 != m2:
                freq = f1 + (threshold - m1) * (f2 - f1) / (m2 - m1)
                return float(freq)

    return float(freq_pos[-1]) if len(freq_pos) > 0 else 0.0


def calculate_diffraction_mtf(frequencies: np.ndarray, config: MTFConfig) -> np.ndarray:
    """Calculate theoretical diffraction-limited MTF."""
    if config.f_number <= 0:
        return np.ones_like(frequencies)

    cutoff_freq = 1000.0 / (config.wavelength_um * config.f_number)
    v = np.abs(frequencies) / cutoff_freq
    v = np.clip(v, 0, 1)

    mtf_diff = (2.0 / np.pi) * (np.arccos(v) - v * np.sqrt(1 - v**2))
    mtf_diff[frequencies > cutoff_freq] = 0.0
    return mtf_diff


def validate_edge_crossing(
    roi: np.ndarray, config: MTFConfig
) -> Tuple[bool, str, Optional[Tuple[float, float, float, float]], Optional[str]]:
    """Validate that the dominant edge crosses the ROI boundaries."""
    if roi is None or roi.size == 0:
        return False, "empty ROI", None, None

    # Step 1: Convert to grayscale and reject obviously unusable ROIs.
    if len(roi.shape) == 3:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    else:
        gray = roi

    h, w = gray.shape[:2]
    if h < 4 or w < 4:
        return False, "ROI too small", None, None

    # Step 2: Build a gradient magnitude image and keep only strong edge pixels.
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.sqrt(gx**2 + gy**2)

    max_mag = float(np.max(mag)) if mag.size > 0 else 0.0
    if max_mag <= 1e-6:
        return False, "no gradients", None, None

    thresh = np.percentile(mag, config.edge_validation_percentile)
    ys, xs = np.where(mag >= thresh)
    if len(xs) < max(1, config.edge_validation_min_points):
        return False, "insufficient edge points", None, None

    # Step 3: Fit a single line through the dominant edge pixels.
    points = np.column_stack((xs, ys)).astype(np.float32)
    try:
        vx, vy, x0, y0 = cv2.fitLine(points, cv2.DIST_L2, 0, 0.01, 0.01).flatten()
    except Exception:
        return False, "line fit failed", None, None

    # Step 4: Check which ROI borders this fitted edge intersects.
    eps = 1e-6
    hits = set()

    if abs(vx) > eps:
        t_left = (0 - x0) / vx
        y_left = y0 + t_left * vy
        if 0 <= y_left <= h - 1:
            hits.add("left")
        t_right = ((w - 1) - x0) / vx
        y_right = y0 + t_right * vy
        if 0 <= y_right <= h - 1:
            hits.add("right")

    if abs(vy) > eps:
        t_top = (0 - y0) / vy
        x_top = x0 + t_top * vx
        if 0 <= x_top <= w - 1:
            hits.add("top")
        t_bottom = ((h - 1) - y0) / vy
        x_bottom = x0 + t_bottom * vx
        if 0 <= x_bottom <= w - 1:
            hits.add("bottom")

    hits_str = ",".join(sorted(hits)) if hits else ""
    if ("left" in hits and "right" in hits) or ("top" in hits and "bottom" in hits):
        return True, "", (float(x0), float(y0), float(vx), float(vy)), hits_str

    if hits:
        return False, f"edge intersects only {sorted(hits)}", (float(x0), float(y0), float(vx), float(vy)), hits_str
    return False, "edge does not intersect ROI borders", (float(x0), float(y0), float(vx), float(vy)), hits_str
