"""Administrative and status callbacks for linear-axis services."""

from __future__ import annotations

from promoc_core.error_handling import handle_service_errors

from ..config import LTS300NodeConfig
from ..models import OperationStateStore, OperationStatus


class LinearAdminCallbacks:
    """Callbacks for status and configuration services."""

    def __init__(
        self,
        logger,
        *,
        driver,
        config: LTS300NodeConfig,
        state_store: OperationStateStore,
    ):
        self.logger = logger
        self.driver = driver
        self.config = config
        self.state_store = state_store

    def _device_units_to_mm_per_s(self, device_units: float) -> float:
        return device_units * self.config.velocity_conversion_factor

    def _mm_per_s_to_device_units(self, mm_per_s: float) -> float:
        return mm_per_s / self.config.velocity_conversion_factor

    def get_operation_status(self) -> tuple[OperationStatus, str]:
        return self.state_store.get()

    @handle_service_errors()
    def callback_get_position(self, request, response):
        response.axis_position = float(self.driver.get_position())
        response.success = True

        status, status_message = self.get_operation_status()
        if status != OperationStatus.IDLE:
            response.status_message = (
                f"Position: {response.axis_position:.2f}mm | Status: {status_message}"
            )
        else:
            response.status_message = "Position retrieved"
        return response

    @handle_service_errors()
    def callback_set_velocity_parameters(self, request, response):
        min_vel = (
            None
            if request.min_velocity < 0
            else self._mm_per_s_to_device_units(request.min_velocity)
        )
        accel = (
            None
            if request.acceleration < 0
            else self._mm_per_s_to_device_units(request.acceleration)
        )
        max_vel = (
            None
            if request.max_velocity < 0
            else self._mm_per_s_to_device_units(request.max_velocity)
        )

        result = self.driver.set_velocity_parameters(min_vel, accel, max_vel)
        response.success = True
        response.status_message = "Velocity parameters updated"

        if result:
            response.actual_min_velocity = self._device_units_to_mm_per_s(result[0])
            response.actual_acceleration = self._device_units_to_mm_per_s(result[1])
            response.actual_max_velocity = self._device_units_to_mm_per_s(result[2])
        return response

    @handle_service_errors()
    def callback_get_velocity_parameters(self, request, response):
        params = self.driver.get_velocity_parameters()
        response.success = True
        response.status_message = "Velocity parameters retrieved"

        if params is not None:
            response.min_velocity = self._device_units_to_mm_per_s(params[0])
            response.acceleration = self._device_units_to_mm_per_s(params[1])
            response.max_velocity = self._device_units_to_mm_per_s(params[2])
        return response

    @handle_service_errors()
    def callback_shutdown(self, request, response):
        self.logger.info("Shutdown requested. Homing device before disconnect...")
        self.driver.home(timeout=float(self.config.homing_timeout))
        self.driver.disconnect()
        self.state_store.set(OperationStatus.IDLE, "Device disconnected")

        response.success = True
        response.status_message = "Device homed and disconnected successfully."
        return response

    @handle_service_errors()
    def callback_get_operation_status(self, request, response):
        status, status_message = self.get_operation_status()
        response.success = True
        response.operation_status = status.value
        response.status_message = status_message
        return response
