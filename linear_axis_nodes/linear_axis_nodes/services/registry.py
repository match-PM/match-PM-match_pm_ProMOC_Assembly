"""Service handlers for LTS300 callbacks composed from focused modules."""

from __future__ import annotations

from promoc_core.logging import LogTags, TaggedLogger

from ..config import LTS300NodeConfig
from .clients.lts300_interface import Lts300Interface
from .handlers.admin import LinearAdminCallbacks
from .handlers.motion import LinearMotionCallbacks
from ..domain.models import OperationStateStore, OperationStatus
from .validation import LinearAxisValidator


class ServiceHandlers:
    """Stable service handler entrypoint used by the LTS300 node orchestrator."""

    def __init__(
        self,
        logger,
        interface: Lts300Interface,
        config: LTS300NodeConfig,
    ):
        self.logger = TaggedLogger(logger, LogTags.LTS_MOVE)
        self.interface = interface
        self.config = config

        state_store = OperationStateStore()
        validator = LinearAxisValidator(self.config, self.logger)

        self._motion = LinearMotionCallbacks(
            self.logger,
            interface=self.interface,
            validator=validator,
            state_store=state_store,
            config=self.config,
        )
        self._admin = LinearAdminCallbacks(
            self.logger,
            interface=self.interface,
            config=self.config,
            state_store=state_store,
        )

    def get_operation_status(self) -> tuple[OperationStatus, str]:
        """Return operation status for periodic publishers and status services."""
        return self._admin.get_operation_status()

    def callback_move_absolute(self, request, response, other_axis_position: float):
        return self._motion.callback_move_absolute(
            request, response, other_axis_position
        )

    def callback_move_relative(self, request, response, other_axis_position: float):
        return self._motion.callback_move_relative(
            request, response, other_axis_position
        )

    def callback_home(self, request, response):
        return self._motion.callback_home(request, response)

    def callback_emergency_stop(self, request, response):
        return self._motion.callback_emergency_stop(request, response)

    def callback_stop(self, request, response):
        return self._motion.callback_stop(request, response)

    def callback_jog_axis(self, request, response):
        return self._motion.callback_jog_axis(request, response)

    def callback_get_position(self, request, response):
        return self._admin.callback_get_position(request, response)

    def callback_set_velocity_parameters(self, request, response):
        return self._admin.callback_set_velocity_parameters(request, response)

    def callback_get_velocity_parameters(self, request, response):
        return self._admin.callback_get_velocity_parameters(request, response)

    def callback_shutdown(self, request, response):
        return self._admin.callback_shutdown(request, response)

    def callback_get_operation_status(self, request, response):
        return self._admin.callback_get_operation_status(request, response)
