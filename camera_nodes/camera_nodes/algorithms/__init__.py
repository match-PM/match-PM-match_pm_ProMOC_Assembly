"""Camera algorithms.

This package contains the algorithm implementations used by the camera package:
- autofocus
- focus metrics
<<<<<<< HEAD
=======
- MTF analysis
- ROI and field-curvature helpers
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
"""

from .autofocus import (
    FourStepAutofocus,
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
<<<<<<< HEAD
=======
from .mtf import MTFAnalyzer, MTFResult, MTFConfig
from .field_curvature import (
    analyze_field_curvature,
    analyze_field_curvature_detailed,
    detect_field_rois,
    calculate_field_metrics,
    FIELD_POSITIONS,
)


# Centralized algorithm definitions for autofocus.
# Used by autofocus callbacks and tooling.
AUTOFOCUS_ALGORITHMS = [
    (0, "goldensection", GoldenSectionAutofocus),
    (1, "hillclimbing", HillClimbingAutofocus),
    (2, "parabolic", IterativeParabolicAutofocus),
    (3, "fibonacci", FibonacciAutofocus),
    (4, "exhaustive", ExhaustiveAutofocus),  # Reference algorithm
    (5, "fourstep", FourStepAutofocus),
    (6, "mspr_autofocus", MSPRAutofocus),
]
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0


__all__ = [
    # Autofocus algorithms
<<<<<<< HEAD
    "FourStepAutofocus",
=======
    "MSPRAutofocus",
    "ParabolicAutofocus",
    "IterativeParabolicAutofocus",
    "GoldenSectionAutofocus",
    "HillClimbingAutofocus",
    "FourStepAutofocus",
    "ExhaustiveAutofocus",
    "FibonacciAutofocus",
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
    "AutofocusConfig",
    "AutofocusResult",
    "Phase",
    "tenengrad",
<<<<<<< HEAD
=======
    "AUTOFOCUS_ALGORITHMS",  # Centralized algorithm list
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
    # Focus metrics
    "laplacian_variance",
    "tenengrad_metric",
    "brenner_gradient",
    "normalized_variance",
    "sml",
<<<<<<< HEAD
=======
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
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
]

