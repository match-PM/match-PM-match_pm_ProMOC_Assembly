"""Helpers for canonical + legacy ROS service alias registration."""

from __future__ import annotations

from typing import Any, Callable


def build_deprecated_service_callback(
    warn: Callable[[str], None],
    legacy_path: str,
    canonical_path: str,
    callback: Callable[[Any, Any], Any],
) -> Callable[[Any, Any], Any]:
    """Wrap a callback and emit a deprecation warning for legacy service paths."""

    def _wrapped(request: Any, response: Any) -> Any:
        warn(
            f"Deprecated service '{legacy_path}' called. Use '{canonical_path}' instead."
        )
        return callback(request, response)

    return _wrapped


def register_service_alias_pair(
    node: Any,
    service_type: Any,
    canonical_path: str,
    legacy_path: str,
    callback: Callable[[Any, Any], Any],
    warn: Callable[[str], None],
    callback_group: Any | None = None,
) -> tuple[Any, Any]:
    """Create canonical and legacy service endpoints for a callback."""
    create_kwargs: dict[str, Any] = {}
    if callback_group is not None:
        create_kwargs["callback_group"] = callback_group

    canonical_service = node.create_service(
        service_type, canonical_path, callback, **create_kwargs
    )
    legacy_service = node.create_service(
        service_type,
        legacy_path,
        build_deprecated_service_callback(
            warn=warn,
            legacy_path=legacy_path,
            canonical_path=canonical_path,
            callback=callback,
        ),
        **create_kwargs,
    )
    return canonical_service, legacy_service
