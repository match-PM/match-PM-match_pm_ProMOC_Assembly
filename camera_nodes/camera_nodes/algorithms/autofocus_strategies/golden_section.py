"""Golden-section autofocus strategy."""

from __future__ import annotations

from enum import Enum, auto

from ..autofocus import AutofocusConfig, AutofocusResult, GOLDEN_RATIO, MSPRAutofocus, Phase


class _GoldenSectionState(Enum):
    """Which inner probe still needs to be measured."""

    UNINITIALIZED = auto()
    MEASURE_LEFT_PROBE = auto()
    MEASURE_RIGHT_PROBE = auto()


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
        self._gs_state = _GoldenSectionState.UNINITIALIZED

    def start(self) -> float:
        # Reset strategy-local state for re-entrant runs.
        self.a = 0.0
        self.b = 0.0
        self.c = 0.0
        self.d = 0.0
        self.fc = None
        self.fd = None
        self._gs_state = _GoldenSectionState.UNINITIALIZED
        return super().start()

    def _prepare_refinement(self):
        if not self._best_measurement:
            return

        # Step 1: Build the initial bracket around the coarse best position.
        center = self._best_measurement.position_mm

        # Initial bracket around the coarse best.
        bracket_width = self.config.step_mm * 2.0
        self.a = max(self.config.start_mm, center - bracket_width)
        self.b = min(self.config.end_mm, center + bracket_width)

        # Step 2: Place the two inner probe points by golden ratio.
        self.c = self.b - (self.b - self.a) / GOLDEN_RATIO
        self.d = self.a + (self.b - self.a) / GOLDEN_RATIO
        self.fc = None
        self.fd = None
        self._gs_state = _GoldenSectionState.MEASURE_LEFT_PROBE

        # Step 3: Schedule the first probe move.
        self._refinement_positions = [self.c]
        self._current_step_mm = abs(self.d - self.c)
        self._current_range_mm = (self.b - self.a) / 2
        self._refinement_index = 0
        self._refinement_level = 1

    def _handle_refinement(self) -> AutofocusResult:
        """Golden-section refinement with explicit interval contraction."""
        current_score = self._measurements[-1].score

        # Step 1: Store the score for the inner probe that was just measured.
        if self._gs_state == _GoldenSectionState.MEASURE_LEFT_PROBE:
            self.fc = current_score
        elif self._gs_state == _GoldenSectionState.MEASURE_RIGHT_PROBE:
            self.fd = current_score

        # Step 2: Force measurement of the missing inner probe before contracting.
        if self.fc is None:
            self._gs_state = _GoldenSectionState.MEASURE_LEFT_PROBE
            return self._make_result(
                next_position=self.c,
                phase=Phase.REFINEMENT,
                progress=min(0.98, 0.5 + 0.05 * self._refinement_level),
            )

        if self.fd is None:
            self._gs_state = _GoldenSectionState.MEASURE_RIGHT_PROBE
            return self._make_result(
                next_position=self.d,
                phase=Phase.REFINEMENT,
                progress=min(0.98, 0.5 + 0.05 * self._refinement_level),
            )

        # Step 3: Stop once the bracket is smaller than the target resolution.
        interval_size = self.b - self.a
        self._current_step_mm = interval_size
        self._current_range_mm = interval_size / 2
        if interval_size <= self.config.min_step_mm * 2:
            self._phase = Phase.FINISHED
            return self._make_result(finished=True, phase=Phase.FINISHED, progress=1.0)

        # Step 4: Keep the better half-interval and reuse one probe point.
        if self.fc > self.fd:
            # Keep [a, d], reuse c as new d.
            self.b = self.d
            self.d = self.c
            self.fd = self.fc
            self.c = self.b - (self.b - self.a) / GOLDEN_RATIO
            self.fc = None
            next_position = self.c
            self._gs_state = _GoldenSectionState.MEASURE_LEFT_PROBE
        else:
            # Keep [c, b], reuse d as new c.
            self.a = self.c
            self.c = self.d
            self.fc = self.fd
            self.d = self.a + (self.b - self.a) / GOLDEN_RATIO
            self.fd = None
            next_position = self.d
            self._gs_state = _GoldenSectionState.MEASURE_RIGHT_PROBE

        # Step 5: Publish the next probe move.
        self._refinement_level += 1
        self._current_step_mm = abs(self.d - self.c)
        self._current_range_mm = (self.b - self.a) / 2
        self._refinement_positions = [next_position]
        return self._make_result(
            next_position=next_position,
            phase=Phase.REFINEMENT,
            progress=min(0.98, 0.5 + 0.05 * self._refinement_level),
        )
