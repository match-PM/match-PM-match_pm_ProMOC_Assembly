"""Shared base classes and service registration for planar motor services."""

from __future__ import annotations

from dataclasses import dataclass

from promoc_core.logging import LogTags, TaggedLogger
from promoc_core.promoc_exceptions import ConfigurationError, SafetyError

from ..config import MoverNodeConfig
from ..drivers.hardware import PmcInterface
from .status import MoverUtils


InvalidParameterError = ConfigurationError
ParameterValidationError = ConfigurationError
PositionOutOfBoundsError = SafetyError


@dataclass(frozen=True)
class ServiceRegistration:
    """Declarative service binding for mover callback wiring."""

    service_name: str
    callback_name: str


class ServiceCallbacksBase:
    """Shared constructor and dependencies for planar motor callbacks."""

    NO_CHANGE = -999999

    def __init__(
        self,
        logger,
        pmc_interface: PmcInterface,
        mover_utils: MoverUtils,
        config: MoverNodeConfig,
    ):
        self.logger = TaggedLogger(logger, LogTags.PMC_MOTION)
        self.pmc = pmc_interface
        self.mover_utils = mover_utils
        self.config = config
        self.logger.info(
            f"Service callbacks initialized. Using PMCLib: {self.pmc.status['source']}"
        )
