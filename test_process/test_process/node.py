from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from promoc_assembly_interfaces.msg import DeviceStatus
from promoc_assembly_interfaces.srv import (
    EmergencyStop,
    GetOperationStatus,
    GetPosition,
    GetVelocityParameters,
    Home,
    JogAxis,
    MoveAbsolute,
    MoveRelative,
    SetVelocityParameters,
    ShutdownLinearAxis,
    Stop,
    LinearMotionSi,
)
from promoc_core import error_codes
from promoc_core.promoc_exceptions import (
    CommunicationError,
    ConnectionError,
    DriverNotAvailableError,
    MovementTimeoutError,
    ProMocError,
    SafetyError,
)
from promoc_core.status import AxisState, DeviceState
import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import Float64


class AxisOperationError(Exception):
    """Structured controller error that maps directly to service responses."""

    def __init__(self, error_code: int, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.message = message


@dataclass(frozen=True)
class AxisSnapshot:
    """Current state published and returned by query services."""

    connected: bool
    device_state: DeviceState
    axis_state: AxisState
    operation_status: str
    error_code: int
    status_message: str
    position_mm: float


class ProcessClient(Node):
    """Client for interacting with linear axis nodes."""

    def __init__(self):
        super().__init__("process_client")
        self.x_axis_jog_client = self.create_client(
            JogAxis, "/x_axis/jog_axis"
        )

        self.linear_pm_client = self.create_client(
            LinearMotionSi, "/mover/linear_motion_si"

        )



        self.get_logger().info("Process client initialized")
        


        self.axisreq = JogAxis.Request()

               
        
        
        
 
        def move_axis(self, step_size: float) -> bool:
            self.axisreq.StepSize = step_size   
            self.x_axis_jog_client.call_async(self.axisreq)

        self.linearrquest = LinearMotionSi.Request()
        self.linearrquest.x_pos = 10.0
        self.linearrquest.y_pos = 60
        self.linearrquest.xbot_id = 0


        self.create_service(start_process, "start_process", self.start_process_callback)




        def start_process_callback(self, request, response):
            self.get_logger().info("Starting process...")
            self.move_axis(10.0)  # Move X-axis by 10mm
            self.move_axis(10.0)  # Move X-axis by 10mm
            self.move_axis(10.0)  # Move X-axis by 10mm
            self.move_axis(10.0)  # Move X-axis by 10mm
            self.move_axis(10.0)  # Move X-axis by 10mm
            self.
            sleep(9)
        
        self.linear_pm_client.call_async(self.linearrquest)


def main(args=None) -> None:
    rclpy.init(args=args)
    client = ProcessClient()
    
    # Example: Jog X-axis by 10mm
    success = client.jog_x_axis(step_size=10.0)
    
    if success:
        client.get_logger().info("X-axis jog completed successfully")
    else:
        client.get_logger().error("X-axis jog failed")
    
    client.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()