"""
Algorithms Package for ProMOC Core.

This package contains reusable algorithms for image processing,
focus analysis, and optical measurements.

Modules:
    - focus_metrics: Focus quality metrics (variance, tenengrad, brenner)
    - autofocus: Hybrid autofocus algorithm with hysteresis compensation
    - mtf_analysis: MTF computation using slanted edge method (ISO 12233)
    - siemens_star: Siemens star analysis for MTF and astigmatism
    - ronchi_grating: Ronchi grating analysis for MTF at specific frequency
"""

from .focus_metrics import (
    laplacian_variance,
    tenengrad,
    brenner_gradient,
    normalized_variance,
    sml
)

from .autofocus import (
    HybridAutofocus,
    AutofocusResult,
    AutofocusConfig,
    FocusPhase,
    ScanDirection
)

from .mtf_analysis import MTFAnalyzer, MTFResult, MTFConfig, compute_mtf

from .siemens_star import (
    SiemensStarAnalyzer,
    SiemensStarResult,
    SiemensStarConfig,
    DirectionalMTF,
    AnalysisStatus
)

from .ronchi_grating import (
    RonchiAnalyzer,
    RonchiResult,
    RonchiConfig,
    RonchiStatus,
    compute_ronchi_mtf
)

__all__ = [
    # Focus metrics
    'laplacian_variance',
    'tenengrad',
    'brenner_gradient',
    'normalized_variance',
    'sml',
    # Autofocus
    'HybridAutofocus',
    'AutofocusResult',
    'AutofocusConfig',
    'FocusPhase',
    'ScanDirection',
    # MTF (Slanted Edge)
    'MTFAnalyzer',
    'MTFResult',
    'MTFConfig',
    'compute_mtf',
    # Siemens Star
    'SiemensStarAnalyzer',
    'SiemensStarResult',
    'SiemensStarConfig',
    'DirectionalMTF',
    'AnalysisStatus',
    # Ronchi Grating
    'RonchiAnalyzer',
    'RonchiResult',
    'RonchiConfig',
    'RonchiStatus',
    'compute_ronchi_mtf',
]
