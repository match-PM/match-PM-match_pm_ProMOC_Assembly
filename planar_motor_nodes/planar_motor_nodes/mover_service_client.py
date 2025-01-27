import rclpy
from rclpy.node import Node
from promoc_assembly_interfaces.srv import (
    LinearMotionSi,
    SixDofMotion,
    ArcMotionTargetRadius,
    RotaryMotion,
    StopMotion,
    SetVelocityAcceleration,
    LevitationXbots,
    ActivateXbots
)


class MoverServiceClient(Node):
    def __init__(self):
        super().__init__("mover_service_client")

        # Create service clients for each service
        self.linear_motion_client = self.create_client(LinearMotionSi, "mover_node/linear_mover_motion")
        self.six_d_motion_client = self.create_client(SixDofMotion, "mover_node/six_d_mover_motion")
        self.arc_motion_client = self.create_client(ArcMotionTargetRadius, "mover_node/arcmotion_target_radius")
        self.rotary_motion_client = self.create_client(RotaryMotion, "mover_node/rotary_motion")
        self.stop_motion_client = self.create_client(StopMotion, "mover_node/stop_motion")
        self.set_velocity_acceleration_client = self.create_client(SetVelocityAcceleration, "mover_node/set_velocity_acceleration")
        self.levitation_xbots_client = self.create_client(LevitationXbots, "mover_node/levitation_xbots")
        self.activate_xbots_client = self.create_client(ActivateXbots, "mover_node/activate_xbots")

        # Wait for the service clients to be ready
        while not self.linear_motion_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info("Linear motion service not available, waiting again...")
        while not self.six_d_motion_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info("Six-D motion service not available, waiting again...")
        # Add similar wait_for_service calls for other services...

    def call_linear_motion_service(self, xbot_id, x_pos, y_pos):
        request = LinearMotionSi.Request()
        request.xbot_id = xbot_id
        request.x_pos = x_pos
        request.y_pos = y_pos

        future = self.linear_motion_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)

        response = future.result()
        if response.finished:
            self.get_logger().info("Linear motion completed successfully")
        else:
            self.get_logger().error("Linear motion failed")

    # Add similar call_service functions for other services...


def main(args=None):
    rclpy.init(args=args)
    client = MoverServiceClient()

    # Call the service functions with desired parameters
    client.call_linear_motion_service(1, 0.5, 0.5)
    # Add similar calls for other services...

    rclpy.shutdown()


if __name__ == "__main__":
    main()