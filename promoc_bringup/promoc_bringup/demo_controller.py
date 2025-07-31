#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import time
import threading

# Import service interfaces
from promoc_assembly_interfaces.srv import (
    ActivateXbots,
    LevitationXbots,
    LinearMotionSi,
    SixDofMotion,
    RotaryMotion,
    Home,
    MoveAbsolute
)
from promoc_assembly_interfaces.msg import LinearAxisInfo


class DemoController(Node):
    def __init__(self):
        super().__init__('demo_controller')
        self.get_logger().info('🚀 Demo Controller started!')

        self.declare_parameter('xbot_id', 1)
        self.xbot_id = self.get_parameter(
            'xbot_id').get_parameter_value().integer_value
        self.get_logger().info(f'🤖 Using XBot ID: {self.xbot_id}')

        self.cycle_delay = 5.0  # Delay between demo cycles in seconds

        # Status tracking für LTS300 Achsen
        self.x_axis_homed = False
        self.z_axis_homed = False
        self.x_axis_position = None
        self.z_axis_position = None

        # Create Service Clients
        self.create_service_clients()
        self.get_logger().info('✅ Service clients created!')

        self.create_positon_subscribers()
        self.get_logger().info('✅ Subscribers created!')

        # Warte auf Services UND PMC Connection
        self.get_logger().info('⏳ Waiting for services and PMC connection...')
        if not self.wait_for_services():
            self.get_logger().error('❌ Failed to connect to services/PMC')
            return

        self.get_logger().info('✅ All services available and PMC connected!')

        # Starte Demo-Sequenz
        self.demo_thread = threading.Thread(target=self.run_endless_demo)
        self.demo_thread.daemon = True
        self.demo_thread.start()

    def create_service_clients(self):
        """Erstelle alle benötigten Service Clients"""
        self.activate_client = self.create_client(
            ActivateXbots, '/mover_node/activate_xbots')
        self.levitation_client = self.create_client(
            LevitationXbots, '/mover_node/levitation_xbots')
        self.linear_motion_client = self.create_client(
            LinearMotionSi, '/mover_node/linear_mover_motion')
        self.six_dof_motion_client = self.create_client(
            SixDofMotion, '/mover_node/six_d_mover_motion')
        self.rotary_motion_client = self.create_client(
            RotaryMotion, '/mover_node/rotary_motion')

        # # LTS300 Clients
        # self.lts300_x_client = self.create_client(
        #     MoveAbsolute, '/lts300_x_axis/move_absolute')
        # self.lts300_z_client = self.create_client(
        #     MoveAbsolute, '/lts300_z_axis/move_absolute')

        # # Home services für LTS300
        # self.lts300_x_home_client = self.create_client(
        #     Home, '/lts300_x_axis/home')
        # self.lts300_z_home_client = self.create_client(
        #     Home, '/lts300_z_axis/home')

    def create_positon_subscribers(self):
        """Create subscribers for LTS300 axis positions"""
        # self.x_axis_subscription = self.create_subscription(
        #     LinearAxisInfo,
        #     '/promoc_assembly/lts300_x_axis/position',
        #     self.x_axis_position_callback,
        #     10)

        # self.z_axis_subscription = self.create_subscription(
        #     LinearAxisInfo,
        #     '/promoc_assembly/lts300_z_axis/position',
        #     self.z_axis_position_callback,
        #     10)

    def wait_for_services(self):
        """Wait for all required services to be available"""
        # Mover Services
        try:
            self.activate_client.wait_for_service(timeout_sec=10.0)
            self.levitation_client.wait_for_service(timeout_sec=10.0)
            self.linear_motion_client.wait_for_service(timeout_sec=10.0)
        except:
            self.get_logger().error('❌ Some services not available, exiting...')
            rclpy.shutdown()

        # LTS300 Services (optional)
        # try:
        #     self.lts300_x_client.wait_for_service(timeout_sec=5.0)
        #     self.lts300_z_client.wait_for_service(timeout_sec=5.0)
        #     self.lts300_x_home_client.wait_for_service(timeout_sec=5.0)
        #     self.lts300_z_home_client.wait_for_service(timeout_sec=5.0)
        # except:
        #     self.get_logger().warn('⚠️ Some LTS300 services not available')

    def x_axis_position_callback(self, msg):
        """Callback für X-Achse Position"""
        # self.x_axis_position = msg.axis_position
        # # Prüfe ob gehomed (Position nahe 0)
        # if not self.x_axis_homed and abs(msg.axis_position) < 1.0:
        #     self.x_axis_homed = True
        #     self.get_logger().info('✅ X-Axis is homed')
        pass

    def z_axis_position_callback(self, msg):
        """Callback für Z-Achse Position"""
        # self.z_axis_position = msg.axis_position
        # # Prüfe ob gehomed (Position nahe 0)
        # if not self.z_axis_homed and abs(msg.axis_position) < 1.0:
        #     self.z_axis_homed = True
        #     self.get_logger().info('✅ Z-Axis is homed')
        pass

    def wait_for_homing(self):
        """Warte bis beide LTS300 Achsen gehomed sind - nur wenn nötig"""
        # self.get_logger().info('🏠 Checking which axes need homing...')

        # # Sende nur Home-Kommandos an nicht-gehomte Achsen
        # if not self.x_axis_homed:
        #     self.get_logger().info('🏠 X-Axis needs homing...')
        #     self.call_lts300_home('x')
        # else:
        #     self.get_logger().info('✅ X-Axis already homed')

        # if not self.z_axis_homed:
        #     self.get_logger().info('🏠 Z-Axis needs homing...')
        #     self.call_lts300_home('z')
        # else:
        #     self.get_logger().info('✅ Z-Axis already homed')

        # # Warte bis beide gehomed sind (falls noch nötig)
        # timeout = 120.0
        # start_time = time.time()

        # while not (self.x_axis_homed and self.z_axis_homed):
        #     if time.time() - start_time > timeout:
        #         self.get_logger().error('❌ Homing timeout reached!')
        #         return False

        #     self.get_logger().info(
        #         f'🏠 Waiting for homing - X: {self.x_axis_homed}, Z: {self.z_axis_homed}')
        #     time.sleep(2.0)

        # self.get_logger().info('✅ Both LTS300 axes are homed and ready!')
        # return True
        pass

    def call_lts300_home(self, axis):
        """Home eine LTS300 Achse"""
        # try:
        #     if axis == 'x':
        #         client = self.lts300_x_home_client
        #     else:
        #         client = self.lts300_z_home_client

        #     request = Home.Request()
        #     future = client.call_async(request)
        #     rclpy.spin_until_future_complete(self, future, timeout_sec=10.0)

        #     if future.result() and future.result().success:
        #         self.get_logger().info(
        #             f'✅ {axis.upper()}-Axis homing initiated')
        #     else:
        #         self.get_logger().error(
        #             f'❌ Failed to home {axis.upper()}-Axis')
        # except Exception as e:
        #     self.get_logger().error(f'❌ Error homing {axis.upper()}-Axis: {e}')
        pass

    def run_endless_demo(self):
        """Endlose Demo-Sequenz"""
        time.sleep(2.0)  # Kurz warten

        # # Einfache Logik: Prüfe Status und handle entsprechend
        # if self.x_axis_homed and self.z_axis_homed:
        #     self.get_logger().info('✅ Both axes are homed, starting demo...')
        # else:
        #     self.get_logger().warn('⚠️ Some axes are not homed!')
        #     self.get_logger().info('🏠 Waiting for axes to be homed...')

        #     # Warte bis gehomed (ohne aktives Homing zu starten)
        #     if not self.wait_for_homing_status():
        #         self.get_logger().error('❌ Axes not homed, stopping demo')
        #         return

        #     else:
        #         self.get_logger().info('🏠 LTS300 homing disabled, skipping...')

        self.get_logger().info('🏠 LTS300 homing disabled, starting demo directly...')
        
        cycle_count = 0

        try:
            while rclpy.ok():
                cycle_count += 1
                self.get_logger().info(f'🔄 Starting demo cycle #{cycle_count}')

                self.run_single_demo_cycle()

                # Unterbrechbarer Sleep in 1s-Schritten
                for i in range(int(self.cycle_delay)):
                    if not rclpy.ok():
                        return
                    time.sleep(1.0)

        except KeyboardInterrupt:
            self.get_logger().info('🛑 Demo stopped by user (Ctrl+C)')
        except Exception as e:
            self.get_logger().error(f'❌ Demo error: {e}')

        self.get_logger().info('🏁 Demo finished')

    def run_single_demo_cycle(self):
        """Demo-Zyklus mit Millimeter-Eingaben"""
        try:
            # 1. XBots aktivieren
            self.get_logger().info('🔧 Step 1: Activating XBots...')
            self.call_activate_xbots(True)
            

            # 2. Levitation aktivieren
            self.get_logger().info(
                f'🎈 Step 2: Enabling levitation for XBot {self.xbot_id}...')
            #self.call_levitation(True)
            

            # 3. Startposition (in MILLIMETERN für Mover Node)
            self.get_logger().info(
                f'📍 Step 3: Moving XBot {self.xbot_id} to start position...')
            self.call_six_dof_motion(
                self.xbot_id, 240.0, 120.0, 3, 0, 0, 0)  # 2
            
            self.get_logger().info(
                f'📍 Step 3: Moving XBot {self.xbot_id} to start position...')
            self.call_six_dof_motion(
                self.xbot_id, 360.0, 120.0, 3, 0, 0, 0)  # 2
            

            self.get_logger().info(
                f'📍 Step 5: Starting systematic 6DOF demo for XBot {self.xbot_id}...')

            # Basis-Position

            
            self.call_six_dof_motion(self.xbot_id, 60, 120, 4, 25, 0, 100)
            self.call_six_dof_motion(self.xbot_id, 80, 140, 4, 25, 25, 0)
            self.call_six_dof_motion(self.xbot_id, 100, 160, 4, 0, 25, -100)
            self.call_six_dof_motion(self.xbot_id, 120, 140, 4, -25, 25, -50)
            self.call_six_dof_motion(self.xbot_id, 140, 120, 4, -25, 0, 0)
            self.call_six_dof_motion(self.xbot_id, 160, 100, 4, -25, -25, 50)
            self.call_six_dof_motion(self.xbot_id, 180, 80, 4, 0, -25, 100)
            self.call_six_dof_motion(self.xbot_id, 200, 60, 4, 25, -25, 0)
            self.call_six_dof_motion(self.xbot_id, 220, 80, 4, 25, 0, -100)
            self.call_six_dof_motion(self.xbot_id, 240, 100, 3, 20, 0, -0)
            self.call_six_dof_motion(self.xbot_id, 260, 120, 3, 20, 20, 50)
            self.call_six_dof_motion(self.xbot_id, 280, 140, 3, 0, 20, 100)
            self.call_six_dof_motion(self.xbot_id, 300, 160, 3, -20, 20, 0)
            self.call_six_dof_motion(self.xbot_id, 320, 140, 3, -20, -20, -50)
            self.call_six_dof_motion(self.xbot_id, 340, 120, 2, 0, -15, -100)
            self.call_six_dof_motion(self.xbot_id, 360, 100, 2, 15, 0, 100)
            self.call_six_dof_motion(self.xbot_id, 380, 80, 2, 0, 0, 0)
            self.call_six_dof_motion(self.xbot_id, 400, 60, 2, 10, 10, -100)
            self.call_six_dof_motion(self.xbot_id, 420, 80, 2, -10, -10, 100)
            self.call_six_dof_motion(self.xbot_id, 240, 120, 2, 25, 0, -100)




            self.get_logger().info('🔄 Phase 5: Returning to center position')
            self.call_six_dof_motion(self.xbot_id, 60, 60, 2, 0, 0, 0)
            self.call_six_dof_motion(self.xbot_id, 420, 180, 1, 0, 0, 0)
            self.call_six_dof_motion(self.xbot_id, 420, 60, 3, 0, 0, 0)
            self.call_six_dof_motion(self.xbot_id, 60, 180, 4, 0, 0, 0)

            self.call_six_dof_motion(self.xbot_id, 110, 180, 4, 25, 0, 100)
            self.call_six_dof_motion(self.xbot_id, 110, 180, 4, 0, 25, 0)
            self.call_six_dof_motion(self.xbot_id, 110, 180, 4, -25, 0, -100)


            # self.call_lts300_x_motion(250.0)
            # time.sleep(5.0)
            # self.call_lts300_x_motion(10.0)
            # time.sleep(5.0)

            # self.call_lts300_z_motion(300.0)
            # time.sleep(5.0)

            # self.call_lts300_z_motion(0.0)
            # time.sleep(5.0)

            self.get_logger().info('✅ Demo cycle completed successfully!')
            return True

        except KeyboardInterrupt:
            self.get_logger().info('🛑 Demo cycle interrupted by user')
            return False
        except Exception as e:
            self.get_logger().error(f'❌ Demo cycle failed: {str(e)}')
            return False

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

    def call_levitation(self, enable):
        """Levitation ein/ausschalten"""
        request = LevitationXbots.Request()
        request.levitation = enable

        future = self.levitation_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)

        if future.result():
            status = "enabled" if enable else "disabled"
            self.get_logger().info(f'✅ Levitation {status}')
        else:
            self.get_logger().error(f'❌ Failed to set levitation')

    def call_linear_motion(self, xbot_id, x_pos, y_pos):
        """2D Lineare Bewegung für spezifische XBot ID"""
        request = LinearMotionSi.Request()
        request.xbot_id = xbot_id
        request.x_pos = float(x_pos)
        request.y_pos = float(y_pos)

        future = self.linear_motion_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=10.0)

        if future.result():
            self.get_logger().info(
                f'✅ XBot {xbot_id} movement to ({x_pos},{y_pos})mm initiated')
        else:
            self.get_logger().error(
                f'❌ Failed to move XBot {xbot_id} to ({x_pos},{y_pos})mm')

    def call_six_dof_motion(self, xbot_id, x_pos, y_pos, z_pos, rx, ry, rz):
        """6DOF Bewegung für spezifische XBot ID"""
        try:
            request = SixDofMotion.Request()
            request.xbot_id = xbot_id
            request.x_pos = float(x_pos)
            request.y_pos = float(y_pos)
            request.z_pos = float(z_pos)
            request.rx_pos = float(rx)
            request.ry_pos = float(ry)
            request.rz_pos = float(rz)

            self.get_logger().info(
                f'📍 6DOF motion: ({x_pos},{y_pos},{z_pos})mm, ({rx},{ry},{rz})mrad')

            # KORRIGIERT: Verwende den richtigen Service Client
            future = self.six_dof_motion_client.call_async(request)
            rclpy.spin_until_future_complete(self, future, timeout_sec=10.0)

            if future.result() and future.result().success:
                self.get_logger().info(
                    f'✅ 6DOF motion for XBot {xbot_id} completed')
                return True
            else:
                error_msg = future.result().status_message if future.result() else "Service call failed"
                self.get_logger().error(f'❌ 6DOF motion failed: {error_msg}')
                return False

        except Exception as e:
            self.get_logger().error(f'❌ 6DOF motion call failed: {e}')
            return False

    def call_rotary_motion(self, xbot_id, angle, rotation_speed=1.0, rotation_acceleration=1.0):
        """Rotary Bewegung für spezifische XBot ID"""
        request = RotaryMotion.Request()
        request.xbot_id = xbot_id
        request.target_rz = float(angle)
        request.max_rz_speed = float(rotation_speed)
        request.max_accel_rz = float(rotation_acceleration)

        future = self.rotary_motion_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=10.0)

        if future.result():
            self.get_logger().info(
                f'✅ Rotary motion for XBot {xbot_id} to angle {angle}° initiated')
        else:
            self.get_logger().error(
                f'❌ Failed to perform rotary motion for XBot {xbot_id} to angle {angle}°')

    def stop_demo(self):
        """Demo stoppen für spezifische XBot ID"""
        self.get_logger().info(f'🛑 Stopping demo for XBot {self.xbot_id}...')
        # Levitation ausschalten
        self.call_levitation(False)
        # XBots deaktivieren
        self.call_activate_xbots(False)

    def emergency_stop(self):
        """Notaus für spezifische XBot ID"""
        self.get_logger().error(f'🚨 Emergency Stop for XBot {self.xbot_id}!')
        try:
            self.call_levitation(False)
            self.call_activate_xbots(False)
        except:
            pass

    def call_lts300_x_motion(self, position):
        """LTS300 X-Achse bewegen"""
        # try:
        #     request = MoveAbsolute.Request()
        #     request.axis_position = float(position)

        #     future = self.lts300_x_client.call_async(request)
        #     rclpy.spin_until_future_complete(self, future, timeout_sec=10.0)

        #     if future.result() and future.result().success:
        #         self.get_logger().info(f'✅ X-Axis moved to {position}mm')
        #     else:
        #         self.get_logger().error(
        #             f'❌ Failed to move X-Axis to {position}mm')
        # except Exception as e:
        #     self.get_logger().warn(f'⚠️ X-Axis service error: {e}')
        pass

    def call_lts300_z_motion(self, position):
        """LTS300 Z-Achse bewegen"""
        # try:
        #     request = MoveAbsolute.Request()
        #     request.axis_position = float(position)

        #     future = self.lts300_z_client.call_async(request)
        #     rclpy.spin_until_future_complete(self, future, timeout_sec=15.0)

        #     if future.result() and future.result().success:
        #         self.get_logger().info(f'✅ Z-Axis moved to {position}mm')
        #     else:
        #         self.get_logger().error(
        #             f'❌ Failed to move Z-Axis to {position}mm')
        # except Exception as e:
        #     self.get_logger().warn(f'⚠️ Z-Axis service error: {e}')
        pass

    def test_mover_connection(self):
        """Teste ob Mover wirklich mit PMC connected ist"""
        try:
            # Teste mit einem einfachen Service-Call
            request = ActivateXbots.Request()
            request.activation_status = True

            future = self.activate_client.call_async(request)
            rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)

            if future.result() and future.result().success:
                self.get_logger().info('✅ PMC connection test successful!')
                return True
            else:
                self.get_logger().warn('⚠️ PMC not ready yet, service call failed')
                return False

        except Exception as e:
            self.get_logger().warn(f'⚠️ PMC connection test failed: {e}')
            return False

    def wait_for_services(self):
        """Wait for all required services AND PMC connection"""
        services = [
            (self.activate_client, "activate_xbots"),
            (self.levitation_client, "levitation_xbots"),
            (self.linear_motion_client, "linear_motion"),
            (self.six_dof_motion_client, "six_dof_motion"),
            (self.rotary_motion_client, "rotary_motion"),
        ]

        for client, name in services:
            self.get_logger().info(f'⏳ Waiting for {name} service...')
            while not client.wait_for_service(timeout_sec=1.0):
                if not rclpy.ok():
                    return False
                self.get_logger().info(
                    f'⏳ Service {name} not available, waiting...')
            self.get_logger().info(f'✅ Service {name} is ready!')

        # PMC Connection Test
        self.get_logger().info('⏳ Testing PMC connection...')
        while not self.test_mover_connection():
            if not rclpy.ok():
                return False
            self.get_logger().info('⏳ PMC not ready, waiting 2 seconds...')
            time.sleep(2.0)

        self.get_logger().info('✅ PMC connection confirmed!')
        return True


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
