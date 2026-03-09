"""Deterministic autofocus benchmark against ExhaustiveAutofocus reference."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
import types

import numpy as np
import pytest


PYTHON_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PYTHON_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_PACKAGE_ROOT))

# Autofocus imports cv2, but this benchmark bypasses image processing by
# injecting deterministic score functions. A tiny stub keeps the import working
# even when OpenCV is not installed in the test environment.
if "cv2" not in sys.modules:
    sys.modules["cv2"] = types.SimpleNamespace()

from camera_nodes.domain.algorithms.autofocus import (  # noqa: E402
    AutofocusConfig,
    ExhaustiveAutofocus,
    FibonacciAutofocus,
    FourStepAutofocus,
    GoldenSectionAutofocus,
    HillClimbingAutofocus,
    IterativeParabolicAutofocus,
    MSPRAutofocus,
)


@dataclass(frozen=True)
class Scenario:
    name: str
    peak_mm: float
    sigma_mm: float
    amplitude: float
    baseline: float
    noise_amplitude: float = 0.0
    plateau_half_width_mm: float = 0.0
    seed: int = 0


ALGORITHMS = {
    "goldensection": GoldenSectionAutofocus,
    "hillclimbing": HillClimbingAutofocus,
    "parabolic": IterativeParabolicAutofocus,
    "fibonacci": FibonacciAutofocus,
    "fourstep": FourStepAutofocus,
    "mspr_autofocus": MSPRAutofocus,
}


SCENARIOS = [
    Scenario(
        name="clean_unimodal",
        peak_mm=3.73,
        sigma_mm=0.42,
        amplitude=4200.0,
        baseline=120.0,
        noise_amplitude=0.0,
        seed=1,
    ),
    Scenario(
        name="moderate_noise",
        peak_mm=4.12,
        sigma_mm=0.50,
        amplitude=3800.0,
        baseline=150.0,
        noise_amplitude=80.0,
        seed=2,
    ),
    Scenario(
        name="low_contrast",
        peak_mm=2.45,
        sigma_mm=0.55,
        amplitude=900.0,
        baseline=200.0,
        noise_amplitude=30.0,
        seed=3,
    ),
    Scenario(
        name="plateau_near_peak",
        peak_mm=4.90,
        sigma_mm=0.45,
        amplitude=2600.0,
        baseline=180.0,
        noise_amplitude=40.0,
        plateau_half_width_mm=0.06,
        seed=4,
    ),
]


def _deterministic_noise(position_mm: float, amplitude: float, seed: int) -> float:
    """Order-independent pseudo-noise for fair algorithm comparison."""
    if amplitude <= 0:
        return 0.0
    return float(amplitude * np.sin((23.0 * position_mm) + (0.31 * seed)))


def _build_score_function(scenario: Scenario):
    def _score(position_mm: float) -> float:
        pos = float(position_mm)
        if scenario.plateau_half_width_mm > 0.0:
            distance = max(0.0, abs(pos - scenario.peak_mm) - scenario.plateau_half_width_mm)
            signal = np.exp(-0.5 * (distance / scenario.sigma_mm) ** 2)
        else:
            signal = np.exp(-0.5 * ((pos - scenario.peak_mm) / scenario.sigma_mm) ** 2)

        score = scenario.baseline + (scenario.amplitude * signal)
        score += _deterministic_noise(pos, scenario.noise_amplitude, scenario.seed)
        return max(0.0, float(score))

    return _score


def _run_algorithm(algorithm_cls, config: AutofocusConfig, score_fn, max_steps: int = 5000) -> dict:
    algorithm = algorithm_cls(config)
    algorithm._calculate_score = lambda image: score_fn(float(image))  # noqa: SLF001

    current_pos = float(algorithm.start())
    steps = 0
    result = None
    while steps < max_steps:
        result = algorithm.process_image(current_pos, current_pos)
        steps += 1
        if result.finished:
            break
        if result.next_position_mm is None:
            break
        current_pos = float(result.next_position_mm)

    return {
        "finished": bool(result.finished) if result is not None else False,
        "best_position_mm": float(result.best_position_mm) if result and result.best_position_mm is not None else np.nan,
        "best_score": float(result.best_score) if result is not None else 0.0,
        "measurements": steps,
    }


def _base_config() -> AutofocusConfig:
    return AutofocusConfig(
        start_mm=0.0,
        end_mm=6.0,
        step_mm=0.5,
        refinement_samples=31,
        min_step_mm=0.02,
        shrink_factor=0.45,
        early_termination_threshold=0.7,
        early_termination_count=3,
        use_sift_weighting=False,
        coarse_terminate_threshold=0.6,
        coarse_terminate_count=2,
        disable_coarse_early_termination=False,
    )


def test_autofocus_benchmark_convergence_and_efficiency():
    for scenario in SCENARIOS:
        score_fn = _build_score_function(scenario)
        reference = _run_algorithm(ExhaustiveAutofocus, _base_config(), score_fn)
        assert reference["finished"], f"Reference failed in scenario={scenario.name}"

        for name, algorithm_cls in ALGORITHMS.items():
            result = _run_algorithm(algorithm_cls, _base_config(), score_fn)
            assert result["finished"], f"{name} did not converge in scenario={scenario.name}"
            assert np.isfinite(result["best_position_mm"]), f"{name} produced invalid best position"
            assert result["measurements"] < reference["measurements"], (
                f"{name} is not more efficient than exhaustive in scenario={scenario.name}"
            )


def test_autofocus_benchmark_accuracy_vs_exhaustive():
    max_abs_error_mm = {
        "goldensection": 0.25,
        "hillclimbing": 0.40,
        "parabolic": 0.25,
        "fibonacci": 0.25,
        "fourstep": 0.20,
        "mspr_autofocus": 0.25,
    }

    for scenario in SCENARIOS:
        score_fn = _build_score_function(scenario)
        reference = _run_algorithm(ExhaustiveAutofocus, _base_config(), score_fn)
        ref_pos = reference["best_position_mm"]
        assert np.isfinite(ref_pos), f"Invalid exhaustive reference in scenario={scenario.name}"

        for name, algorithm_cls in ALGORITHMS.items():
            result = _run_algorithm(algorithm_cls, _base_config(), score_fn)
            assert result["finished"], f"{name} did not converge in scenario={scenario.name}"
            err = abs(result["best_position_mm"] - ref_pos)
            assert err <= max_abs_error_mm[name], (
                f"{name} error {err:.4f}mm exceeds limit {max_abs_error_mm[name]:.4f}mm "
                f"in scenario={scenario.name}"
            )
