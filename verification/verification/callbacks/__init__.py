"""Scientific verification callback modules."""

from .autofocus import AutofocusVerificationCallbacks
from .base import ScientificVerificationBase
from .correlation import CorrelationVerificationCallbacks
from .mtf import MTFVerificationCallbacks


class ScientificVerificationCallbacks(
    AutofocusVerificationCallbacks,
    MTFVerificationCallbacks,
    CorrelationVerificationCallbacks,
    ScientificVerificationBase,
):
    """Combined callback class for the scientific verification node."""


__all__ = [
    "ScientificVerificationCallbacks",
    "AutofocusVerificationCallbacks",
    "MTFVerificationCallbacks",
    "CorrelationVerificationCallbacks",
    "ScientificVerificationBase",
]
