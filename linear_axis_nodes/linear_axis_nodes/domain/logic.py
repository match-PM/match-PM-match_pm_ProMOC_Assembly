"""Domain-level helpers for linear-axis behavior."""

from .models import OperationStatus


def is_terminal_status(status: OperationStatus) -> bool:
    """Return True when status represents a terminal motion state."""
    return status in {OperationStatus.IDLE, OperationStatus.ERROR}
