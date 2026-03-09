"""Golden-section autofocus strategy."""

from __future__ import annotations

from ..autofocus import AutofocusConfig, AutofocusResult, GOLDEN_RATIO, MSPRAutofocus, Phase


class GoldenSectionAutofocus(MSPRAutofocus):
    """Refinement strategy using golden-section interval contraction."""

    def __init__(self, config: AutofocusConfig):
        super().__init__(config)
        self.a = 0.0
        self.b = 0.0
        self.c = 0.0
        self.d = 0.0
        self.fc: float | None = None
        self.fd: float | None = None
        self._gs_state = "INIT"  # INIT, PROBE_C, PROBE_D

    def start(self) -> float:
        # Reset strategy-local state for re-entrant runs.
        self.a = 0.0
        self.b = 0.0
        self.c = 0.0
        self.d = 0.0
        self.fc = None
        self.fd = None
        self._gs_state = "INIT"
        return super().start()

    def _prepare_refinement(self):
        if not self._best_measurement:
            return

        center = self._best_measurement.position_mm

        # Initial bracket around the coarse best.
        bracket_width = self.config.step_mm * 2.0
        self.a = max(self.config.start_mm, center - bracket_width)
        self.b = min(self.config.end_mm, center + bracket_width)

        self.c = self.b - (self.b - self.a) / GOLDEN_RATIO
        self.d = self.a + (self.b - self.a) / GOLDEN_RATIO
        self.fc = None
        self.fd = None
        self._gs_state = "PROBE_C"

        self._refinement_positions = [self.c]
        self._current_step_mm = abs(self.d - self.c)
        self._current_range_mm = (self.b - self.a) / 2
        self._refinement_index = 0
        self._refinement_level = 1

    def _handle_refinement(self) -> AutofocusResult:
        """Golden-section refinement with explicit interval contraction."""
        current_score = self._measurements[-1].score

        if self._gs_state == "PROBE_C":
            self.fc = current_score
        elif self._gs_state == "PROBE_D":
            self.fd = current_score

        if self.fc is None:
            self._gs_state = "PROBE_C"
            return self._make_result(
                next_position=self.c,
                phase=Phase.REFINEMENT,
                progress=min(0.98, 0.5 + 0.05 * self._refinement_level),
            )

        if self.fd is None:
            self._gs_state = "PROBE_D"
            return self._make_result(
                next_position=self.d,
                phase=Phase.REFINEMENT,
                progress=min(0.98, 0.5 + 0.05 * self._refinement_level),
            )

        # Converged: interval below target resolution.
        interval_size = self.b - self.a
        self._current_step_mm = interval_size
        self._current_range_mm = interval_size / 2
        if interval_size <= self.config.min_step_mm * 2:
            self._phase = Phase.FINISHED
            return self._make_result(finished=True, phase=Phase.FINISHED, progress=1.0)

        # Contract interval by comparing inner probe scores.
        if self.fc > self.fd:
            # Keep [a, d], reuse c as new d.
            self.b = self.d
            self.d = self.c
            self.fd = self.fc
            self.c = self.b - (self.b - self.a) / GOLDEN_RATIO
            self.fc = None
            next_position = self.c
            self._gs_state = "PROBE_C"
        else:
            # Keep [c, b], reuse d as new c.
            self.a = self.c
            self.c = self.d
            self.fc = self.fd
            self.d = self.a + (self.b - self.a) / GOLDEN_RATIO
            self.fd = None
            next_position = self.d
            self._gs_state = "PROBE_D"

        self._refinement_level += 1
        self._current_step_mm = abs(self.d - self.c)
        self._current_range_mm = (self.b - self.a) / 2
        self._refinement_positions = [next_position]
        return self._make_result(
            next_position=next_position,
            phase=Phase.REFINEMENT,
            progress=min(0.98, 0.5 + 0.05 * self._refinement_level),
        )
