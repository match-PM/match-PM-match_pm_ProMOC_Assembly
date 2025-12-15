"""
ProMOC Core - Shared Utilities and Algorithms
==============================================

This package provides common utilities and algorithms for all ProMOC
Assembly nodes. By centralizing shared functionality here, we ensure
consistency and reduce code duplication across the system.

Quick Start
-----------
Most common imports:

    # Unit conversions (ROS uses meters, hardware often uses mm)
    from promoc_core.conversions import mm_to_m, m_to_mm
    
    # Validation (bounds checking, collision detection)
    from promoc_core.validation import is_in_range, check_collision_risk
    
    # Motion status tracking
    from promoc_core.motion import MotionStatus, check_position_reached
    
    # Custom exceptions
    from promoc_core.promoc_exceptions import HardwareError, PositionError
    
    # Error handling
    from promoc_core.error_handling import ErrorHandler

Module Overview
---------------
**conversions**
    Unit conversion functions for length (m, mm, µm), angles (rad, deg),
    optical frequencies (lp/mm), and velocities (m/s, mm/s).

**validation**
    Position validation, bounds checking, and collision detection.
    Includes Bounds1D, Bounds3D classes and various validate_* functions.

**motion**
    Motion status tracking and waiting logic. Includes MotionStatus enum,
    MotionResult dataclass, and wait_for_position/wait_for_idle functions.

**promoc_exceptions**
    Custom exception hierarchy for structured error handling.
    Base class: ProMOCError. Subclasses: HardwareError, MotionError, etc.

**error_handling**
    ROS-integrated error handler that manages logging, severity levels,
    and error counting for diagnostics.

**algorithms**
    Image processing algorithms for lens testing:
    - autofocus: Autofocus algorithms (hill climbing, binary search)
    - focus_metrics: Image sharpness metrics (Laplacian, Tenengrad, etc.)
    - mtf_analysis: MTF measurement and analysis

Example Usage
-------------
Typical usage in a ROS2 node:

    from promoc_core.conversions import mm_to_m
    from promoc_core.validation import is_in_range
    from promoc_core.promoc_exceptions import SoftLimitViolationError
    
    class MyNode(Node):
        def move_to(self, position_mm: float):
            # Validate position
            if not is_in_range(position_mm, self.min_pos, self.max_pos):
                raise SoftLimitViolationError(f"Position {position_mm} out of range")
            
            # Convert to ROS units (meters)
            position_m = mm_to_m(position_mm)
            
            # Send to hardware...

For More Information
--------------------
- See individual module docstrings for detailed API documentation
- See docs/examples/ for example code
- See ERROR_HANDLING.md for error handling patterns
- See QUICK_REFERENCE.md for common patterns
"""

# Import modules in dependency order to avoid circular imports
from . import promoc_exceptions
from . import conversions
from . import validation
from . import motion
from . import error_handling

# Import algorithms last (may depend on other modules)
# NOTE: In some ROS/pytest collection scenarios (especially with mixed
# workspaces and partially built install trees), importing algorithms can
# trigger circular-import style errors that are not a plain ImportError.
# We keep the package importable and let users import submodules directly.
try:
    from . import algorithms
    _has_algorithms = True
except Exception:  # noqa: BLE001
    _has_algorithms = False
    algorithms = None

__all__ = [
    'promoc_exceptions',
    'error_handling',
    'conversions',
    'validation',
    'motion',
]

if _has_algorithms:
    __all__.append('algorithms')
