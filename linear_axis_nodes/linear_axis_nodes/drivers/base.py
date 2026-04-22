"""
Abstract Base Class for Linear Axis Drivers.

This module defines the interface that all linear axis drivers must implement.
It provides a consistent API for controlling linear motion stages regardless
of the underlying hardware.

Implementations:
    - ThorlabsLTS300Driver: Real hardware driver for Thorlabs LTS300 stages
    - SimulatedLinearAxisDriver: Simulated driver for testing without hardware
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple


class LinearAxisDriver(ABC):
    """
    Abstract base class defining the interface for linear axis drivers.
    
    All concrete driver implementations must inherit from this class and
    implement all abstract methods to ensure consistent behavior across
    different hardware platforms.
    
    Attributes:
        connected (bool): Connection status to the hardware
        serial_no (str): Device serial number
        axis_type (str): Axis type identifier ('x', 'z', or 'unknown')
    """
    
    # ========================================================================
    # Connection Methods
    # ========================================================================
    
    @abstractmethod
    def connect(self, port: str = None) -> bool:
        """
        Connect to the linear axis device.
        
        Args:
            port: Serial port or device path (e.g., '/dev/ttyUSB0')
                  Can be None for simulated devices.
        
        Returns:
            bool: True if connection successful, False otherwise
            
        Raises:
            DeviceNotFoundError: If device cannot be found
            DriverNotAvailableError: If required driver library is not available
            HardwareError: If connection fails due to hardware issues
        """
        pass

    @abstractmethod
    def disconnect(self):
        """
        Disconnect from the device and cleanup resources.
        
        This should be called when the node shuts down to ensure
        proper cleanup of hardware connections.
        """
        pass

    # ========================================================================
    # Motion Control Methods
    # ========================================================================

    @abstractmethod
    def move_absolute(self, position: float):
        """
        Move to an absolute position.
        
        Args:
            position: Target position in millimeters
            
        Raises:
            CommunicationError: If device is not connected
            MovementTimeoutError: If movement times out
            HardwareError: If movement command fails
        """
        pass

    @abstractmethod
    def move_relative(self, distance: float):
        """
        Move a relative distance from current position.
        
        Args:
            distance: Distance to move in millimeters (positive or negative)
            
        Raises:
            CommunicationError: If device is not connected
            MovementTimeoutError: If movement times out
            HardwareError: If movement command fails
        """
        pass

    @abstractmethod
    def home(self, timeout: float = 180.0):
        """
        Home the axis to its reference position.
        
        Args:
            timeout: Maximum time to wait for homing in seconds
            
        Raises:
            CommunicationError: If device is not connected
            HomingFailedError: If homing operation fails or times out
        """
        pass

    @abstractmethod
    def stop(self):
        """
        Emergency stop - immediately halt any ongoing motion.
        
        This is a safety-critical function that should halt motion
        as quickly as possible.
        
        Raises:
            CommunicationError: If device is not connected
            HardwareError: If stop command fails
        """
        pass

    # ========================================================================
    # Jog Methods
    # ========================================================================

    @abstractmethod
    def jog_positive(self, step_size: float = 1.0):
        """
        Jog the axis in positive direction by the specified step size.
        
        Args:
            step_size: Distance to jog in mm (default: 1.0mm)
            
        Raises:
            CommunicationError: If device is not connected
            SoftLimitViolationError: If jog would exceed limits
            HardwareError: If jog command fails
        """
        pass

    @abstractmethod
    def jog_negative(self, step_size: float = 1.0):
        """
        Jog the axis in negative direction by the specified step size.
        
        Args:
            step_size: Distance to jog in mm (default: 1.0mm)
            
        Raises:
            CommunicationError: If device is not connected
            SoftLimitViolationError: If jog would exceed limits
            HardwareError: If jog command fails
        """
        pass

    # ========================================================================
    # Status Methods
    # ========================================================================

    @abstractmethod
    def get_position(self) -> float:
        """
        Get current position in millimeters.
        
        Returns:
            float: Current position in mm, or -1.0 if error
            
        Raises:
            CommunicationError: If device is not connected
        """
        pass

    @abstractmethod
    def is_moving(self) -> bool:
        """
        Check if axis is currently in motion.
        
        Returns:
            bool: True if axis is moving, False otherwise
        """
        pass

    @abstractmethod
    def get_serial_number(self) -> str:
        """
        Get the device serial number.
        
        Returns:
            str: Device serial number, or empty string if not available
        """
        pass

    @abstractmethod
    def get_axis_type(self) -> str:
        """
        Get the axis type identifier.
        
        Returns:
            str: Axis type ('x', 'z', or 'unknown')
        """
        pass

    # ========================================================================
    # Velocity Parameter Methods
    # ========================================================================

    @abstractmethod
    def get_velocity_parameters(self) -> Tuple[float, float, float]:
        """
        Get current velocity parameters.
        
        Returns:
            Tuple of (min_velocity, acceleration, max_velocity) in mm/s and mm/s²
            
        Raises:
            CommunicationError: If device is not connected
        """
        pass

    @abstractmethod
    def set_velocity_parameters(
        self, 
        min_velocity: Optional[float] = None, 
        acceleration: Optional[float] = None, 
        max_velocity: Optional[float] = None
    ) -> Tuple[float, float, float]:
        """
        Set velocity parameters.
        
        Args:
            min_velocity: Minimum velocity in mm/s (None to keep current)
            acceleration: Acceleration in mm/s² (None to keep current)
            max_velocity: Maximum velocity in mm/s (None to keep current)
            
        Returns:
            Tuple of actual set parameters (min_velocity, acceleration, max_velocity)
            
        Raises:
            CommunicationError: If device is not connected
            HardwareError: If parameter setting fails
        """
        pass

    # ========================================================================
    # Validation Methods
    # ========================================================================

    @abstractmethod
    def validate_position(self, position: float) -> bool:
        """
        Validate if a position is within safe hardware limits.
        
        Args:
            position: Position to validate in mm
            
        Returns:
            bool: True if position is valid, False otherwise
        """
        pass
