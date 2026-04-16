"""Camera algorithms.

This package contains the algorithm implementations used by the camera package:
- autofocus
- focus metrics
- MTF analysis
- ROI and field-curvature helpers
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
    tenengrad,
)
from .focus_metrics import (
    laplacian_variance,
    tenengrad as tenengrad_metric,
    brenner_gradient,
    normalized_variance,
    sml,
)
from .mtf import MTFAnalyzer, MTFResult, MTFConfig
from .field_curvature import (
    analyze_field_curvature,
    analyze_field_curvature_detailed,
    detect_field_rois,
    calculate_field_metrics,
    FIELD_POSITIONS,
)


# Centralized algorithm definitions for autofocus.
# Used by service handlers and tooling.
AUTOFOCUS_ALGORITHMS = [
    (0, "fourstep", FourStepAutofocus),
    (1, "hillclimbing", HillClimbingAutofocus),
    (2, "parabolic", IterativeParabolicAutofocus),
    (3, "fibonacci", FibonacciAutofocus),
    (4, "exhaustive", ExhaustiveAutofocus),  # Reference algorithm
    (5, "goldensection", GoldenSectionAutofocus),
    (6, "mspr_autofocus", MSPRAutofocus),
]


__all__ = [
    # Autofocus algorithms
    "MSPRAutofocus",
    "ParabolicAutofocus",
    "IterativeParabolicAutofocus",
    "GoldenSectionAutofocus",
    "HillClimbingAutofocus",
    "FourStepAutofocus",
    "ExhaustiveAutofocus",
    "FibonacciAutofocus",
    "AutofocusConfig",
    "AutofocusResult",
    "Phase",
    "tenengrad",
    "AUTOFOCUS_ALGORITHMS",  # Centralized algorithm list
    # Focus metrics
    "laplacian_variance",
    "tenengrad_metric",
    "brenner_gradient",
    "normalized_variance",
    "sml",
    # MTF analysis
    "MTFAnalyzer",
    "MTFResult",
    "MTFConfig",
    # Field Curvature
    "analyze_field_curvature",
    "analyze_field_curvature_detailed",
    "detect_field_rois",
    "calculate_field_metrics",
    "FIELD_POSITIONS",
]
