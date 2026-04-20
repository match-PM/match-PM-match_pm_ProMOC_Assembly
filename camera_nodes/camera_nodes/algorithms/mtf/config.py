"""MTF configuration dataclass."""

from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass
class MTFConfig:
    """Configuration for MTF analysis."""
    pixel_size_um: float = 2.40  # IDS U3-3800CP (Sony IMX183)
    input_mode: str = "dense_gray"  # dense_gray | raw_bayer_rggb
    raw_bayer_pattern: str = "RGGB"
    roi_width: int = 200
    roi_height: int = 200
    roi_center: Optional[Tuple[int, int]] = None
    min_edge_angle: float = 2.0
    max_edge_angle: float = 10.0
    oversample_factor: int = 4
    canny_low: int = 50
    canny_high: int = 150
    hough_threshold: int = 50
    f_number: float = 2.8  # Lens aperture (default assumption)
    wavelength_um: float = 0.555  # Green light default

    # LSF windowing
    lsf_window_mode: str = "full"  # full | peak | none
    lsf_peak_window_size: int = 0  # samples; 0 = auto

    # Derivative / ISO options
    derivative_mode: str = "iso"  # diff | iso
    apply_derivative_correction: bool = True
    derivative_correction_max: float = 0.0  # 0 disables cap
    apply_angle_correction: bool = True

    # ESF smoothing
    esf_smooth_mode: str = "none"  # none | sg
    esf_sg_window: int = 11
    esf_sg_poly: int = 2

    # Edge geometry validation
    edge_validation_mode: str = "warn"  # off | warn | fail
    edge_validation_percentile: float = 90.0
    edge_validation_min_points: int = 50
    angle_estimation_mode: str = "hybrid"  # hybrid | geometric | phase
    angle_allow_phase_fallback: bool = True
    angle_consistency_warn_deg: float = 1.5
    angle_min_support_points: int = 20
    analysis_strip_width_px: int = 60
    clip_to_nyquist: bool = True
    export_dual_curves: bool = False

    # MTF output handling
    mtf_clip_max: float = 0.0  # 0 disables clipping
    mtf_warn_threshold: float = 1.05  # warn if MTF peak exceeds this
    raw_green_pair_warn_pct: float = 10.0

    # Capture metadata
    capture_pixel_format: str = ""
    capture_binning_h: int = 0
    capture_binning_v: int = 0
    capture_exposure_us: float = 0.0
    capture_gain: float = 0.0
    source_encoding: str = ""
    measurement_metadata: dict[str, object] = field(default_factory=dict)

    # Debug export
    debug_export_dir: Optional[str] = None
    debug_export_prefix: str = "mtf"
    debug_export_csv: bool = True
    debug_export_png: bool = False

    def validate(self) -> None:
        """Validate configuration parameters."""
        if self.pixel_size_um <= 0:
            raise ValueError(
                f"pixel_size_um must be positive, got {self.pixel_size_um}")
        if self.input_mode not in {"dense_gray", "raw_bayer_rggb"}:
            raise ValueError(
                f"input_mode must be one of ['dense_gray','raw_bayer_rggb'], got {self.input_mode}"
            )
        if self.raw_bayer_pattern not in {"RGGB"}:
            raise ValueError(
                f"raw_bayer_pattern must currently be 'RGGB', got {self.raw_bayer_pattern}"
            )
        if self.roi_width <= 0 or self.roi_height <= 0:
            raise ValueError("ROI dimensions must be positive")
        if self.min_edge_angle < 0 or self.max_edge_angle <= self.min_edge_angle:
            raise ValueError(
                f"Invalid edge angle range: [{self.min_edge_angle}, {self.max_edge_angle}]")
        if self.oversample_factor < 1:
            raise ValueError(
                f"oversample_factor must be >= 1, got {self.oversample_factor}")
        if self.lsf_window_mode not in {"full", "peak", "none"}:
            raise ValueError(
                f"lsf_window_mode must be one of ['full','peak','none'], got {self.lsf_window_mode}")
        if self.lsf_peak_window_size < 0:
            raise ValueError("lsf_peak_window_size must be >= 0")
        if self.derivative_mode not in {"diff", "iso"}:
            raise ValueError(
                f"derivative_mode must be one of ['diff','iso'], got {self.derivative_mode}")
        if self.derivative_correction_max < 0:
            raise ValueError("derivative_correction_max must be >= 0")
        if self.esf_smooth_mode not in {"none", "sg"}:
            raise ValueError(
                f"esf_smooth_mode must be one of ['none','sg'], got {self.esf_smooth_mode}")
        if self.esf_sg_window <= 0:
            raise ValueError("esf_sg_window must be > 0")
        if self.esf_sg_poly < 0:
            raise ValueError("esf_sg_poly must be >= 0")
        if self.edge_validation_mode not in {"off", "warn", "fail"}:
            raise ValueError(
                f"edge_validation_mode must be one of ['off','warn','fail'], got {self.edge_validation_mode}")
        if self.angle_estimation_mode not in {"hybrid", "geometric", "phase"}:
            raise ValueError(
                "angle_estimation_mode must be one of ['hybrid','geometric','phase']"
            )
        if not (0 < self.edge_validation_percentile <= 100):
            raise ValueError("edge_validation_percentile must be in (0, 100]")
        if self.edge_validation_min_points < 0:
            raise ValueError("edge_validation_min_points must be >= 0")
        if self.angle_consistency_warn_deg < 0:
            raise ValueError("angle_consistency_warn_deg must be >= 0")
        if self.angle_min_support_points < 0:
            raise ValueError("angle_min_support_points must be >= 0")
        if self.analysis_strip_width_px < 0:
            raise ValueError("analysis_strip_width_px must be >= 0")
        if self.mtf_clip_max < 0:
            raise ValueError("mtf_clip_max must be >= 0")
        if self.mtf_warn_threshold < 0:
            raise ValueError("mtf_warn_threshold must be >= 0")
        if self.raw_green_pair_warn_pct < 0:
            raise ValueError("raw_green_pair_warn_pct must be >= 0")
        if self.capture_exposure_us < 0:
            raise ValueError("capture_exposure_us must be >= 0")
