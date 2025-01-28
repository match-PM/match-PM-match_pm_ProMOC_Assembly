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

    def call_six_d_motion_service(self, xbot_id, x_pos, y_pos, z_pos, rx_pos, ry_pos, rz_pos):
        request = SixDofMotion.Request()
        request.xbot_id = xbot_id
        request.x_pos = x_pos
        request.y_pos = y_pos
        request.z_pos = z_pos
        request.rx_pos = rx_pos
        request.ry_pos = ry_pos
        request.rz_pos = rz_pos

        future = self.six_d_motion_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)

        response = future.result()
        if response.finished:
            self.get_logger().info("Six-D motion completed successfully")
        else:
            self.get_logger().error("Six-D motion failed")

    def call_arc_motion_service(self, xbot_id, x_pos, y_pos, arc_type, postion_mode, arc_dir, radius_meters, xy_max_speed, xy_max_accl, final_speed):
        request = ArcMotionTargetRadius.Request()
        request.xbot_id = xbot_id
        request.x_pos = x_pos
        request.y_pos = y_pos
        request.arc_type = arc_type
        request.postion_mode = postion_mode
        request.arc_dir = arc_dir
        request.radius_meters = radius_meters
        request.xy_max_speed = xy_max_speed
        request.xy_max_accl = xy_max_accl
        request.final_speed = final_speed

        future = self.arc_motion_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)

        response = future.result()
        if response.finished:
            self.get_logger().info("Arc motion completed successfully")
        else:
            self.get_logger().error("Arc motion failed")

    def call_rotary_motion_service(self, xbot_id, target_rz, max_rz_speed, max_accel_rz):
        request = RotaryMotion.Request()
        request.xbot_id = xbot_id
        request.target_rz = target_rz
        request.max_rz_speed = max_rz_speed
        request.max_accel_rz = max_accel_rz

        future = self.rotary_motion_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)

        response = future.result()
        if response.finished:
            self.get_logger().info("Rotary motion completed successfully")
        else:
            self.get_logger().error("Rotary motion failed")

    def call_stop_motion_service(self, xbot_id):
        request = StopMotion.Request()
        request.xbot_id = xbot_id

        future = self.stop_motion_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)

        response = future.result()
        if response.finished:
            self.get_logger().info("Motion stopped successfully")
        else:
            self.get_logger().error("Failed to stop motion")

    def call_set_velocity_acceleration_service(self, xbot_id, xy_vel, xy_max_accel, z_vel, z_max_accel,rx_vel,ry_vel,rz_vel):
        request = SetVelocityAcceleration.Request()
        request.xbot_id = xbot_id
        request.xy_vel = xy_vel
        request.xy_max_accel = xy_max_accel
        request.z_vel = z_vel
        request.z_max_accel = z_max_accel
        request.rx_vel = rx_vel
        request.ry_vel = ry_vel
        request.rz_vel = rz_vel

        future = self.set_velocity_acceleration_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)

        response = future.result()
        if response.finished:
            self.get_logger().info("Velocity and acceleration set successfully")
        else:
            self.get_logger().error("Failed to set velocity and acceleration")

    def call_levitation_xbots_service(self, xbot_id, levitation):
        request = LevitationXbots.Request()
        request.xbot_id = xbot_id
        request.levitation = levitation

        future = self.levitation_xbots_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)

        response = future.result()
        if response.finished:
            self.get_logger().info("XBot levitation completed successfully")
        else:
            self.get_logger().error("Failed to levitate XBot")

    def call_activate_xbots_service(self, xbot_id, activate):
        request = ActivateXbots.Request()
        request.xbot_id = xbot_id
        request.activation_status = activate

        future = self.activate_xbots_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)

        response = future.result()
        if response.finished:
            self.get_logger().info("XBot activation completed successfully")
        else:
            self.get_logger().error("Failed to activate XBot")


def main(args=None):
    rclpy.init(args=args)
    client = MoverServiceClient()

    rclpy.shutdown()


if __name__ == "__main__":
    main()