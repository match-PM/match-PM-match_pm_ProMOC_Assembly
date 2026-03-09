"""Camera service validation helpers."""

from __future__ import annotations


def has_image(message) -> bool:
    """Return True when an image message is available."""
    return message is not None
