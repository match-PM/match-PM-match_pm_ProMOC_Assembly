"""Linear-axis domain layer."""

from .logic import is_terminal_status
from .models import OperationStateStore, OperationStatus


__all__ = [
    "OperationStateStore",
    "OperationStatus",
    "is_terminal_status",
]
