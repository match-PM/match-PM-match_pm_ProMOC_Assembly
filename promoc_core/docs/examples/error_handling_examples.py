"""
Example: Using the ProMOC Error Handling System

This file demonstrates how to use the custom exception hierarchy and
error handling utilities in the ProMOC Assembly system.

Author: ProMOC Assembly Team
Date: 29. Oktober 2025
"""
# ruff: noqa: E402, F401

# Example 1: Basic Exception Usage
# ============================================================================

from promoc_core.promoc_exceptions import (
    PositionOutOfBoundsError,
    HomingRequiredError,
    DeviceNotFoundError,
    MovementTimeoutError
)


class ExampleLinearAxisDriver:
    """Example driver showing exception usage."""
    
    def __init__(self, logger):
        self.logger = logger
        self.is_homed = False
        self.min_position = 0.0
        self.max_position = 300.0
        self.current_position = 0.0
    
    def validate_position(self, position: float):
        """Validate position and raise specific exceptions."""
        
        # Check if homing is required
        if not self.is_homed:
            raise HomingRequiredError(
                "Device must be homed before movement",
                details={
                    'current_state': 'unhomed',
                    'requested_position': position
                }
            )
        
        # Check position bounds
        if position < self.min_position or position > self.max_position:
            raise PositionOutOfBoundsError(
                f"Position {position}mm is outside valid range "
                f"[{self.min_position}, {self.max_position}]mm",
                details={
                    'requested': position,
                    'min': self.min_position,
                    'max': self.max_position,
                    'current': self.current_position
                }
            )
    
    def move_absolute(self, position: float, timeout: float = 30.0):
        """Move to absolute position with error handling."""
        
        # Validation raises specific exceptions
        self.validate_position(position)
        
        # Simulate movement
        self.logger.info(f"Moving to {position}mm...")
        
        # Simulate timeout scenario
        import time
        start_time = time.time()
        
        # In real implementation, this would be actual movement
        # For demo, we check timeout
        if time.time() - start_time > timeout:
            raise MovementTimeoutError(
                f"Movement to {position}mm timed out after {timeout}s",
                details={
                    'target_position': position,
                    'current_position': self.current_position,
                    'timeout': timeout,
                    'elapsed': time.time() - start_time
                }
            )
        
        self.current_position = position
        self.logger.info(f"Movement completed to {position}mm")


# Example 2: Service Callback with Error Handling Decorator
# ============================================================================

from rclpy.node import Node
from promoc_core.error_handling import (
    handle_service_errors,
    ServiceResponse
)
# Assuming you have a service definition like:
# from promoc_assembly_interfaces.srv import MoveAbsolute


class ExampleNode(Node):
    """Example node showing service error handling."""
    
    def __init__(self):
        super().__init__('example_node')
        self.driver = ExampleLinearAxisDriver(self.get_logger())
        
        # Create service
        # self.srv = self.create_service(
        #     MoveAbsolute,
        #     'move_absolute',
        #     self.move_absolute_callback
        # )
    
    @handle_service_errors()  # Automatically handles all exceptions
    def move_absolute_callback(self, request, response):
        """
        Service callback with automatic error handling.
        
        The decorator will:
        - Catch all exceptions
        - Populate response with error info
        - Log errors appropriately
        - Add execution time
        """
        
        # Business logic - just write the happy path!
        # Exceptions will be caught and handled by the decorator
        self.driver.move_absolute(
            position=request.position,
            timeout=request.timeout
        )
        
        response.success = True
        response.status_message = f"Moved to {request.position}mm successfully"
        return response


# Example 3: Retry Mechanism
# ============================================================================

from promoc_core.error_handling import retry_on_error, RetryConfig
from promoc_core.promoc_exceptions import (
    DeviceDisconnectedError,
    CommunicationTimeoutError
)


class ExampleDriverWithRetry:
    """Example driver with automatic retry on connection errors."""
    
    def __init__(self, logger):
        self.logger = logger
        self.connected = False
    
    @retry_on_error(RetryConfig(
        max_attempts=5,
        delay=1.0,
        backoff_factor=2.0,
        max_delay=30.0,
        retriable_exceptions=(DeviceDisconnectedError, CommunicationTimeoutError)
    ))
    def connect(self, port: str) -> bool:
        """
        Connect with automatic retry.
        
        This method will automatically retry up to 5 times with
        exponential backoff if connection fails.
        """
        
        self.logger.info(f"Attempting to connect to port {port}...")
        
        # Simulate connection attempt
        import random
        if random.random() < 0.3:  # 30% chance of success for demo
            self.connected = True
            self.logger.info("Connection successful!")
            return True
        else:
            # This will trigger a retry
            raise CommunicationTimeoutError(
                f"Failed to connect to port {port}",
                details={'port': port, 'attempt': 'simulated'}
            )


# Example 4: Error Recovery Strategies
# ============================================================================

from promoc_core.error_handling import (
    ErrorRecoveryManager,
    HomingRecoveryStrategy,
    ReconnectionRecoveryStrategy,
    ErrorRecoveryStrategy
)
from promoc_core.promoc_exceptions import ProMocError


class CustomRecoveryStrategy(ErrorRecoveryStrategy):
    """Custom recovery strategy for specific error types."""
    
    def can_recover(self, error: Exception) -> bool:
        """Check if we can recover from this error."""
        return isinstance(error, PositionOutOfBoundsError)
    
    def recover(self, error: Exception, context: dict) -> bool:
        """Attempt to recover by moving to safe position."""
        try:
            driver = context.get('driver')
            if driver:
                if self.logger:
                    self.logger.info("Recovering by moving to safe position (0mm)")
                
                # Move to safe position
                driver.current_position = 0.0
                driver.is_homed = True
                
                if self.logger:
                    self.logger.info("Recovery successful")
                return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Recovery failed: {e}")
        
        return False


class NodeWithRecovery(Node):
    """Example node with error recovery."""
    
    def __init__(self):
        super().__init__('node_with_recovery')
        self.driver = ExampleLinearAxisDriver(self.get_logger())
        
        # Setup recovery manager
        self.recovery_manager = ErrorRecoveryManager(self.get_logger())
        self.recovery_manager.add_strategy(HomingRecoveryStrategy(self.get_logger()))
        self.recovery_manager.add_strategy(CustomRecoveryStrategy(self.get_logger()))
    
    def perform_operation_with_recovery(self, position: float):
        """Perform operation with automatic recovery on error."""
        
        try:
            self.driver.move_absolute(position)
            
        except ProMocError as e:
            self.get_logger().warning(f"Operation failed: {e}")
            
            # Attempt recovery
            context = {
                'driver': self.driver,
                'requested_position': position
            }
            
            if self.recovery_manager.attempt_recovery(e, context):
                self.get_logger().info("Recovery successful, retrying operation...")
                # Retry the operation
                try:
                    self.driver.move_absolute(position)
                    self.get_logger().info("Operation succeeded after recovery")
                except Exception as retry_error:
                    self.get_logger().error(f"Operation failed even after recovery: {retry_error}")
                    raise
            else:
                self.get_logger().error("Could not recover from error")
                raise


# Example 5: Manual Service Response Creation
# ============================================================================

import time


class ManualResponseExample:
    """Example showing manual service response creation."""
    
    def __init__(self, logger):
        self.logger = logger
        self.driver = ExampleLinearAxisDriver(logger)
    
    def service_callback_manual(self, request, response):
        """Service callback with manual error handling."""
        
        start_time = time.time()
        
        try:
            # Perform operation
            self.driver.move_absolute(request.position)
            
            # Create success response
            service_response = ServiceResponse.success_response(
                message=f"Movement to {request.position}mm completed successfully",
                execution_time=time.time() - start_time,
                warnings=[],
                final_position=self.driver.current_position,
                distance_traveled=abs(request.position - self.driver.current_position)
            )
            
        except ProMocError as e:
            # Create error response from ProMOC exception
            service_response = ServiceResponse.error_response(
                error=e,
                execution_time=time.time() - start_time,
                attempted_position=request.position,
                current_position=self.driver.current_position
            )
            
            self.logger.error(f"Service call failed: {e}")
        
        # Populate ROS response object
        return service_response.to_ros_response(response)


# Example 6: Exception Catching Best Practices
# ============================================================================

class BestPracticesExample:
    """Example showing best practices for exception handling."""
    
    def __init__(self, logger):
        self.logger = logger
        self.driver = ExampleLinearAxisDriver(logger)
    
    def specific_exception_handling(self, position: float):
        """Use specific exception types for precise handling."""
        
        try:
            self.driver.move_absolute(position)
            
        except HomingRequiredError as e:
            # Specific handling for homing required
            self.logger.warning(f"Homing required: {e}")
            self.logger.info("Performing homing...")
            self.driver.is_homed = True  # In real code, call driver.home()
            # Retry after homing
            self.driver.move_absolute(position)
            
        except PositionOutOfBoundsError as e:
            # Specific handling for position errors
            self.logger.error(f"Position validation failed: {e}")
            self.logger.debug(f"Error details: {e.details}")
            # Maybe clamp to valid range?
            safe_position = max(self.driver.min_position, 
                               min(position, self.driver.max_position))
            self.logger.info(f"Clamping to safe position: {safe_position}mm")
            self.driver.move_absolute(safe_position)
            
        except MovementTimeoutError as e:
            # Specific handling for timeouts
            self.logger.error(f"Movement timed out: {e}")
            # Maybe stop the movement?
            raise  # Re-raise if we can't handle it
            
        except ProMocError as e:
            # Catch-all for other ProMOC errors
            self.logger.error(f"ProMOC error occurred: {e}")
            self.logger.error(f"Error code: {e.error_code}")
            raise
    
    def error_code_based_handling(self, position: float):
        """Handle errors based on error codes."""
        
        try:
            self.driver.move_absolute(position)
            
        except ProMocError as e:
            # Handle based on error code ranges
            if 1200 <= e.error_code < 1300:  # Motion errors
                self.logger.error(f"Motion error {e.error_code}: {e}")
                # Handle motion errors
                
            elif 1300 <= e.error_code < 1400:  # Safety violations
                self.logger.critical(f"SAFETY VIOLATION {e.error_code}: {e}")
                # Emergency handling
                
            elif 1400 <= e.error_code < 1500:  # Calibration errors
                self.logger.warning(f"Calibration error {e.error_code}: {e}")
                # Maybe perform calibration
                
            else:
                self.logger.error(f"Error {e.error_code}: {e}")
                raise


# Example 7: Testing with Custom Exceptions
# ============================================================================

def example_test():
    """Example showing how to test code with custom exceptions."""
    
    import pytest
    import logging
    
    logger = logging.getLogger(__name__)
    driver = ExampleLinearAxisDriver(logger)
    
    # Test 1: Position out of bounds
    with pytest.raises(PositionOutOfBoundsError) as exc_info:
        driver.move_absolute(500.0)  # Exceeds max_position
    
    # Check exception details
    assert exc_info.value.error_code == 1202
    assert exc_info.value.details['requested'] == 500.0
    assert exc_info.value.details['max'] == 300.0
    
    # Test 2: Homing required
    driver.is_homed = False
    with pytest.raises(HomingRequiredError) as exc_info:
        driver.move_absolute(100.0)
    
    assert exc_info.value.error_code == 1401
    
    # Test 3: Successful operation
    driver.is_homed = True
    driver.move_absolute(150.0)  # Should succeed
    assert driver.current_position == 150.0


if __name__ == '__main__':
    """
    Run examples (requires ROS2 environment).
    
    Note: Some examples are simplified and won't run without
    proper ROS2 setup and service definitions.
    """
    
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    print("=" * 70)
    print("Example 1: Basic Exception Usage")
    print("=" * 70)
    
    driver = ExampleLinearAxisDriver(logger)
    driver.is_homed = True
    
    try:
        driver.move_absolute(500.0)  # Will fail - out of bounds
    except PositionOutOfBoundsError as e:
        print(f"Caught exception: {e}")
        print(f"Error code: {e.error_code}")
        print(f"Details: {e.details}")
    
    print("\n" + "=" * 70)
    print("Example 2: Retry Mechanism")
    print("=" * 70)
    
    retry_driver = ExampleDriverWithRetry(logger)
    try:
        # This will retry multiple times if it fails
        retry_driver.connect("/dev/ttyUSB0")
    except Exception as e:
        print(f"Connection failed after all retries: {e}")
    
    print("\n" + "=" * 70)
    print("Example 3: Error Recovery")
    print("=" * 70)
    
    # Recovery example would require ROS2 node setup
    print("See NodeWithRecovery class for implementation example")
    
    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)
