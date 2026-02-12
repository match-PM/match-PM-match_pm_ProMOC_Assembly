"""Scientific verification callback modules."""

from .base import ScientificVerificationBase

AutofocusVerificationCallbacks = None
MTFVerificationCallbacks = None
CorrelationVerificationCallbacks = None

try:  # pragma: no cover - exercised in ROS runtime
    from .autofocus import AutofocusVerificationCallbacks
    from .correlation import CorrelationVerificationCallbacks
    from .mtf import MTFVerificationCallbacks
except ImportError:
    pass

__all__ = ["ScientificVerificationBase"]

if (
    AutofocusVerificationCallbacks is not None
    and MTFVerificationCallbacks is not None
    and CorrelationVerificationCallbacks is not None
):

    class ScientificVerificationCallbacks(
        AutofocusVerificationCallbacks,
        MTFVerificationCallbacks,
        CorrelationVerificationCallbacks,
        ScientificVerificationBase,
    ):
        """Combined callback class for the scientific verification node."""

    __all__.extend(
        [
            "ScientificVerificationCallbacks",
            "AutofocusVerificationCallbacks",
            "MTFVerificationCallbacks",
            "CorrelationVerificationCallbacks",
        ]
    )
