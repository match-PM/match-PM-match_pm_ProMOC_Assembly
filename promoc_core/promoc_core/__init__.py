"""\
ProMOC Core – Shared Utilities and Algorithms
=============================================

This package contains common helper functions and algorithms that are reused
across all ProMOC assembly nodes.

The goal is to bundle central components (conversions, validation, motion tracking,
error classes, and image processing algorithms) in one place. This helps
avoid code duplication and maintains consistent behavior across the entire system.

Quickstart
----------
Typical imports:

    # Unit conversions (ROS uses SI → meters, hardware often → mm)
    from promoc_core.conversions import mm_to_m, m_to_mm

    # Validation (bounds checks, safety checks)
    from promoc_core.validation import is_in_range, check_collision_risk

    # Motion status / target achievement
    from promoc_core.motion import MotionStatus, check_position_reached

    # Custom Exceptions
    from promoc_core.promoc_exceptions import HardwareError, PositionError

    # Error handling (logging, severity, diagnostics)
    from promoc_core.error_handling import ErrorHandler

Module Overview
---------------
**conversions**
    Functions for converting units: length (m, mm, µm), angles (rad, deg),
    optical frequencies (lp/mm), and velocities (m/s, mm/s).

**validation**
    Position validation, bounds checking, and collision/risk checks.
    Contains Bounds1D/Bounds3D and various `validate_*` helpers.

**motion**
    Motion status tracking and waiting/polling logic.
    Contains MotionStatus, MotionResult, as well as wait_for_position/wait_for_idle.

**promoc_exceptions**
    Exception hierarchy for structured error handling.
    Base class: ProMOCError. Subclasses: HardwareError, MotionError, etc.

**error_handling**
    ROS-integrated error handling including logging, severity levels, and
    error counters for diagnostics.

**algorithms**
    Image processing algorithms for optics/camera evaluation:
    - autofocus: Autofocus algorithms (Hybrid, Multi-Level, etc.).
    - focus_metrics: Sharpness metrics (Laplacian, Tenengrad, ...).
    - mtf_analysis: MTF measurement & analysis.

Example
--------
Typical usage in a ROS2 node:

    from promoc_core.conversions import mm_to_m
    from promoc_core.validation import is_in_range
    from promoc_core.promoc_exceptions import SoftLimitViolationError

    class MyNode(Node):
        def move_to(self, position_mm: float):
            # Validate position
            if not is_in_range(position_mm, self.min_pos, self.max_pos):
                raise SoftLimitViolationError(
                    f"Position {position_mm} is outside valid limits"
                )

            # Convert to ROS units (meters)
            position_m = mm_to_m(position_mm)

            # Send to hardware...

Further Info
-------------
- Detailed API documentation is available in the docstrings of the respective modules.
- Examples can be found under `docs/examples/`.
- For error handling patterns, see `ERROR_HANDLING.md`.
- For a quick reference, see `QUICK_REFERENCE.md`.
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
