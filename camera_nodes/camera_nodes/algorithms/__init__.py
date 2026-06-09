"""Camera algorithms.

This package contains the algorithm implementations used by the camera package:
- autofocus
- focus metrics
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


__all__ = [
    # Autofocus algorithms
    "FourStepAutofocus",
    "AutofocusConfig",
    "AutofocusResult",
    "Phase",
    "tenengrad",
    # Focus metrics
    "laplacian_variance",
    "tenengrad_metric",
    "brenner_gradient",
    "normalized_variance",
    "sml",
]

