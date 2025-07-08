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
