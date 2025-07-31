#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
import time
import threading
import math

# Import service interfaces
from promoc_assembly_interfaces.srv import (
    ActivateXbots,
    LevitationXbots,
    LinearMotionSi,
    SixDofMotion,
    RotaryMotion
)


class PMDemoController(Node):
    def __init__(self):
        super().__init__('pm_demo_controller')
        self.get_logger().info('🚀 PM Demo Controller started!')

        self.declare_parameter('xbot_id', 1)
        self.xbot_id = self.get_parameter(
            'xbot_id').get_parameter_value().integer_value
        self.get_logger().info(f'🤖 Using XBot ID: {self.xbot_id}')

        self.cycle_delay = 5.0  # Delay between demo cycles in seconds

        # Create Service Clients
        self.create_service_clients()
        self.get_logger().info('✅ Service clients created!')

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

    def run_endless_demo(self):
        """Endlose Demo-Sequenz für Planar Motor"""
        time.sleep(2.0)  # Kurz warten

        self.get_logger().info('🚀 Starting Planar Motor demo...')

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
        """Demo-Zyklus mit systematischen Eckfahrten und sinusförmigen Verkippungen"""
        try:
            # 1. XBots aktivieren
            self.get_logger().info('🔧 Step 1: Activating XBots...')
            self.call_activate_xbots(True)
            time.sleep(1.0)

            # 2. Levitation aktivieren
            self.get_logger().info(
                f'🎈 Step 2: Enabling levitation for XBot {self.xbot_id}...')
            self.call_levitation(True)
            time.sleep(1.0)

            # 3. Startposition (Zentrum)
            self.get_logger().info(
                f'📍 Step 3: Moving XBot {self.xbot_id} to center position...')
            self.call_six_dof_motion(self.xbot_id, 120.0, 120.0, 2.5, 0, 0, 0)
            time.sleep(2.0)

            # 4. Systematische Eckfahrt mit sinusförmigen Verkippungen
            self.get_logger().info(
                f'� Step 4: Corner pattern with sinusoidal tilting for XBot {self.xbot_id}...')
            
            # Definiere Eckpunkte (X, Y in mm)
            corners = [
                (60, 60),    # Unten links
                (180, 60),   # Unten rechts  
                (180, 180),  # Oben rechts
                (60, 180),   # Oben links
            ]
            
            # Parameter für sinusförmige Bewegung
            max_tilt_at_max_z = 25.0  # Maximale Neigung bei Z=4mm in mrad
            max_z = 4.0              # Maximale Z-Position in mm
            min_z = 1.0              # Minimale Z-Position in mm
            steps_per_corner = 12    # Anzahl Schritte pro Ecke
            
            for cycle in range(3):  # 3 komplette Durchläufe
                self.get_logger().info(f'🔄 Starting corner cycle #{cycle + 1}/3')
                
                for corner_idx, (x, y) in enumerate(corners):
                    self.get_logger().info(f'📍 Moving to corner {corner_idx + 1}: ({x}, {y})mm')
                    
                    # Fahre zu Ecke mit sinusförmigen Verkippungen
                    for step in range(steps_per_corner):
                        # Sinusförmige Verkippung berechnen
                        angle = (step / steps_per_corner) * 2 * math.pi
                        
                        # Z-Position variieren (1-4mm)
                        z = min_z + (max_z - min_z) * (0.5 + 0.5 * math.sin(angle * 2))
                        
                        # Neigung skaliert mit Z-Position (bei Z=4mm max 25mrad, bei Z=1mm entsprechend weniger)
                        tilt_factor = (z / max_z)  # Skalierungsfaktor basierend auf Z-Position
                        max_tilt_current = max_tilt_at_max_z * tilt_factor
                        
                        rx = max_tilt_current * math.sin(angle)
                        ry = max_tilt_current * math.cos(angle)
                        
                        self.get_logger().info(f'  Z={z:.1f}mm, max_tilt={max_tilt_current:.1f}mrad')
                        self.call_six_dof_motion(self.xbot_id, x, y, z, rx, ry, 0)
                        time.sleep(0.3)  # Kurze Pause zwischen Schritten
                
                # Zurück zum Zentrum mit neutraler Position
                self.get_logger().info('🏠 Returning to center...')
                self.call_six_dof_motion(self.xbot_id, 120, 120, 2.5, 0, 0, 0)
                time.sleep(1.0)

            # 5. Zusätzliche sinusförmige Bewegung im Zentrum
            self.get_logger().info('🌊 Step 5: Sinusoidal motion in center...')
            center_steps = 20
            for step in range(center_steps):
                angle = (step / center_steps) * 4 * math.pi  # 2 komplette Zyklen
                
                # Z-Position variieren (1-4mm)
                z = min_z + (max_z - min_z) * (0.5 + 0.5 * math.sin(angle * 0.7))
                
                # Neigung skaliert mit Z-Position
                tilt_factor = (z / max_z)
                max_tilt_current = max_tilt_at_max_z * tilt_factor
                
                # Sinusförmige Verkippungen
                rx = max_tilt_current * math.sin(angle)
                ry = max_tilt_current * math.cos(angle * 1.5)  # Verschiedene Frequenz für komplexere Bewegung
                rz = 10.0 * math.sin(angle * 2)   # Rotation um Z-Achse
                
                # Kleine XY-Variation
                x_offset = 10.0 * math.sin(angle * 0.5)
                y_offset = 10.0 * math.cos(angle * 0.5)
                
                self.call_six_dof_motion(
                    self.xbot_id, 
                    120 + x_offset, 
                    120 + y_offset, 
                    z, 
                    rx, ry, rz
                )
                time.sleep(0.4)

            # 6. Finale Position
            self.get_logger().info('🏁 Final position...')
            self.call_six_dof_motion(self.xbot_id, 120, 120, 2.5, 0, 0, 0)
            time.sleep(2.0)

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
    

    demo_controller = PMDemoController()
    
    try:
        rclpy.spin(demo_controller)
    except KeyboardInterrupt:
        demo_controller.get_logger().info('🛑 Demo Controller stopped by user')
    finally:
        demo_controller.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()