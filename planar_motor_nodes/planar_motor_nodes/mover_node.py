"""
ROS2 Node for XBot Mover Control (Planar Motor).

This module implements the MoverServiceNode - the central orchestrator
for controlling XBot planar motors via the PMC controller.

Architecture Overview:
======================
The node follows a dependency injection pattern for better testability:

    MoverServiceNode (Orchestrator)
        │
    ├── Config (dict)       → Configuration from ROS parameters (bounds, tolerances, mock mode)
        ├── PmcInterface        → Hardware abstraction (PMCLib wrapper)
        ├── MoverUtils          → Helper functions (position, conversions)
        └── ServiceCallbacks    → Business logic (motion processing)

Startup Sequence:
=================
1. Node Initialization
   └── Create ROS2 node, configure logger.

2. Configuration Loading
   └── Read parameters from ROS2 parameters (use_mock, xbot_id, bounds...).

3. Component Creation
   ├── PmcInterface  → Tries to load PMCLib (local → installed → mock).
   ├── MoverUtils    → Position tracking and conversions.
   └── ServiceCallbacks → Callback logic for all services.

4. ROS2 Service Registration
   └── linear_motion, six_dof_motion, activate, stop, etc.

5. PMC Connection
   └── Attempts to connect with retries (or uses mock mode).

6. System Activation
   └── Start XBot activation and levitation.

7. Timer Start
   └── Publish regular position updates.

Usage:
======
    # Start as a ROS2 node:
    ros2 run planar_motor_nodes mover_node

    # With mock mode (without hardware):
    ros2 run planar_motor_nodes mover_node --ros-args -p use_mock:=true

Example Service Calls:
======================
    # Move XBot linearly (in mm):
    ros2 service call /mover/linear_motion_si promoc_assembly_interfaces/srv/LinearMotionSI \\
        "{xbot_id: 0, target_x: 100.0, target_y: 50.0}"

    # Stop motion:
    ros2 service call /mover/stop_motion promoc_assembly_interfaces/srv/StopMotion \\
        "{xbot_id: 0}"
"""

import rclpy
import time
import math
from rclpy.node import Node
from promoc_assembly_interfaces.msg import XBotInfo
from promoc_assembly_interfaces.srv import (
    ActivateXbots, ArcMotionSi, LevitationXbots,
    LinearMotionSi, RotaryMotion, SetVelocityAcceleration,
    SixDofMotion, StopMotion
)

# Import our new, clean components
from .mover_pmc_interface import PmcInterface
from .mover_utils import MoverUtils
from .callbacks import ServiceCallbacks
from promoc_core.conversions import m_to_mm, mm_to_m, rad_to_deg, deg_to_rad
from promoc_core.promoc_exceptions import ConnectionError
from promoc_core.logging import TaggedLogger, LogTags


class MoverServiceNode(Node):
    """
    Central ROS2 node for planar motor control.

    This class is the "orchestrator" - it creates and coordinates all
    other components but does not handle business logic itself.

    How it works:
    -------------
    The node proceeds through the following phases on startup:

    1. INIT-PHASE:
       - ROS2 node is initialized.
       - Configuration is loaded from ROS parameters.
       - Components are created (PmcInterface, MoverUtils, ServiceCallbacks).

    2. SETUP-PHASE:
       - ROS2 services are registered (linear_motion, activate, stop, etc.).
       - Position publisher is created.

    3. CONNECT-PHASE:
       - Connection to the PMC controller is established.
       - On failure: retries with exponential backoff.
       - Mock mode: uses simulated movements.

    4. ACTIVATE-PHASE:
       - XBot is activated.
       - Levitation is started (motor floats above the stator).

    5. RUN-PHASE:
       - Position timer regularly publishes XBot position.
       - Services wait for incoming requests.

    Attributes:
        config (dict): Configuration (bounds, tolerances, XBot ID).
        pmc (PmcInterface): Hardware abstraction for the PMC controller.
        mover_utils (MoverUtils): Helper functions for position calculation.
        service_callbacks (ServiceCallbacks): Callback logic for services.
        xbot_info_publisher: ROS2 publisher for position updates.

    Example:
        # Automatic start via ROS2 launch or directly:
        node = MoverServiceNode()
        rclpy.spin(node)
    """

    def __init__(self):
        """
        Initializes the MoverServiceNode.

        Sequence (Step-by-Step):
        -------------------------
        1. Create ROS2 node named "mover_node".
        2. Load configuration from ROS parameters → Config (dict).
        3. Create components:
           - PmcInterface: Hardware connection.
           - MoverUtils: Helper functions.
           - ServiceCallbacks: Callback logic.
        4. Register ROS2 services.
        5. Start a connection timer (attempts to connect to PMC).
        """
        super().__init__("mover_node")
        
        # Setup TaggedLogger for this node
        self.log = TaggedLogger(self.get_logger(), LogTags.PMC)

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 1: Load Configuration
        # ══════════════════════════════════════════════════════════════════════
        # Loads all parameters (use_mock, xbot_id, bounds) from ROS parameters
        self.config = self._load_config()
        self.is_connected = False

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 2: Create Components (Dependency Injection)
        # ══════════════════════════════════════════════════════════════════════
        # Each component gets its dependencies passed in explicitly.
        # This makes the system testable and the dependencies clear.
        
        # PMC Interface gets specific [PMC:CONN] logger
        self.pmc = PmcInterface(
            TaggedLogger(self.get_logger(), LogTags.PMC_CONN), 
            use_mock=self.config['use_mock']
        )
        
        # MoverUtils gets node logger [PMC]
        self.mover_utils = MoverUtils(self.log, self.pmc, self.config)
        
        # ServiceCallbacks gets raw logger (it wraps it internally with [PMC:MOTION])
        self.callbacks = ServiceCallbacks(
            self.get_logger(), self.pmc, self.mover_utils, self.config)
            
        self.xbot_pos_publisher = self.create_publisher(
            XBotInfo, "xbot_info", 10)

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 3: Register ROS2 Services
        # ══════════════════════════════════════════════════════════════════════
        self._setup_services()

        # ══════════════════════════════════════════════════════════════════════
        # PHASE 4: Start Connection Timer
        # ══════════════════════════════════════════════════════════════════════
        # Timer tries to connect to the PMC controller every 100ms.
        # On success, it stops itself and activates the system.
        self.log.info(
            f"Connecting to PMC at {self.config['pmc_ip']}...")
        self.connection_timer = self.create_timer(0.1, self._try_connect)

        self.log.info("Mover Service Node initialized. Waiting for PMC connection...")

    def _try_connect(self):
        """
        Attempts to establish a connection to the PMC controller.

        Called by the connection_timer every 100ms until a connection is made.
        On success, the timer is stopped and the system is activated.

        Flow:
        -----
        1. Attempt connection via PmcInterface.connect().
        2. On success:
           - Stop the timer.
           - Activate the system (_activate_system).
        3. On failure:
           - Log at debug level (to avoid spamming the console).
           - Next attempt in 100ms.
        """
        try:
            while not self.is_connected:
                self.is_connected = self.pmc.connect(self.config['pmc_ip'])
            self.log.info("PMC Connected! Activating system.")

            # Stop the timer - connection is established
            self.connection_timer.cancel()

            # Activate the system (XBots + publisher)
            self._activate_system()

        except Exception as e:
            # Debug level to avoid spam during startup
            self.log.debug(f"Connection attempt failed: {e}")

    def _activate_system(self):
        """
        Activates the XBot system after a successful PMC connection.

        Flow:
        -----
        1. Activate XBots (puts hardware in a ready state).
        2. Start the position publisher timer (for regular updates).
        """
        try:
            self.pmc.bot.activate_xbots()
            self.log.info("XBot Activated")
            self._start_publisher_timer()
        except Exception as e:
            self.log.error(
                f"Failed to activate XBots after connection: {e}")

    def _load_config(self) -> dict:
        """
        Loads configuration from ROS parameters.

        Parameters are declared with defaults and can be overridden via
        launch files or the command line.

        Returns:
            dict: A dictionary with all configuration values.

        Parameter Categories:
        ---------------------
        1. General:
           - use_mock: True for simulation without hardware.
           - xbot_id: ID of the XBot to control.
           - pmc_ip: IP address of the PMC controller.

        2. Movement Boundaries (in meters):
           - x_min/x_max: X-axis limits.
           - y_min/y_max: Y-axis limits.
           - z_min/z_max: Z-axis (levitation) limits.

        3. Tolerances (in meters):
           - xy_tolerance: Accuracy for XY positioning.
           - six_d_tolerance: Accuracy for 6-DOF movements.
        """
        # Declare all parameters with their default values
        self.declare_parameter('use_mock', False)
        self.declare_parameter('xbot_id', 0)
        self.declare_parameter('publish_rate', 10.0)
        self.declare_parameter('pmc_ip', '192.168.10.100')

        # Movement boundaries and tolerances
        self.declare_parameter('xy_tolerance', 0.001)
        self.declare_parameter('six_d_tolerance', 0.001)
        self.declare_parameter('x_min', 0.055)
        self.declare_parameter('x_max', 0.420)
        self.declare_parameter('y_min', 0.055)
        self.declare_parameter('y_max', 0.180)
        self.declare_parameter('z_min', 0.000)
        self.declare_parameter('z_max', 0.004)

        config = {
            'use_mock': self.get_parameter('use_mock').value,
            'xbot_id': self.get_parameter('xbot_id').value,
            'publish_rate': self.get_parameter('publish_rate').value,
            'pmc_ip': self.get_parameter('pmc_ip').value,
            'xy_tolerance': self.get_parameter('xy_tolerance').value,
            'six_d_tolerance': self.get_parameter('six_d_tolerance').value,
            'x_min': self.get_parameter('x_min').value,
            'x_max': self.get_parameter('x_max').value,
            'y_min': self.get_parameter('y_min').value,
            'y_max': self.get_parameter('y_max').value,
            'z_min': self.get_parameter('z_min').value,
            'z_max': self.get_parameter('z_max').value,
        }

        self.log.info(f"Configuration loaded: {config}")
        return config

    def _setup_services(self):
        """
        Registers all ROS2 services for mover control.

        Available Services:
        --------------------
        - linear_motion_si: Linear XY motion (mm).
        - six_dof_motion: 6-DOF motion (X,Y,Z,Rx,Ry,Rz).
        - activate_xbots: Activate XBot.
        - levitation_xbots: Start/stop levitation.
        - arc_motion_si: Arc-shaped motion.
        - stop_motion: Stop motion.
        - rotary_motion: Rotational motion (Rz).
        - set_velocity_acceleration: Set velocity/acceleration.

        Each service is created with the node name as a prefix,
        e.g., /mover_node/linear_motion_si
        """
        services = [
            ('linear_motion_si', LinearMotionSi,
             self.callbacks.callback_linear_motion_si),
            ('six_dof_motion', SixDofMotion, self.callbacks.callback_six_d_motion),
            ('activate_xbots', ActivateXbots,
             self.callbacks.callback_activate_xbot),
            ('levitation_xbots', LevitationXbots,
             self.callbacks.callback_levitation_xbot),
            ('arc_motion_si', ArcMotionSi, self.callbacks.callback_arc_motion_si),
            ('stop_motion', StopMotion, self.callbacks.callback_stop_motion),
            ('rotary_motion', RotaryMotion, self.callbacks.callback_rotary_motion),
            ('set_velocity_acceleration', SetVelocityAcceleration,
             self.callbacks.callback_set_velocity_acceleration)
        ]
        for name, srv_type, callback in services:
            self.create_service(
                srv_type, f"{self.get_name()}/{name}", callback)
        self.log.info("All services are created.")

    def _start_publisher_timer(self):
        """
        Starts timers for periodic position updates.

        This is called only after a successful PMC connection.

        Timers:
        -------
        1. Position Timer: Publishes XBot position (default: 10 Hz).
        2. Diagnosis Timer: Checks XBot availability every 5s (only on real hardware).
        """
        publish_interval = 1.0 / self.config['publish_rate']
        self.xbot_position_timer = self.create_timer(
            publish_interval, self._publish_xbot_position)
        if not self.pmc.status['is_mock']:
            self.xbot_diagnosis_timer = self.create_timer(
                5.0, self.mover_utils.diagnose_xbot_availability)
        self.log.info("Timers started.")

    def _publish_xbot_position(self):
        """
        Publishes the current XBot position as an XBotInfo message.

        Converts internal SI units to user-friendly units:
        - Position: meters → millimeters
        - Angle: radians → degrees
        """
        if not self.is_connected:
            return

        msg = XBotInfo()
        try:
            current_pos = self.mover_utils.get_current_position(0)
            if current_pos:
                # Convert: m → mm, rad → deg
                msg.x_pos = m_to_mm(current_pos[0])
                msg.y_pos = m_to_mm(current_pos[1])
                msg.z_pos = m_to_mm(current_pos[2])
                msg.rx_pos = rad_to_deg(current_pos[3])
                msg.ry_pos = rad_to_deg(current_pos[4])
                msg.rz_pos = rad_to_deg(current_pos[5])

            msg.xbot_state = self.mover_utils.get_xbot_state_string(0)
            self.xbot_pos_publisher.publish(msg)
        except Exception as e:
            self.log.error(f"Position publishing error: {e}")

    def destroy_node(self):
        """Clean shutdown."""
        self.log.info("Shutting down MoverServiceNode...")
        if self.is_connected:
            try:
                self.pmc.bot.deactivate_xbots()
                self.log.info("XBots deactivated.")
            except Exception as e:
                self.log.error(f"Error during deactivation: {e}")
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MoverServiceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
