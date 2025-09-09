# abstract base class for linear axis drivers with all necessary methods

from abc import ABC, abstractmethod


class LinearAxisDriver(ABC):
    @abstractmethod
    def connect(self, serial_port: str, x_axis_serial: str, z_axis_serial: str, debug_mode: bool):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def move_absolute(self, position: float):
        pass

    @abstractmethod
    def move_relative(self, distance: float):
        pass

    @abstractmethod
    def home(self):
        pass

    @abstractmethod
    def get_position(self) -> float:
        pass

    @abstractmethod
    def is_moving(self) -> bool:
        pass

    @abstractmethod
    def get_serial_number(self) -> str:
        pass

    @abstractmethod
    def get_axis_type(self) -> str:
        pass

    @abstractmethod
    def get_velocity_parameters(self) -> tuple:
        """Get current velocity parameters (min_velocity, acceleration, max_velocity)"""
        pass

    @abstractmethod
    def set_velocity_parameters(self, min_velocity=None, acceleration=None, max_velocity=None):
        """Set velocity parameters. If any parameter is None, use current value."""
        pass

    @abstractmethod
    def stop(self):
        """Emergency stop - immediately halt any motion."""
        pass

    @abstractmethod
    def set_jog_parameters(self, step_size: float, speed: float = None) -> tuple:
        """
        Set jog parameters.

        Args:
            step_size: Jog step size in mm (must be positive)
            speed: Jog speed in mm/s (optional, None to keep current)

        Returns:
            tuple: (actual_step_size, actual_speed) - actual values set by driver
        """
        pass

    @abstractmethod
    def get_jog_parameters(self) -> tuple:
        """
        Get current jog parameters.

        Returns:
            tuple: (step_size, speed) - current jog step size in mm and speed in mm/s
        """
        pass

    @abstractmethod
    def get_jog_step_size(self) -> float:
        """
        Get current jog step size.

        Returns:
            float: Current jog step size in mm
        """
        pass

    @abstractmethod
    def jog_step(self, direction: int):
        """
        Execute a single jog step.

        Args:
            direction: Direction (±1) - positive = forward, negative = backward
        """
        pass
