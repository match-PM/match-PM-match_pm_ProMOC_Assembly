#!/usr/bin/env python3
# filepath: /home/soc/Development/Ros2/promoc_assembly/src/match-PM-match_pm_ProMOC_Assembly/promoc_bringup/promoc_bringup/demo_controller.py

import rclpy
from rclpy.node import Node
import time
import threading

# Import service interfaces
from promoc_assembly_interfaces.srv import (
    ActivateXbots,
    LevitationXbots,
    LinearMotionSi
)


class DemoController(Node):
    def __init__(self):
        super().__init__('demo_controller')
        self.get_logger().info('🚀 Demo Controller started!')

        # Service Clients erstellen
        self.activate_client = self.create_client(
            ActivateXbots, '/mover_node/activate_xbots')
        self.levitation_client = self.create_client(
            LevitationXbots, '/mover_node/levitation_xbots')
        self.linear_motion_client = self.create_client(
            LinearMotionSi, '/mover_node/linear_mover_motion')

        # LTS300 Clients (falls verfügbar)
        self.lts300_x_client = self.create_client(
            LinearMotionSi, '/lts300_x_axis/linear_motion')
        self.lts300_z_client = self.create_client(
            LinearMotionSi, '/lts300_z_axis/linear_motion')

        # Warte auf Services
        self.get_logger().info('Waiting for services...')
        self.activate_client.wait_for_service(timeout_sec=10.0)
        self.get_logger().info('✅ All services available!')

        # Starte Demo-Sequenz
        self.demo_thread = threading.Thread(target=self.run_demo_sequence)
        self.demo_thread.daemon = True
        self.demo_thread.start()

    def run_demo_sequence(self):
        """Vereinfachte Demo-Sequenz"""
        time.sleep(2.0)  # Kurz warten

        # 1. XBots aktivieren
        self.get_logger().info('🔧 Step 1: Activating XBots...')
        self.call_activate_xbots(True)
        time.sleep(1.0)

        # 2. Levitation aktivieren
        self.get_logger().info('🎈 Step 2: Enabling levitation...')
        self.call_levitation(0, True)
        time.sleep(1.0)

        # 3. Startposition: 120,120
        self.get_logger().info('📍 Step 3: Moving to start position (120,120)...')
        self.call_linear_motion(0, 120.0, 120.0)  # Explizit float!
        time.sleep(3.0)

        # 4. Ecken-Sequenz
        self.get_logger().info('📍 Step 4: Starting corner sequence...')
        corners = [
            (55.0, 55.0, "Corner 1"),      # Alle als float
            (180.0, 55.0, "Corner 2"),
            (180.0, 180.0, "Corner 3"),
            (55.0, 180.0, "Corner 4"),
            (75.0, 180.0, "Final position")
        ]

        for x, y, name in corners:
            self.get_logger().info(f'📍 Moving to {name} ({x},{y})...')
            self.call_linear_motion(0, x, y)
            time.sleep(3.0)

        # 5. X-Achse vorfahren (falls LTS300 verfügbar)
        self.get_logger().info('➡️ Step 5: X-Axis forward...')
        self.call_lts300_x_motion(100.0)  # Als float
        time.sleep(3.0)

        # 6. X-Achse zurück
        self.get_logger().info('⬅️ Step 6: X-Axis back...')
        self.call_lts300_x_motion(0.0)  # Als float
        time.sleep(3.0)

        # 7. Z-Achse herunterfahren auf 300mm
        self.get_logger().info('⬇️ Step 7: Z-Axis down to 300mm...')
        self.call_lts300_z_motion(300.0)  # Als float
        time.sleep(5.0)

        self.get_logger().info('🎯 Demo sequence completed!')

    def call_activate_xbots(self, activate):
        """XBots aktivieren/deaktivieren"""
        request = ActivateXbots.Request()
        request.activation_status = activate

        future = self.activate_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)

        if future.result():
            status = "activated" if activate else "deactivated"
            self.get_logger().info(f'✅ XBots {status} successfully!')
        else:
            self.get_logger().error('❌ Failed to change XBot activation status')

    def call_levitation(self, xbot_id, enable):
        """Levitation ein/ausschalten"""
        request = LevitationXbots.Request()
        request.xbot_id = xbot_id
        request.levitation = enable

        future = self.levitation_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)

        if future.result():
            status = "enabled" if enable else "disabled"
            self.get_logger().info(f'✅ Levitation {status} for XBot {xbot_id}')
        else:
            self.get_logger().error(
                f'❌ Failed to set levitation for XBot {xbot_id}')

    def call_linear_motion(self, xbot_id, x_pos, y_pos):
        """2D Lineare Bewegung"""
        request = LinearMotionSi.Request()
        request.xbot_id = xbot_id
        request.x_pos = float(x_pos)  # Explizit zu float konvertieren
        request.y_pos = float(y_pos)  # Explizit zu float konvertieren

        future = self.linear_motion_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=10.0)

        if future.result():
            self.get_logger().info(
                f'✅ Movement to ({x_pos},{y_pos})mm initiated')
        else:
            self.get_logger().error(f'❌ Failed to move to ({x_pos},{y_pos})mm')

    def call_lts300_x_motion(self, position):
        """LTS300 X-Achse bewegen"""
        try:
            request = LinearMotionSi.Request()
            request.xbot_id = 0  # Nicht verwendet für LTS300
            request.x_pos = float(position)  # Explizit zu float
            request.y_pos = 0.0  # Als float

            future = self.lts300_x_client.call_async(request)
            rclpy.spin_until_future_complete(self, future, timeout_sec=10.0)

            if future.result():
                self.get_logger().info(f'✅ X-Axis moved to {position}mm')
            else:
                self.get_logger().error(
                    f'❌ Failed to move X-Axis to {position}mm')
        except Exception as e:
            self.get_logger().warn(f'⚠️ X-Axis service not available: {e}')

    def call_lts300_z_motion(self, position):
        """LTS300 Z-Achse bewegen"""
        try:
            request = LinearMotionSi.Request()
            request.xbot_id = 0  # Nicht verwendet für LTS300
            request.x_pos = float(position)  # Explizit zu float
            request.y_pos = 0.0  # Als float

            future = self.lts300_z_client.call_async(request)
            rclpy.spin_until_future_complete(self, future, timeout_sec=15.0)

            if future.result():
                self.get_logger().info(f'✅ Z-Axis moved to {position}mm')
            else:
                self.get_logger().error(
                    f'❌ Failed to move Z-Axis to {position}mm')
        except Exception as e:
            self.get_logger().warn(f'⚠️ Z-Axis service not available: {e}')


def main(args=None):
    rclpy.init(args=args)
    demo_controller = DemoController()

    try:
        rclpy.spin(demo_controller)
    except KeyboardInterrupt:
        demo_controller.get_logger().info('🛑 Demo Controller stopped by user')
    finally:
        demo_controller.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
