"""Service registry for the linear-axis package."""

from __future__ import annotations

from promoc_core.logging import LogTags, TaggedLogger

from ..config import LTS300NodeConfig
from ..models import OperationStateStore, OperationStatus
from .admin import LinearAdminCallbacks
from .motion import LinearMotionCallbacks
from .validation import LinearAxisValidator


class ServiceHandlers:
    """Compose motion and admin callbacks behind one stable service entrypoint."""

    def __init__(
        self,
        logger,
        driver,
        config: LTS300NodeConfig,
    ):
        self.logger = TaggedLogger(logger, LogTags.LTS_MOVE)
        self.driver = driver
        self.config = config

        state_store = OperationStateStore()
        validator = LinearAxisValidator(self.config, self.logger)

        self._motion = LinearMotionCallbacks(
            self.logger,
            driver=self.driver,
            validator=validator,
            state_store=state_store,
            config=self.config,
        )
        self._admin = LinearAdminCallbacks(
            self.logger,
            driver=self.driver,
            config=self.config,
            state_store=state_store,
        )

    def get_operation_status(self) -> tuple[OperationStatus, str]:
        return self._admin.get_operation_status()

    def callback_move_absolute(self, request, response, other_axis_position: float):
        return self._motion.callback_move_absolute(request, response, other_axis_position)

    def callback_move_relative(self, request, response, other_axis_position: float):
        return self._motion.callback_move_relative(request, response, other_axis_position)

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
