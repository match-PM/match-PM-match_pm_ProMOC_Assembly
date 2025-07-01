# Linear Axis Nodes API

This module provides control for Thorlabs LTS300 linear positioning stages.

```{eval-rst}
.. automodule:: linear_axis_nodes
   :members:
   :undoc-members:
   :show-inheritance:
```

## Core Components

### Service Node

```{eval-rst}
.. automodule:: linear_axis_nodes.lts300_service_node
   :members:
   :undoc-members:
   :show-inheritance:
```

### Drivers

#### Base Driver

```{eval-rst}
.. automodule:: linear_axis_nodes.drivers.linear_axis_driver
   :members:
   :undoc-members:
   :show-inheritance:
```

#### Thorlabs LTS300 Driver

```{eval-rst}
.. automodule:: linear_axis_nodes.drivers.thorlabs_lts300_driver
   :members:
   :undoc-members:
   :show-inheritance:
```

#### Simulation Driver

```{eval-rst}
.. automodule:: linear_axis_nodes.drivers.simulated_linear_axis_driver
   :members:
   :undoc-members:
   :show-inheritance:
```

#### Gazebo Driver

```{eval-rst}
.. automodule:: linear_axis_nodes.drivers.gazebo_linear_axis_driver
   :members:
   :undoc-members:
   :show-inheritance:
```

## ROS2 Interfaces

### Services

The linear axis nodes provide the following ROS2 services:

#### Move Absolute
- **Service Type**: `promoc_assembly_interfaces/srv/linear_axis/MoveAbsolute`
- **Description**: Move to an absolute position
- **Parameters**:
  - `target_position` (float64): Target position in meters
  - `velocity` (float64): Movement velocity in m/s
- **Response**:
  - `success` (bool): Operation success
  - `message` (string): Status message

#### Move Relative  
- **Service Type**: `promoc_assembly_interfaces/srv/linear_axis/MoveRelative`
- **Description**: Move relative to current position
- **Parameters**:
  - `distance` (float64): Distance to move in meters
  - `velocity` (float64): Movement velocity in m/s

#### Get Position
- **Service Type**: `promoc_assembly_interfaces/srv/linear_axis/GetPosition`
- **Description**: Get current position and status
- **Response**:
  - `position` (float64): Current position in meters
  - `status` (string): Movement status (IDLE, MOVING, ERROR)

#### Home
- **Service Type**: `promoc_assembly_interfaces/srv/linear_axis/Home`
- **Description**: Home the axis to reference position

#### Shutdown
- **Service Type**: `promoc_assembly_interfaces/srv/linear_axis/Shutdown`
- **Description**: Safely shutdown the axis

### Topics

#### Status Information
- **Topic**: `linear_axis_info`
- **Message Type**: `promoc_assembly_interfaces/msg/linear_axis/LinearAxisInfo`
- **Description**: Continuous status updates

## Usage Examples

### Python Client Example

```python
import rclpy
from rclpy.node import Node
from promoc_assembly_interfaces.srv.linear_axis import MoveAbsolute

class LinearAxisClient(Node):
    def __init__(self):
        super().__init__('linear_axis_client')
        self.client = self.create_client(MoveAbsolute, 'x_axis/move_absolute')
        
    def move_to_position(self, position):
        request = MoveAbsolute.Request()
        request.target_position = position
        request.velocity = 0.01  # 10 mm/s
        
        future = self.client.call_async(request)
        return future
```

### Command Line Usage

```bash
# Move X-axis to 100mm position
ros2 service call /promoc_assembly/x_axis/move_absolute \
  promoc_assembly_interfaces/srv/linear_axis/MoveAbsolute \
  "{target_position: 0.1, velocity: 0.01}"

# Get current position
ros2 service call /promoc_assembly/x_axis/get_position \
  promoc_assembly_interfaces/srv/linear_axis/GetPosition

# Home the axis
ros2 service call /promoc_assembly/x_axis/home \
  promoc_assembly_interfaces/srv/linear_axis/Home
```

## Configuration

### Node Parameters

- `use_sim_time` (bool): Use simulation time
- `use_gazebo` (bool): Enable Gazebo integration
- `debug_mode` (bool): Enable debug output
- `x_axis_serial` (string): X-axis serial number
- `z_axis_serial` (string): Z-axis serial number
- `serial_port` (string): Serial port for communication
- `collision_threshold` (float): Collision detection threshold

### Hardware Configuration

For real hardware, configure in your launch file:

```python
parameters=[{
    'use_sim_time': False,
    'use_gazebo': False,
    'debug_mode': True,
    'x_axis_serial': '12345678',  # Your LTS300 serial
    'z_axis_serial': '87654321',
    'collision_threshold': 300.0,
}]
```

## Safety Features

- **Collision Detection**: Monitors force feedback
- **Soft Limits**: Configurable position limits  
- **Emergency Stop**: Immediate motion halt
- **Homing Required**: Ensures reference position
- **Status Monitoring**: Continuous health checks
