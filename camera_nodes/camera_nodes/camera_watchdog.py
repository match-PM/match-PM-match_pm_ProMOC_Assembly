#!/usr/bin/env python3
"""
Camera Connection Watchdog Node.

Monitors the camera connection and attempts automatic recovery if the connection is lost.
This node runs alongside the camera system to ensure continuous operation.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import time
import subprocess
import threading


class CameraWatchdog(Node):
    """
    Watchdog node that monitors camera connection and performs automatic recovery.
    
    Features:
    - Monitors image topic for data flow
    - Detects connection loss (timeout)
    - Attempts automatic USB reset on failure
    - Logs all events for debugging
    """

    def __init__(self):
        super().__init__('camera_watchdog')
        
        # Parameters
        self.declare_parameter('image_topic', '/promoc/assembly_camera/stream0/image_raw')
        self.declare_parameter('timeout_seconds', 10.0)
        self.declare_parameter('enable_auto_reset', True)
        self.declare_parameter('reset_cooldown_seconds', 30.0)
        
        self.image_topic = self.get_parameter('image_topic').value
        self.timeout_seconds = self.get_parameter('timeout_seconds').value
        self.enable_auto_reset = self.get_parameter('enable_auto_reset').value
        self.reset_cooldown_seconds = self.get_parameter('reset_cooldown_seconds').value
        
        # State
        self.last_image_time = None
        self.image_count = 0
        self.last_reset_time = 0
        self.connection_lost = False
        self.reset_in_progress = False
        self.lock = threading.Lock()
        
        # Subscriber
        self.image_sub = self.create_subscription(
            Image,
            self.image_topic,
            self.image_callback,
            10
        )
        
        # Watchdog timer (check every 2 seconds)
        self.watchdog_timer = self.create_timer(2.0, self.watchdog_check)
        
        self.get_logger().info('🐕 Camera Watchdog started')
        self.get_logger().info(f'   Monitoring: {self.image_topic}')
        self.get_logger().info(f'   Timeout: {self.timeout_seconds}s')
        self.get_logger().info(f'   Auto-reset: {"Enabled" if self.enable_auto_reset else "Disabled"}')

    def image_callback(self, msg: Image):
        """Update last seen time on image receipt."""
        current_time = time.time()
        
        with self.lock:
            self.last_image_time = current_time
            self.image_count += 1
            
            # Connection restored after loss
            if self.connection_lost:
                self.get_logger().info(
                    f'✅ Camera connection restored! Images flowing again.'
                )
                self.connection_lost = False

    def watchdog_check(self):
        """Periodic check for connection health."""
        current_time = time.time()
        
        with self.lock:
            # No images received yet
            if self.last_image_time is None:
                # Don't alert immediately on startup
                if current_time > 10.0:  # Give 10s grace period on startup
                    self.get_logger().warn(
                        '⏳ Waiting for first camera image...'
                    )
                return
            
            time_since_last = current_time - self.last_image_time
            
            # Connection healthy
            if time_since_last < self.timeout_seconds:
                return
            
            # Connection lost
            if not self.connection_lost:
                self.get_logger().error(
                    f'❌ CAMERA CONNECTION LOST! No images for {time_since_last:.1f}s'
                )
                self.connection_lost = True
                
                # Attempt automatic recovery
                if self.enable_auto_reset:
                    self.attempt_auto_recovery()
            else:
                # Still lost, log periodically
                self.get_logger().error(
                    f'❌ Camera still disconnected ({time_since_last:.1f}s)'
                )

    def attempt_auto_recovery(self):
        """Attempt to recover camera connection via USB reset."""
        current_time = time.time()
        
        # Check cooldown
        if current_time - self.last_reset_time < self.reset_cooldown_seconds:
            remaining = self.reset_cooldown_seconds - (current_time - self.last_reset_time)
            self.get_logger().warn(
                f'⏰ Reset cooldown active, waiting {remaining:.0f}s before retry'
            )
            return
        
        if self.reset_in_progress:
            self.get_logger().warn('🔄 Reset already in progress, skipping')
            return
        
        # Start reset in background thread
        self.reset_in_progress = True
        reset_thread = threading.Thread(target=self._perform_usb_reset)
        reset_thread.daemon = True
        reset_thread.start()

    def _perform_usb_reset(self):
        """Perform USB reset in background thread."""
        IDS_VENDOR_PRODUCT = "1409:8000"
        
        self.get_logger().info('🔄 Attempting automatic camera recovery...')
        self.get_logger().info('   Executing: sudo usbreset 1409:8000')
        
        try:
            result = subprocess.run(
                ['sudo', '-n', 'usbreset', IDS_VENDOR_PRODUCT],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.get_logger().info('✅ USB reset successful')
                self.get_logger().info('⏳ Waiting for camera to reinitialize...')
                time.sleep(5)
                self.last_reset_time = time.time()
            else:
                self.get_logger().error(
                    f'❌ USB reset failed: {result.stderr}'
                )
                self.get_logger().error(
                    '   Manual intervention required: sudo usbreset 1409:8000'
                )
                
        except subprocess.TimeoutExpired:
            self.get_logger().error('❌ USB reset timeout')
        except FileNotFoundError:
            self.get_logger().error(
                '❌ usbreset command not found! Install: sudo apt-get install usbutils'
            )
        except Exception as e:
            self.get_logger().error(f'❌ USB reset error: {e}')
        finally:
            self.reset_in_progress = False


def main(args=None):
    """Main entry point."""
    rclpy.init(args=args)
    
    watchdog = CameraWatchdog()
    
    try:
        rclpy.spin(watchdog)
    except KeyboardInterrupt:
        pass
    finally:
        watchdog.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
