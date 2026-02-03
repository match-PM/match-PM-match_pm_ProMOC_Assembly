"""
Camera Algorithms Package.

Image processing algorithms for camera_nodes:
- autofocus: Simple autofocus with multi-level refinement
- focus_metrics: Sharpness/focus quality metrics (tenengrad, laplacian, etc.)
- mtf_analysis: MTF computation using slanted edge method (ISO 12233)
- statistics: Statistical analysis utilities for verification
- field_curvature: Field curvature analysis for MTF across FOV
"""

from camera_nodes.algorithms.autofocus import (
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
from camera_nodes.algorithms.focus_metrics import (
    laplacian_variance,
    tenengrad as tenengrad_metric,
    brenner_gradient,
    normalized_variance,
    sml
)
from camera_nodes.algorithms.mtf_analysis import MTFAnalyzer, MTFResult, MTFConfig
from .statistics import (
    calculate_statistics,
    detect_outliers,
    perform_t_test,
    calculate_rms_error,
    calculate_repeatability,
    StatisticsResult,
    TTestResult
)
from camera_nodes.algorithms.field_curvature import (
    analyze_field_curvature,
    analyze_field_curvature_detailed,
    detect_field_rois,
    calculate_field_metrics,
    FIELD_POSITIONS
)


# Centralized algorithm definitions for autofocus
# Used by autofocus callbacks and verification services
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
    
    # Statistics
    'calculate_statistics',
    'detect_outliers',
    'perform_t_test',
    'calculate_rms_error',
    'calculate_repeatability',
    'StatisticsResult',
    'TTestResult',
    
    # Field curvature
    'analyze_field_curvature',
    'analyze_field_curvature_detailed',
    'detect_field_rois',
    'calculate_field_metrics',
    'FIELD_POSITIONS',
]

