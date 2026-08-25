"""Weighted and robust surface fitting plus optional reference surfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class SurfaceFitResult:
    coefficients: np.ndarray
    covariance: np.ndarray
    predicted: np.ndarray
    residuals: np.ndarray
    base_weights: np.ndarray
    robust_weights: np.ndarray
    final_weights: np.ndarray


def build_surface_design(
    x_mm: np.ndarray,
    y_mm: np.ndarray,
    *,
    quadratic: bool,
) -> np.ndarray:
    """Build a center-referenced plane or quadratic surface design matrix."""
    design = np.column_stack((np.ones(x_mm.size), x_mm, y_mm))
    if quadratic:
        design = np.column_stack(
            (design, x_mm * x_mm, x_mm * y_mm, y_mm * y_mm)
        )
    return design


def fit_surface(
    design: np.ndarray,
    values_mm: np.ndarray,
    *,
    base_weights: np.ndarray | None = None,
    robust: bool = True,
    huber_k: float = 1.345,
    max_iterations: int = 30,
) -> SurfaceFitResult:
    """Fit a weighted surface with optional Huber IRLS.

    Input inverse-variance weights are normalized to median one. This leaves
    the coefficient estimate unchanged, improves numerical conditioning and
    makes exported weights comparable. Covariance is the inverse weighted
    normal matrix scaled by the reduced weighted residual sum of squares.
    """
    design = np.asarray(design, dtype=np.float64)
    values = np.asarray(values_mm, dtype=np.float64)
    if design.ndim != 2 or values.shape != (design.shape[0],):
        raise ValueError("surface design/value shape mismatch")
    if design.shape[0] <= design.shape[1]:
        raise ValueError("not enough ROIs for requested surface model")
    if base_weights is None:
        base = np.ones(design.shape[0], dtype=np.float64)
    else:
        base = np.asarray(base_weights, dtype=np.float64).copy()
        if base.shape != values.shape or np.any(~np.isfinite(base)) or np.any(base <= 0.0):
            raise ValueError("surface weights must be finite and positive")
        base /= max(float(np.median(base)), 1.0e-18)

    robust_weights = np.ones_like(base)
    coefficients = _weighted_lstsq(design, values, base)
    if robust:
        for _ in range(max_iterations):
            residuals = values - design @ coefficients
            scale = 1.4826 * float(
                np.median(np.abs(residuals - np.median(residuals)))
            )
            if scale <= 1.0e-12:
                break
            normalized = np.abs(residuals) / (huber_k * scale)
            updated_robust = np.ones_like(normalized)
            mask = normalized > 1.0
            updated_robust[mask] = 1.0 / normalized[mask]
            final = base * updated_robust
            updated = _weighted_lstsq(design, values, final)
            robust_weights = updated_robust
            if np.linalg.norm(updated - coefficients) <= 1.0e-10 * (
                1.0 + np.linalg.norm(coefficients)
            ):
                coefficients = updated
                break
            coefficients = updated

    final_weights = base * robust_weights
    predicted = design @ coefficients
    residuals = values - predicted
    normal = design.T @ (final_weights[:, None] * design)
    if np.linalg.matrix_rank(normal) < normal.shape[0]:
        raise ValueError("surface design matrix is rank deficient")
    dof = design.shape[0] - design.shape[1]
    reduced_weighted_rss = float(np.sum(final_weights * residuals**2)) / max(dof, 1)
    covariance = np.linalg.inv(normal) * reduced_weighted_rss
    return SurfaceFitResult(
        coefficients=coefficients,
        covariance=covariance,
        predicted=predicted,
        residuals=residuals,
        base_weights=base,
        robust_weights=robust_weights,
        final_weights=final_weights,
    )


def _weighted_lstsq(
    design: np.ndarray,
    values: np.ndarray,
    weights: np.ndarray,
) -> np.ndarray:
    root = np.sqrt(weights)
    return np.linalg.lstsq(design * root[:, None], values * root, rcond=None)[0]


@dataclass(frozen=True)
class ReferenceSurface:
    """Camera-fixed reference surface evaluated in object-side millimetres."""

    model: str
    coefficients: tuple[float, ...]
    object_um_per_pixel: float
    image_shape: tuple[int, int]
    metadata: dict[str, Any] = field(default_factory=dict)

    def evaluate(self, x_mm: np.ndarray, y_mm: np.ndarray) -> np.ndarray:
        quadratic = self.model == "quadratic"
        design = build_surface_design(x_mm, y_mm, quadratic=quadratic)
        coefficients = np.asarray(self.coefficients, dtype=np.float64)
        if coefficients.size != design.shape[1]:
            raise ValueError("reference-surface coefficient count does not match model")
        return design @ coefficients

    def validate_profile(
        self,
        *,
        object_um_per_pixel: float,
        image_shape: tuple[int, int],
    ) -> None:
        if tuple(image_shape) != tuple(self.image_shape):
            raise ValueError(
                f"reference image shape {self.image_shape} does not match {image_shape}"
            )
        relative = abs(self.object_um_per_pixel - object_um_per_pixel) / max(
            abs(object_um_per_pixel), 1.0e-12
        )
        if relative > 1.0e-6:
            raise ValueError("reference object_um_per_pixel does not match scan profile")

    def save(self, path: str | Path) -> None:
        payload = {
            "schema_version": 1,
            "model": self.model,
            "coefficients": list(self.coefficients),
            "object_um_per_pixel": self.object_um_per_pixel,
            "image_shape": list(self.image_shape),
            "metadata": self.metadata,
        }
        Path(path).write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "ReferenceSurface":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        model = str(payload["model"])
        if model not in {"plane", "quadratic"}:
            raise ValueError(f"unsupported reference surface model '{model}'")
        return cls(
            model=model,
            coefficients=tuple(float(value) for value in payload["coefficients"]),
            object_um_per_pixel=float(payload["object_um_per_pixel"]),
            image_shape=tuple(int(value) for value in payload["image_shape"]),
            metadata=dict(payload.get("metadata", {})),
        )
