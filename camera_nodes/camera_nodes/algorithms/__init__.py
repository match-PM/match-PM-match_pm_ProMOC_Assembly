"""
Camera Algorithms Package.

Image processing algorithms for camera_nodes:
- autofocus: Simple autofocus with multi-level refinement
- focus_metrics: Sharpness/focus quality metrics (tenengrad, laplacian, etc.)
- mtf_analysis: MTF computation using slanted edge method (ISO 12233)
"""

from .autofocus import (
    MSPRAutofocus,
    ParabolicAutofocus,
    IterativeParabolicAutofocus,
    GoldenSectionAutofocus,
    HillClimbingAutofocus,
    FourStepAutofocus,
    ExhaustiveAutofocus,
    FibonacciAutofocus,
    AutofocusConfig,
    AutofocusResult,
    Phase,
    tenengrad
)
from .focus_metrics import (
    laplacian_variance,
    tenengrad as tenengrad_metric,
    brenner_gradient,
    normalized_variance,
    sml
)
from .mtf_analysis import MTFAnalyzer, MTFResult, MTFConfig
from .field_curvature import (
    analyze_field_curvature,
    analyze_field_curvature_detailed,
    detect_field_rois,
    calculate_field_metrics,
    FIELD_POSITIONS
)


# Centralized algorithm definitions for autofocus.
# Used by autofocus callbacks and tooling.
AUTOFOCUS_ALGORITHMS = [
    (0, 'goldensection', GoldenSectionAutofocus),
    (1, 'hillclimbing', HillClimbingAutofocus),
    (2, 'parabolic', IterativeParabolicAutofocus),
    (3, 'fibonacci', FibonacciAutofocus),
    (4, 'exhaustive', ExhaustiveAutofocus),  # Reference algorithm
    (5, 'fourstep', FourStepAutofocus),
    (6, 'mspr_autofocus', MSPRAutofocus),
]


__all__ = [
    # Autofocus algorithms
    'MSPRAutofocus',
    'ParabolicAutofocus',
    'IterativeParabolicAutofocus',
    'GoldenSectionAutofocus',
    'HillClimbingAutofocus',
    'FourStepAutofocus',
    'ExhaustiveAutofocus',
    'FibonacciAutofocus',
    'AutofocusConfig',
    'AutofocusResult',
    'Phase',
    'tenengrad',
    'AUTOFOCUS_ALGORITHMS',  # Centralized algorithm list
    
    # Focus metrics
    'laplacian_variance',
    'tenengrad_metric',
    'brenner_gradient',
    'normalized_variance',
    'sml',
    
    # MTF analysis
    'MTFAnalyzer',
    'MTFResult',
    'MTFConfig',
    
    # Field Curvature
    'analyze_field_curvature',
    'analyze_field_curvature_detailed',
    'detect_field_rois',
    'calculate_field_metrics',
    'FIELD_POSITIONS',
]

