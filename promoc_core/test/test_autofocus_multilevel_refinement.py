import numpy as np


def _dummy_image() -> np.ndarray:
    # Image content is irrelevant because we'll monkeypatch the focus score.
    return np.zeros((32, 32), dtype=np.uint8)


def test_multilevel_refinement_reaches_min_step(monkeypatch):
    """HybridAutofocus should add refinement levels until min_step_mm is reached."""

    from promoc_core.algorithms.autofocus import HybridAutofocus, AutofocusConfig

    # Make the score a nice single peak around 1.234mm.
    target = 1.234

    def fake_score(_self, _image):
        # Use the current_z stored by the test harness (set before each call).
        z = getattr(_self, '_test_current_z', 0.0)
        return float(1.0 / (1e-6 + (z - target) ** 2))

    monkeypatch.setattr(
        HybridAutofocus, '_compute_focus_score', fake_score, raising=True)

    cfg = AutofocusConfig(
        z_min_mm=0.0,
        z_max_mm=2.0,
        coarse_step_mm=0.5,
        fine_step_mm=0.05,
        fine_range_mm=0.5,
        enable_multilevel=True,
        refinement_samples=21,
        min_step_mm=0.01,
        refinement_shrink_factor=0.25,
    )
    af = HybridAutofocus(cfg)

    z = af.start()
    img = _dummy_image()

    # Iterate until finished.
    for _ in range(2000):
        af._test_current_z = z  # used by fake_score
        result = af.process_image(z, img)
        if result.finished:
            assert result.best_z_mm is not None
            # Should at least be close-ish to target.
            assert abs(result.best_z_mm - target) <= 0.05
            # Internal step should have reached min_step.
            assert af._refine_current_step_mm <= cfg.min_step_mm + 1e-12
            return
        assert result.next_z_mm is not None
        z = float(result.next_z_mm)

    raise AssertionError('Autofocus did not finish in expected iterations')
