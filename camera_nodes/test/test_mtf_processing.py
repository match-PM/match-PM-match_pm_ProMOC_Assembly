"""Unit tests for low-level MTF processing behavior."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
path_str = str(ROOT / "camera_nodes")
if path_str not in sys.path:
    sys.path.insert(0, path_str)

from camera_nodes.algorithms.mtf.config import MTFConfig  # noqa: E402
from camera_nodes.algorithms.mtf.processing import compute_mtf_from_lsf  # noqa: E402


def test_compute_mtf_from_lsf_caps_derivative_correction_peak():
    lsf = np.array([0.0, 0.2, 1.0, 0.2, 0.0], dtype=np.float64)
    uncapped_cfg = MTFConfig(
        pixel_size_um=2.4,
        derivative_mode="iso",
        apply_derivative_correction=True,
        derivative_correction_max=0.0,
        clip_to_nyquist=False,
        mtf_clip_max=0.0,
    )
    capped_cfg = MTFConfig(
        pixel_size_um=2.4,
        derivative_mode="iso",
        apply_derivative_correction=True,
        derivative_correction_max=1.15,
        clip_to_nyquist=False,
        mtf_clip_max=0.0,
    )

    _freq_uncapped, mtf_raw_uncapped, _mtf_used_uncapped, _lsf_windowed, peak_uncapped = (
        compute_mtf_from_lsf(lsf, uncapped_cfg, measure_angle=5.0)
    )
    _freq_capped, mtf_raw_capped, mtf_used_capped, _lsf_windowed, peak_capped = (
        compute_mtf_from_lsf(lsf, capped_cfg, measure_angle=5.0)
    )

    assert peak_capped <= peak_uncapped
    assert float(np.max(mtf_raw_capped)) == peak_capped
    assert float(np.max(mtf_used_capped)) == peak_capped


def test_compute_mtf_from_lsf_leaves_standard_path_unclipped_when_clip_max_zero():
    lsf = np.array([0.0, 0.1, 0.8, 0.1, 0.0], dtype=np.float64)
    cfg = MTFConfig(
        pixel_size_um=2.4,
        derivative_mode="iso",
        apply_derivative_correction=True,
        derivative_correction_max=1.15,
        clip_to_nyquist=False,
        mtf_clip_max=0.0,
    )

    _frequencies, mtf_raw, mtf_used, _lsf_windowed, _peak = compute_mtf_from_lsf(
        lsf,
        cfg,
        measure_angle=5.0,
    )

    assert np.allclose(mtf_raw, mtf_used)
