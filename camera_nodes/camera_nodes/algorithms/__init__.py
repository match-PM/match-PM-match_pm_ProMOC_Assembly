"""
Camera Algorithms Package.

Image processing algorithms for camera_nodes:
- autofocus: Simple autofocus with multi-level refinement
- focus_metrics: Sharpness/focus quality metrics (tenengrad, laplacian, etc.)
- mtf_analysis: MTF computation using slanted edge method (ISO 12233)
"""

from .autofocus import (
    Autofocus, 
    ParabolicAutofocus,
    HillClimbingAutofocus,
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

__all__ = [
    # Autofocus
    'Autofocus',
    'ParabolicAutofocus',
    'AutofocusConfig',
    'AutofocusResult',
    'Phase',
    'tenengrad',
    
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
]
