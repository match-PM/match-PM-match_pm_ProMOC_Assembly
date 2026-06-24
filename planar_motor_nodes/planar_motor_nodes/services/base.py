"""Shared service helpers for the planar-motor node."""

from __future__ import annotations

from contextlib import contextmanager
import math

from promoc_core import error_codes
from promoc_core.error_handling import handle_service_errors
from promoc_core.logging import LogTags, TaggedLogger
from promoc_core.promoc_exceptions import ConfigurationError

from ..config import MoverNodeConfig
from ..drivers.base import PlanarMotorDriver
from ..models import SpeedProfile
from .status import MoverUtils


class ServiceCallbacksBase:
    """Shared constructor and helpers for planar-motor service callbacks."""

    NO_CHANGE = -999999.0

    def __init__(
        self,
        logger,
        driver: PlanarMotorDriver,
        mover_utils: MoverUtils,
        config: MoverNodeConfig,
    ):
        self.logger = TaggedLogger(logger, LogTags.PMC_MOTION)
        self.driver = driver
        self.mover_utils = mover_utils
        self.config = config

    @staticmethod
    def _require_finite(value: float, name: str) -> float:
        if not math.isfinite(float(value)):
            raise ConfigurationError(
                f"{name} must be finite",
                error_code=error_codes.INVALID_COMMAND,
                details={"parameter": name, "value": value},
            )
        return float(value)

    @contextmanager
    def _operation_guard(self, xbot_id: int):
        with self.mover_utils.claim_operation(xbot_id):
            yield

    def _success(self, response, message: str):
        response.success = True
        response.error_code = error_codes.SUCCESS
        response.status_message = message
        return response
