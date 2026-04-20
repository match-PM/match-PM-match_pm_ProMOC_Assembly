"""MTF result dataclass."""

from dataclasses import dataclass, field
from typing import Optional, Tuple
import numpy as np


@dataclass
class MTFResult:
    """Result of MTF computation."""
    mtf50: float = 0.0
    mtf20: float = 0.0
    mtf10: float = 0.0
    frequencies: np.ndarray = field(default_factory=lambda: np.array([]))
    frequencies_alt: np.ndarray = field(default_factory=lambda: np.array([]))
    mtf_values: np.ndarray = field(default_factory=lambda: np.array([]))
    mtf_raw: np.ndarray = field(default_factory=lambda: np.array([]))
    mtf_raw_alt: np.ndarray = field(default_factory=lambda: np.array([]))
    mtf_used_alt: np.ndarray = field(default_factory=lambda: np.array([]))
    mtf_ideal: np.ndarray = field(default_factory=lambda: np.array([]))
    esf_raw: np.ndarray = field(default_factory=lambda: np.array([]))
    esf: np.ndarray = field(default_factory=lambda: np.array([]))
    lsf: np.ndarray = field(default_factory=lambda: np.array([]))
    lsf_windowed: np.ndarray = field(default_factory=lambda: np.array([]))
    edge_angle: float = 0.0
    valid: bool = False
    error_msg: str = ""
    roi_bounds: Optional[Tuple[int, int, int, int]] = None
    contrast: float = 0.0
    edge_name: str = ""
    edge_direction: str = ""
    sensor_nyquist: float = 0.0
    mtf_peak: float = 0.0
    mtf_peak_raw: float = 0.0
    mtf_clipped: bool = False
    warning_msg: str = ""
    capture_mode: str = ""
    capture_pixel_format: str = ""
    capture_binning_h: int = 0
    capture_binning_v: int = 0
    capture_exposure_us: float = 0.0
    capture_gain: float = 0.0
    illumination_wavelength_um: float = 0.0
    source_encoding: str = ""
    edge_angle_method: str = ""
    edge_angle_geometric: float = 0.0
    edge_angle_phase: float = 0.0
    edge_angle_consistency_deg: float = 0.0
    edge_fit_residual_px: float = 0.0
    edge_support_points: int = 0
    analysis_roi_bounds: Optional[Tuple[int, int, int, int]] = None
    g1_mtf50: float = 0.0
    g2_mtf50: float = 0.0
    g1_mtf20: float = 0.0
    g2_mtf20: float = 0.0
    g1_mtf10: float = 0.0
    g2_mtf10: float = 0.0
    g1_g2_delta_pct: float = 0.0

    @property
    def nyquist_frequency(self) -> float:
        """Nyquist frequency in lp/mm (Sensor Limit)."""
        if self.sensor_nyquist > 0:
            return self.sensor_nyquist
        if len(self.frequencies) > 0:
            return float(np.max(self.frequencies))
        return 0.0
