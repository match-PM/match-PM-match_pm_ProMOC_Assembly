# real Hardware drive neccesary for hardware connection 

import time
import warnings
from typing import Optional, Tuple
import struct

# Try to import Thorlabs library
try:
    from pylablib.devices import Thorlabs
except ImportError as e:
    print(f"Error importing Thorlabs: {e}")
    Thorlabs = None # Set to None if import fails

from .linear_axis_driver import LinearAxisDriver

# Unterdrücke Pylablib Warnings beim Import
warnings.filterwarnings("ignore", message="can't recognize the stage name*")
warnings.filterwarnings("ignore", message="can't recognize motor model*")

ABSOLUTE_MAX_POSITION =300.0

class ThorlabsLTS300Driver(LinearAxisDriver):
    def __init__(self):
        self.device: Optional[Thorlabs.KinesisMotor] = None # type: ignore
        self.connected: bool = False
        self.serial_no: Optional[str] = None
        self.axis_type: Optional[str] = None
        self.device_units_per_mm: float = 409600.0 # Default value, can be overridden
        self.x_axis_serial: Optional[str] = None
        self.z_axis_serial: Optional[str] = None
        self.debug_mode: bool = False
        
        # Communication lock to prevent concurrent hardware access
        import threading
        self._comm_lock = threading.Lock()
        self._last_position_cache = 0.0
        self._last_position_time = 0.0

    def connect(self, port: str = None) -> bool:
        """Connect to the Thorlabs LTS300 device"""
        if Thorlabs is None:
            print("❌ Thorlabs library not available")
            return False
            
        try:
            if not port:
                print("❌ No port specified")
                return False
                
            print(f"🔗 Connecting to LTS300 on port {port}...")
            
            # Convert /dev/serial/by-id/... to /dev/ttyUSB* if needed
            actual_port = port
            if '/dev/serial/by-id/' in port:
                try:
                    import os
                    actual_port = os.readlink(port)
                    if not actual_port.startswith('/dev/'):
                        actual_port = '/dev/' + os.path.basename(actual_port)
                    print(f"🔄 Converted {port} to {actual_port}")
                except Exception as e:
                    print(f"⚠️ Could not resolve symlink: {e}")
                    # Fallback: try to find ttyUSB device
                    import glob
                    usb_devices = glob.glob('/dev/ttyUSB*')
                    if usb_devices:
                        actual_port = usb_devices[0]  # Take first available
                        print(f"🔄 Using fallback port: {actual_port}")
            
            # Now connect using the actual ttyUSB port
            self.device = Thorlabs.KinesisMotor(actual_port, scale="m")
            
            # Read the serial number from device
            device_info = self.device.get_device_info()
            self.serial_no = str(device_info[0])
            print(f"✅ Detected serial number: {self.serial_no}")
            
            self.connected = True
            print(f"✅ Connected to Thorlabs LTS300 (S/N: {self.serial_no}) on port {actual_port}")
            
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print(f"Exception type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            self.connected = False
            return False
            

    def disconnect(self):
        if self.connected and self.device:
            try:
                self.device.close()
                self.connected = False
                if self.debug_mode:
                    print('✅ Device disconnected')
            except Exception as e:
                if self.debug_mode:
                    print(f'❌ Error during shutdown: {e}')

    def move_absolute(self, position: float):
        if not self.connected or not self.device:
            raise ConnectionError("Device not connected.")
        if self.debug_mode:
            print(f'🔧 Moving to position: {position} mm')
        
        with self._comm_lock:
            # Start the movement
            self.device.move_to(position * self.device_units_per_mm, scale=False)
            
            # Wait for movement completion with robust error handling
            import time
            max_wait_time = 300.0  # 5 minutes maximum wait
            start_time = time.time()
            check_interval = 0.5   # Check every 500ms instead of 100ms
            
            while time.time() - start_time < max_wait_time:
                try:
                    if not self.device.is_moving():
                        break
                except Exception as e:
                    if self.debug_mode:
                        print(f'⚠️ Error checking movement status, continuing: {e}')
                    # If we can't check status, wait a bit and try again
                    time.sleep(check_interval * 2)
                
                time.sleep(check_interval)
            
            # Update position cache
            try:
                current_pos = self.device.get_position() / self.device_units_per_mm
                self._last_position_cache = current_pos
                self._last_position_time = time.time()
            except Exception as e:
                if self.debug_mode:
                    print(f'⚠️ Error updating position cache: {e}')

    def move_relative(self, distance: float):
        if not self.connected or not self.device:
            raise ConnectionError("Device not connected.")
        if self.debug_mode:
            print(f'🔧 Moving relatively by: {distance} mm')
        
        with self._comm_lock:
            current_position = self.device.get_position()
            target_position = current_position + (distance * self.device_units_per_mm)
            
            # Start the movement
            self.device.move_to(target_position, scale=False)
            
            # Wait for movement completion with robust error handling
            import time
            max_wait_time = 300.0  # 5 minutes maximum wait
            start_time = time.time()
            check_interval = 0.5   # Check every 500ms instead of 100ms
            
            while time.time() - start_time < max_wait_time:
                try:
                    if not self.device.is_moving():
                        break
                except Exception as e:
                    if self.debug_mode:
                        print(f'⚠️ Error checking movement status, continuing: {e}')
                    # If we can't check status, wait a bit and try again
                    time.sleep(check_interval * 2)
                
                time.sleep(check_interval)
            
            # Update position cache
            try:
                current_pos = self.device.get_position() / self.device_units_per_mm
                self._last_position_cache = current_pos
                self._last_position_time = time.time()
            except Exception as e:
                if self.debug_mode:
                    print(f'⚠️ Error updating position cache: {e}')

    def home(self, timeout: float = 180.0):
        """
        Home the device with configurable timeout.
        
        Args:
            timeout (float): Homing timeout in seconds (default: 180s)
        """
        if not self.connected or not self.device:
            raise ConnectionError("Device not connected.")
        if self.debug_mode:
            print(f'🔧 Homing device with {timeout}s timeout...')
        
        with self._comm_lock:
            # Use configurable timeout for homing operations
            # LTS300 can take up to 2+ minutes for full-range homing
            self.device.home(force=True, timeout=timeout)
            
            # Wait for homing completion with robust error handling
            import time
            max_wait_time = timeout + 30.0  # Add 30s buffer to device timeout
            start_time = time.time()
            check_interval = 1.0   # Check every 1s for homing
            
            while time.time() - start_time < max_wait_time:
                try:
                    if not self.device.is_moving():
                        break
                except Exception as e:
                    if self.debug_mode:
                        print(f'⚠️ Error checking homing status, continuing: {e}')
                    # If we can't check status, wait a bit and try again
                    time.sleep(check_interval * 2)
                
                time.sleep(check_interval)
            
            # Update position cache
            try:
                current_pos = self.device.get_position() / self.device_units_per_mm
                self._last_position_cache = current_pos
                self._last_position_time = time.time()
            except Exception as e:
                if self.debug_mode:
                    print(f'⚠️ Error updating position cache: {e}')

    def get_position(self) -> float:
        if not self.connected or not self.device:
            raise ConnectionError("Device not connected.")
        
        # Use cached position during operations to reduce hardware communication
        import time
        current_time = time.time()
        
        # Try to get lock without blocking for position queries
        if self._comm_lock.acquire(blocking=False):
            try:
                position = self.device.get_position() / self.device_units_per_mm
                self._last_position_cache = position
                self._last_position_time = current_time
                return position
            except Exception as e:
                if self.debug_mode:
                    print(f'⚠️ Error getting position: {e}')
                # Return cached position if available
                if hasattr(self, '_last_position_cache'):
                    return self._last_position_cache
                return -1.0
            finally:
                self._comm_lock.release()
        else:
            # Communication busy, return cached position if recent enough (< 2 seconds)
            if (hasattr(self, '_last_position_cache') and 
                hasattr(self, '_last_position_time') and
                current_time - self._last_position_time < 2.0):
                if self.debug_mode:
                    print(f'🔄 Using cached position: {self._last_position_cache:.2f}mm')
                return self._last_position_cache
            
            # No recent cache, wait briefly for lock
            if self._comm_lock.acquire(timeout=0.5):
                try:
                    position = self.device.get_position() / self.device_units_per_mm
                    self._last_position_cache = position
                    self._last_position_time = current_time
                    return position
                except Exception as e:
                    if self.debug_mode:
                        print(f'⚠️ Error getting position: {e}')
                    return self._last_position_cache if hasattr(self, '_last_position_cache') else -1.0
                finally:
                    self._comm_lock.release()
            else:
                # Still can't get lock, return cached value or error
                return self._last_position_cache if hasattr(self, '_last_position_cache') else -1.0

    def is_moving(self) -> bool:
        if not self.connected or not self.device:
            return False
        
        # Use timeout to avoid blocking indefinitely
        if self._comm_lock.acquire(timeout=0.3):
            try:
                moving_status = self.device.is_moving()
                return moving_status
            except Exception as e:
                # Handle Thorlabs communication errors gracefully
                if self.debug_mode:
                    print(f'⚠️ Error checking movement status: {e}')
                # Return False as safe default when we can't check status
                return False
            finally:
                self._comm_lock.release()
        else:
            # Can't acquire lock, assume still moving if we were recently
            return True

    def get_serial_number(self) -> str:
        return self.serial_no if self.serial_no else ""

    def get_axis_type(self) -> str:
        return self.axis_type if self.axis_type else "unknown"

    def determine_axis(self, serial_number: str):
        if serial_number == self.x_axis_serial:
            return 'x'
        elif serial_number == self.z_axis_serial:
            return 'z'
        else:
            return 'unknown'

    def update_position(self):
        # This method is called internally by the driver after movements
        # The actual position is retrieved by get_position()
        pass

    # New velocity control methods
    def get_velocity_parameters(self) -> Tuple[float, float, float]:
        """
        Get current velocity parameters (min_velocity, acceleration, max_velocity)
        Returns values in mm/s and mm/s^2
        """
        if not self.connected or not self.device:
            raise ConnectionError("Device not connected.")
        
        try:
            # Get velocity parameters from device (returns in device units)
            params = self.device.get_velocity_parameters(scale=False)
            
            # Convert from device units to mm/s and mm/s^2
            min_velocity = params.min_velocity / self.device_units_per_mm
            acceleration = params.acceleration / self.device_units_per_mm
            max_velocity = params.max_velocity / self.device_units_per_mm
            
            if self.debug_mode:
                print(f'🔧 Current velocity parameters:')
                print(f'   Min velocity: {min_velocity:.3f} mm/s')
                print(f'   Acceleration: {acceleration:.3f} mm/s²')
                print(f'   Max velocity: {max_velocity:.3f} mm/s')
            
            return (min_velocity, acceleration, max_velocity)
            
        except Exception as e:
            if self.debug_mode:
                print(f'❌ Error getting velocity parameters: {e}')
            # Return default safe values in case of error
            return (0.0, 1.0, 5.0)

    def set_velocity_parameters(self, min_velocity=None, acceleration=None, max_velocity=None) -> Tuple[float, float, float]:
        """
        Set velocity parameters. If any parameter is None, use current value.
        Parameters should be in mm/s and mm/s^2
        Returns the actual set parameters
        """
        if not self.connected or not self.device:
            raise ConnectionError("Device not connected.")
        
        try:
            # Get current parameters if some are not specified
            current_params = self.get_velocity_parameters()
            
            # Use current values for unspecified parameters
            if min_velocity is None:
                min_velocity = current_params[0]
            if acceleration is None:
                acceleration = current_params[1]
            if max_velocity is None:
                max_velocity = current_params[2]
            
            if self.debug_mode:
                print(f'🔧 Setting velocity parameters:')
                print(f'   Min velocity: {min_velocity:.3f} mm/s')
                print(f'   Acceleration: {acceleration:.3f} mm/s²')
                print(f'   Max velocity: {max_velocity:.3f} mm/s')
            
            # Convert to device units
            min_vel_device = int(min_velocity * self.device_units_per_mm)
            accel_device = int(acceleration * self.device_units_per_mm)
            max_vel_device = int(max_velocity * self.device_units_per_mm)
            
            # Set the parameters (scale=False means we're providing device units)
            self.device.setup_velocity(
                min_velocity=min_vel_device,
                acceleration=accel_device,
                max_velocity=max_vel_device,
                scale=False
            )
            
            if self.debug_mode:
                print('✅ Velocity parameters updated successfully')
                
            return self.get_velocity_parameters()
            
        except Exception as e:
            if self.debug_mode:
                print(f'❌ Error setting velocity parameters: {e}')
            raise

    def stop(self):
        """
        Immediately stop any ongoing movement.
        This is an emergency stop function that halts all motion.
        """
        if not self.connected or not self.device:
            raise ConnectionError("Device not connected.")
        
        # For emergency stop, try to acquire lock with timeout
        # If we can't get it quickly, force the stop anyway
        if self._comm_lock.acquire(timeout=0.1):
            try:
                if self.debug_mode:
                    print('🛑 Emergency stop requested - stopping all movement immediately')
                
                # Use pylablib's stop method for immediate halt
                # For KinesisMotor, the correct method is stop() not stop_motion()
                self.device.stop()
                
                if self.debug_mode:
                    print('✅ Movement stopped successfully')
                    
            except Exception as e:
                if self.debug_mode:
                    print(f'❌ Error during emergency stop: {e}')
                raise
            finally:
                self._comm_lock.release()
        else:
            # Emergency case - force stop even if lock is busy
            try:
                if self.debug_mode:
                    print('🛑 EMERGENCY STOP - forcing stop without lock')
                self.device.stop()
            except Exception as e:
                if self.debug_mode:
                    print(f'❌ Error during force stop: {e}')
                raise

    def jog_positive(self, step_size: float = 1.0):
        """
        Jog the axis in positive direction by the specified step size.
        
        Args:
            step_size (float): Distance to jog in mm (default: 1.0mm)
        """
        if not self.connected or not self.device:
            raise ConnectionError("Device not connected.")
        
        try:
            if self.debug_mode:
                print(f'🔧 Jogging positive by {step_size} mm')
            
            # Get current position and calculate target
            current_pos = self.get_position()
            target_pos = current_pos + step_size
            
            # Validate target position
            if not self.validate_position(target_pos):
                raise ValueError(f"Jog target position {target_pos:.2f}mm would exceed safety limits")
            
            # Use relative move for jogging
            self.move_relative(step_size)
            
        except Exception as e:
            if self.debug_mode:
                print(f'❌ Error during positive jog: {e}')
            raise

    def jog_negative(self, step_size: float = 1.0):
        """
        Jog the axis in negative direction by the specified step size.
        
        Args:
            step_size (float): Distance to jog in mm (default: 1.0mm)
        """
        if not self.connected or not self.device:
            raise ConnectionError("Device not connected.")
        
        try:
            if self.debug_mode:
                print(f'🔧 Jogging negative by {step_size} mm')
            
            # Get current position and calculate target
            current_pos = self.get_position()
            target_pos = current_pos - step_size
            
            # Validate target position
            if not self.validate_position(target_pos):
                raise ValueError(f"Jog target position {target_pos:.2f}mm would exceed safety limits")
            
            # Use relative move for jogging (negative distance)
            self.move_relative(-step_size)
            
        except Exception as e:
            if self.debug_mode:
                print(f'❌ Error during negative jog: {e}')
            raise


    def validate_position(self, position: float) -> bool:
        """
        Validate if position is within safe hardware limits.
        Uses conservative defaults to ensure safety.
        """
        # Use conservative safety limits
        min_position = 0.0
        max_position = min(300.0, ABSOLUTE_MAX_POSITION)
        
        if position < min_position or position > max_position:
            if self.debug_mode:
                print(f"❌ Position {position}mm outside limits [{min_position}, {max_position}]mm")
            return False
        return True