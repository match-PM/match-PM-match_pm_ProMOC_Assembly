"""Shared base classes and aliases for planar motor service callbacks."""

from __future__ import annotations

from dataclasses import dataclass

from promoc_core.logging import LogTags, TaggedLogger
from promoc_core.promoc_exceptions import ConfigurationError, SafetyError

from ...config import MoverNodeConfig
from ...domain.logic import MoverUtils
from ...drivers.hardware import PmcInterface


InvalidParameterError = ConfigurationError
ParameterValidationError = ConfigurationError
PositionOutOfBoundsError = SafetyError


@dataclass(frozen=True)
class ServiceRegistration:
    """Declarative service binding for mover node callback wiring."""

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
            f"ServiceCallbacks initialized. Using PMCLib: {self.pmc.status['source']}"
        )
