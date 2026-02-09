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
    mtf_values: np.ndarray = field(default_factory=lambda: np.array([]))
    mtf_ideal: np.ndarray = field(default_factory=lambda: np.array([]))
    esf: np.ndarray = field(default_factory=lambda: np.array([]))
    lsf: np.ndarray = field(default_factory=lambda: np.array([]))
    edge_angle: float = 0.0
    valid: bool = False
    error_msg: str = ""
    roi_bounds: Optional[Tuple[int, int, int, int]] = None
    edge_name: str = ""
    edge_direction: str = ""
    sensor_nyquist: float = 0.0
    mtf_peak: float = 0.0
    mtf_peak_raw: float = 0.0
    mtf_clipped: bool = False
    warning_msg: str = ""

    @property
    def nyquist_frequency(self) -> float:
        """Nyquist frequency in lp/mm (Sensor Limit)."""
        if self.sensor_nyquist > 0:
            return self.sensor_nyquist
        if len(self.frequencies) > 0:
            return float(np.max(self.frequencies))
        return 0.0
