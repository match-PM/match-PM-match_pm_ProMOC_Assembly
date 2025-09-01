from .lts300_interface import Lts300Interface
from .node_config import Lts300Config

class ServiceCallbacks:
    """
    Handles all ROS service callback logic for the LTS300 node, decoupled from the ROS node.
    This class contains the business logic for motion commands and other services.
    """

    def __init__(self, logger, interface: Lts300Interface, config: Lts300Config):
        """
        Initializes the callbacks with explicit dependencies.

        Args:
            logger: The ROS 2 logger instance.
            interface: The hardware interface for the LTS300 driver.
            config: The dataclass holding all node parameters.
        """
        self.logger = logger
        self.interface = interface
        self.config = config
        self.driver = self.interface.driver  # Direct access to the driver instance

    def _collision_check(self, other_axis_position: float) -> bool:
        """
        Checks for a potential collision using the current position of the other axis.
        
        Args:
            other_axis_position (float): The current position of the other axis, passed in by the node.
        """
        if (other_axis_position is not None and
                other_axis_position > self.config.collision_threshold):
            return True
        return False

    # --- Service Callback Implementations ---

    def callback_move_absolute(self, request, response, other_axis_position: float):
        """Handle absolute movement, receiving the other axis position as an argument."""
        if self._collision_check(other_axis_position):
            response.success = False
            response.status_message = f"⚠️ Collision risk! Other axis at {other_axis_position:.2f}mm > {self.config.collision_threshold}mm."
            self.logger.warn(response.status_message)
            return response

        try:
            self.logger.info(f'Moving to absolute position: {request.axis_position} mm')
            self.driver.move_absolute(request.axis_position)
            response.success = True
            response.status_message = f"✅ Moved to {self.driver.get_position():.2f} mm"
        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error in move_absolute: {str(e)}"
            self.logger.error(response.status_message)
        return response

    def callback_move_relative(self, request, response, other_axis_position: float):
        """Handle relative movement requests."""
        if self._collision_check(other_axis_position):
            response.success = False
            response.status_message = f"⚠️ Collision risk! Other axis at {other_axis_position:.2f}mm > {self.config.collision_threshold}mm."
            self.logger.warn(response.status_message)
            return response
            
        try:
            self.logger.info(f'Moving by relative distance: {request.axis_position} mm')
            self.driver.move_relative(request.axis_position)
            response.success = True
            response.status_message = f"✅ Moved to {self.driver.get_position():.2f} mm"
        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error in move_relative: {str(e)}"
            self.logger.error(response.status_message)
        return response

    def callback_home(self, request, response):
        """Handle homing requests."""
        try:
            self.logger.info('Homing device...')
            self.driver.home()
            response.success = True
            response.status_message = "✅ Homing completed"
        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error during homing: {str(e)}"
            self.logger.error(response.status_message)
        return response

    def callback_get_position(self, request, response):
        """Handle get position requests."""
        try:
            response.axis_position = self.driver.get_position()
            response.success = True
            response.status_message = "✅ Position retrieved"
        except Exception as e:
            response.axis_position = -1.0
            response.success = False
            response.status_message = f"❌ Error getting position: {str(e)}"
            self.logger.error(response.status_message)
        return response
        
    def callback_set_velocity_parameters(self, request, response):
        """Handle velocity parameter setting requests."""
        try:
            min_vel = None if request.min_velocity < 0 else request.min_velocity
            accel = None if request.acceleration < 0 else request.acceleration
            max_vel = None if request.max_velocity < 0 else request.max_velocity
            
            result = self.driver.set_velocity_parameters(min_vel, accel, max_vel)
            
            response.success = True
            response.status_message = "✅ Velocity parameters updated"
            response.actual_min_velocity, response.actual_acceleration, response.actual_max_velocity = result
        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error setting velocity: {str(e)}"
            self.logger.error(response.status_message)
        return response

    def callback_get_velocity_parameters(self, request, response):
        """Handle velocity parameter query requests."""
        try:
            params = self.driver.get_velocity_parameters()
            response.success = True
            response.status_message = "✅ Velocity parameters retrieved"
            response.min_velocity, response.acceleration, response.max_velocity = params
        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error getting velocity: {str(e)}"
            self.logger.error(response.status_message)
        return response

    def callback_shutdown(self, request, response):
        """Handle shutdown requests by homing and disconnecting."""
        try:
            self.logger.info("Shutdown requested. Homing device before disconnect...")
            self.driver.home()
            self.interface.disconnect() # Use the interface to manage connection state
            response.success = True
            response.status_message = "✅ Device homed and disconnected successfully."
        except Exception as e:
            response.success = False
            response.status_message = f"❌ Error during shutdown: {str(e)}"
            self.logger.error(response.status_message)
        return response

