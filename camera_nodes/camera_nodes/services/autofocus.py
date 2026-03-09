"""Autofocus handler with fly-over detection and refinement orchestration."""

from __future__ import annotations

import time

from promoc_core.promoc_exceptions import ConfigurationError, ImageProcessingError

from ..models import FocusProfileBuilder
from .fly_over import FlyOverDetector
from .autofocus_axis import AxisClientManager
from .autofocus_runner import AutofocusRunner
from .base import CallbackBase
from promoc_core.error_handling import handle_service_errors


class AutofocusHandler(CallbackBase):
    """Handler for autofocus with fly-over detection."""

    def __init__(self, node, camera_driver):
        super().__init__(node, camera_driver)
        self._axis_clients = AxisClientManager(self)
        self._runner = AutofocusRunner(self)

    def _build_focus_profile(self, request) -> dict:
        """Build objective-aware autofocus profile for fly-over and refinement."""
        return FocusProfileBuilder(self._node).build(request).as_dict()

    @handle_service_errors()
    def autofocus_callback(self, request, response):
        """Run autofocus: optional fly-over plus selected refinement mode."""
        mode = getattr(request, "focus_mode", getattr(request, "refinement_mode", 0))
        start_time = time.time()
        focus_profile = self._build_focus_profile(request)

        self._node.get_logger().info(
            f"Autofocus: range {request.start_position}-{request.end_position}mm, mode={mode}"
        )
        mag_label = (
            f'{focus_profile["magnification_x"]:.2f}x'
            if focus_profile["magnification_x"] is not None
            else "unknown"
        )
        self._node.get_logger().info(
            f'Objective profile: objective="{focus_profile["objective"]}" '
            f"mag={mag_label} beamsplitter={focus_profile['beamsplitter']} "
            f"profile={focus_profile['profile_source']} "
            f"scan_speed={focus_profile['scan_speed_mm_s']:.2f}mm/s "
            f"axis_scale={focus_profile['axis_speed_scale']:.3f} "
            f"max_sample_step={focus_profile['max_sample_step_mm']:.3f}mm "
            f"coarse_step={focus_profile['coarse_step_mm']:.3f}mm min_step={focus_profile['min_step_mm']:.3f}mm "
            f"settle={focus_profile['settle_s']:.2f}s"
        )

        if request.start_position >= request.end_position:
            raise ConfigurationError("start_position must be < end_position")

        clients = self._get_all_axis_clients()

        skip_flyover = getattr(request, "skip_flyover", False)
        if skip_flyover:
            self._node.get_logger().info("Skipping fly-over, using full range.")
            peak_start = float(request.start_position)
            peak_end = float(request.end_position)
        else:
            self._node.get_logger().info("Phase 1: Fly-Over Detection...")
            peak_start, peak_end, max_stddev = self._fly_over_detection(
                request.start_position,
                request.end_position,
                clients,
                focus_profile,
            )
            if peak_start is None or peak_end is None:
                raise ImageProcessingError("No target detected during fly-over")
            self._node.get_logger().info(
                f"Peak detected: {peak_start:.1f}-{peak_end:.1f}mm (max_stddev={max_stddev:.1f})"
            )

        return self._run_single_mode(
            mode,
            peak_start,
            peak_end,
            request,
            response,
            clients,
            start_time,
            focus_profile,
        )

    # ======================================================================
    # AXIS CLIENT MANAGEMENT (delegated)
    # ======================================================================

    def _get_all_axis_clients(self):
        return self._axis_clients.get_all_axis_clients()

    def _wait_for_axis_idle(self, clients):
        self._axis_clients.wait_for_axis_idle(clients)

    def _get_position(self, clients) -> float:
        return self._axis_clients.get_position(clients)

    # ======================================================================
    # FLY-OVER DETECTION
    # ======================================================================

    def _fly_over_detection(
        self,
        start_pos: float,
        end_pos: float,
        clients,
        focus_profile: dict | None = None,
    ) -> tuple:
        """Fast fly-over scan for target detection."""
        detector = FlyOverDetector(
            node=self._node,
            get_latest_cv_image=self._get_latest_cv_image,
            get_center_roi=self._get_center_roi,
            wait_for_axis_idle=self._wait_for_axis_idle,
            get_position=self._get_position,
        )
        result = detector.detect(
            start_pos=float(start_pos),
            end_pos=float(end_pos),
            clients=clients,
            focus_profile=focus_profile,
        )
        return result.peak_start, result.peak_end, result.max_stddev

    # ======================================================================
    # RUNNER DELEGATION
    # ======================================================================

    def _run_single_mode(
        self,
        mode: int,
        peak_start: float,
        peak_end: float,
        request,
        response,
        clients,
        start_time: float,
        focus_profile: dict | None = None,
    ):
        return self._runner.run_single_mode(
            mode,
            peak_start,
            peak_end,
            request,
            response,
            clients,
            start_time,
            focus_profile,
        )

    def _run_autofocus_loop(
        self, af, clients, return_best_image: bool = False, settle_s: float = 0.1
    ) -> tuple:
        return self._runner.run_autofocus_loop(
            af,
            clients,
            return_best_image=return_best_image,
            settle_s=settle_s,
        )

    def _run_comparison(
        self,
        peak_start: float,
        peak_end: float,
        request,
        response,
        clients,
        start_time: float,
        focus_profile: dict | None = None,
    ):
        return self._runner.run_comparison(
            peak_start,
            peak_end,
            request,
            response,
            clients,
            start_time,
            focus_profile,
        )

    @handle_service_errors()
    def autofocus_comparison_callback(self, request, response):
        """Run all autofocus modes sequentially and export a comparison CSV."""
        start_time = time.time()

        self._node.get_logger().info(
            f"Comparison Test: range {request.start_position}-{request.end_position}mm"
        )

        if request.start_position >= request.end_position:
            raise ConfigurationError("start_position must be < end_position")

        clients = self._get_all_axis_clients()
        focus_profile = self._build_focus_profile(request)

        self._node.get_logger().info("Phase 1: Fly-Over Detection...")
        peak_start, peak_end, max_stddev = self._fly_over_detection(
            request.start_position,
            request.end_position,
            clients,
            focus_profile,
        )
        if peak_start is None or peak_end is None:
            raise ImageProcessingError("No target detected during fly-over")

        self._node.get_logger().info(
            f"Peak: {peak_start:.1f}-{peak_end:.1f}mm (max_stddev={max_stddev:.1f})"
        )

        return self._run_comparison(
            peak_start,
            peak_end,
            request,
            response,
            clients,
            start_time,
            focus_profile,
        )

