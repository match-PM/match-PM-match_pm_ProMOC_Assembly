"""Response builders for autofocus service handlers."""

from __future__ import annotations


def fill_single_mode_response(
    response,
    *,
    mode_name: str,
    best_position: float | None,
    best_score: float,
    measurements: int,
    duration_s: float,
    measurement_positions: list[float],
    measurement_scores: list[float],
    best_image_path: str = "",
):
    """Populate AutoFocus response fields for a single autofocus run."""
    response.success = best_position is not None
    response.status_message = f"{mode_name}: pos={float(best_position or 0.0):.3f}mm, score={float(best_score):.0f}"
    response.best_focus_position = float(best_position or 0.0)
    response.best_focus_value = float(best_score)
    response.total_measurements_taken = int(measurements)
    response.duration_seconds = float(duration_s)
    response.best_image_path = str(best_image_path or "")
    response.measurement_positions = [float(value) for value in measurement_positions]
    response.measurement_scores = [float(value) for value in measurement_scores]
    return response
