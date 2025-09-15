# ProMOC Assembly Interfaces

A ROS2 interface package defining custom messages and services for the ProMOC (Planar Motor Control) assembly system. This package provides standardized communication interfaces for planar motors (XBots) and linear translation stages (LTS300).

## 📋 Overview

This package contains all custom message and service definitions used across the ProMOC assembly system, enabling consistent communication between:

- **Planar Motor System** - XBot robot control and monitoring
- **Linear Axis System** - LTS300 translation stage control
- **Assembly Coordination** - Multi-axis synchronized operations

## 📦 Package Structure

```
promoc_assembly_interfaces/
├── msg/
│   ├── linear_axis/
│   │   └── LinearAxisInfo.msg      # Linear axis status information
│   ├── planar_motor/
│   │   └── XBotInfo.msg           # XBot position and state
│   └── test/
│       └── Test.msg               # Test message
└── srv/
    ├── linear_axis/
    │   ├── MoveAbsolute.srv       # Move to absolute position
    │   ├── MoveRelativ.srv        # Move relative distance
    │   ├── Home.srv               # Home axis
    │   ├── GetPosition.srv        # Get current position
    │   ├── SetVelocityParameters.srv  # Set motion parameters
    │   ├── GetVelocityParameters.srv  # Get motion parameters
    │   └── ShutdownLinearAxis.srv # Emergency shutdown
    └── planar_motor/
        ├── ActivateXbots.srv      # Activate/deactivate XBots
        ├── LevitationXbots.srv    # Enable/disable levitation
        ├── SixDofMotion.srv       # 6DOF motion command
        ├── LinearMotionSi.srv     # Linear motion in SI units
        ├── RotaryMotion.srv       # Rotational motion
        ├── SetVelocityAcceleration.srv # Set motion dynamics
        ├── ArcMotionTargetRadius.srv   # Arc motion control
        └── StopMotion.srv         # Emergency stop
```

## 🔧 Installation

```bash
cd ~/ros2_ws
colcon build --packages-select promoc_assembly_interfaces
source install/setup.bash
```

## 📨 Message Definitions

### Linear Axis Messages

#### LinearAxisInfo.msg
Status information for linear translation stages.

```
float64 axis_position   # Current position in mm
string axis_type        # 'x' or 'z'
string serial_number    # Device serial number
string operation_status # Current operation: idle, homing, moving, jogging, error, emergency_stop
```

**Usage Example:**
```bash
ros2 topic echo /promoc_assembly/lts300_x_axis/position
```

### Planar Motor Messages

#### XBotInfo.msg
Position and state information for XBot robots.

```
float64 x_pos           # X position in mm
float64 y_pos           # Y position in mm
float64 z_pos           # Z position in mm
float64 rx_pos          # Rotation around X axis in rad
float64 ry_pos          # Rotation around Y axis in rad
float64 rz_pos          # Rotation around Z axis in rad
string xbot_state       # Current state (e.g., "idle", "moving", "error")
```

**Usage Example:**
```bash
ros2 topic echo /xbot_info
```

## 🛠️ Service Definitions

### Linear Axis Services

#### MoveAbsolute.srv
Move axis to an absolute position.

**Request:**
```
float64 axis_position   # Target position in mm
```

**Response:**
```
bool success           # Operation success
string status_message  # Status description
```

**Usage Example:**
```bash
ros2 service call /lts300_x_axis/move_absolute promoc_assembly_interfaces/srv/MoveAbsolute "{axis_position: 50.0}"
```

#### MoveRelativ.srv
Move axis by a relative distance.

**Request:**
```
float64 axis_distance   # Relative distance in mm
```

**Response:**
```
bool success           # Operation success
string status_message  # Status description
```

#### SetVelocityParameters.srv
Configure motion velocity and acceleration parameters.

**Request:**
```
float32 min_velocity    # Minimum velocity in mm/s
float32 acceleration    # Acceleration in mm/s²
float32 max_velocity    # Maximum velocity in mm/s
```

**Response:**
```
bool success                    # Operation success
string status_message           # Status description
float32 actual_min_velocity     # Actual set minimum velocity
float32 actual_acceleration     # Actual set acceleration
float32 actual_max_velocity     # Actual set maximum velocity
```

### Planar Motor Services

#### SixDofMotion.srv
Command 6-degree-of-freedom motion for XBot.

**Request:**
```
int32 xbot_id          # XBot identifier
float64 x_pos          # Target X position in mm
float64 y_pos          # Target Y position in mm
float64 z_pos          # Target Z position in mm
float64 rx_pos         # Target rotation around X in rad
float64 ry_pos         # Target rotation around Y in rad
float64 rz_pos         # Target rotation around Z in rad
```

**Response:**
```
bool success           # Operation success
string status_message  # Status description
```

**Usage Example:**
```bash
ros2 service call /mover_node/six_dof_motion promoc_assembly_interfaces/srv/SixDofMotion "{
  xbot_id: 0,
  x_pos: 10.0, y_pos: 20.0, z_pos: 5.0,
  rx_pos: 0.0, ry_pos: 0.0, rz_pos: 0.1
}"
```

#### ActivateXbots.srv
Activate or deactivate XBot robots.

**Request:**
```
bool activation_status  # true to activate, false to deactivate
```

**Response:**
```
bool success           # Operation success
bool activation_status # Actual activation status
string status_message  # Status description
```

#### LinearMotionSi.srv
Command linear motion in SI units.

**Request:**
```
int32 xbot_id          # XBot identifier
float64 x_pos          # Target X position in mm
float64 y_pos          # Target Y position in mm
float64 z_pos          # Target Z position in mm
```

**Response:**
```
bool success           # Operation success
string status_message  # Status description
```

## 🎯 Usage Examples

### Complete Linear Axis Workflow

```bash
# 1. Home the axis
ros2 service call /lts300_x_axis/home promoc_assembly_interfaces/srv/Home "{}"

# 2. Set velocity parameters
ros2 service call /lts300_x_axis/set_velocity_parameters promoc_assembly_interfaces/srv/SetVelocityParameters "{
  min_velocity: 1.0,
  acceleration: 50.0,
  max_velocity: 100.0
}"

# 3. Move to position
ros2 service call /lts300_x_axis/move_absolute promoc_assembly_interfaces/srv/MoveAbsolute "{
  axis_position: 25.0
}"

# 4. Check position
ros2 service call /lts300_x_axis/get_position promoc_assembly_interfaces/srv/GetPosition "{}"
```

### Complete Planar Motor Workflow

```bash
# 1. Activate XBots
ros2 service call /mover_node/activate_xbots promoc_assembly_interfaces/srv/ActivateXbots "{
  activation_status: true
}"

# 2. Enable levitation
ros2 service call /mover_node/levitation_xbots promoc_assembly_interfaces/srv/LevitationXbots "{
  levitate: true
}"

# 3. Move XBot
ros2 service call /mover_node/linear_motion_si promoc_assembly_interfaces/srv/LinearMotionSi "{
  xbot_id: 0,
  x_pos: 50.0,
  y_pos: 75.0,
  z_pos: 10.0
}"

# 4. Monitor position
ros2 topic echo /xbot_info
```

## 🔍 Interface Inspection

### List Available Interfaces

```bash
# List all messages
ros2 interface list | grep promoc_assembly_interfaces

# Show message definition
ros2 interface show promoc_assembly_interfaces/msg/XBotInfo
ros2 interface show promoc_assembly_interfaces/msg/LinearAxisInfo

# Show service definition
ros2 interface show promoc_assembly_interfaces/srv/SixDofMotion
ros2 interface show promoc_assembly_interfaces/srv/MoveAbsolute
```

### Runtime Service Discovery

```bash
# Find services using these interfaces
ros2 service list -t | grep promoc_assembly_interfaces

# Call service with help
ros2 service call /mover_node/six_dof_motion promoc_assembly_interfaces/srv/SixDofMotion --help
```

## 🛡️ Safety Considerations

### Service Response Patterns

All services follow a consistent response pattern:

- **success**: Boolean indicating operation success
- **status_message**: Human-readable status description
- **Additional fields**: Service-specific return values

### Error Handling

Always check the `success` field in service responses:

```python
# Python example
response = self.client.call(request)
if response.success:
    self.get_logger().info(f"Operation successful: {response.status_message}")
else:
    self.get_logger().error(f"Operation failed: {response.status_message}")
```

## 🔧 Development

### Adding New Interfaces

1. **Add message definition:**
   ```bash
   # Create new .msg file in appropriate subdirectory
   touch msg/linear_axis/NewMessage.msg
   ```

2. **Add service definition:**
   ```bash
   # Create new .srv file in appropriate subdirectory
   touch srv/planar_motor/NewService.srv
   ```

3. **Update CMakeLists.txt:**
   ```cmake
   rosidl_generate_interfaces(${PROJECT_NAME}
     "msg/linear_axis/LinearAxisInfo.msg"
     "msg/linear_axis/NewMessage.msg"          # Add new message
     "srv/planar_motor/SixDofMotion.srv"
     "srv/planar_motor/NewService.srv"         # Add new service
     # ...
   )
   ```

4. **Rebuild package:**
   ```bash
   colcon build --packages-select promoc_assembly_interfaces
   ```

### Interface Validation

```bash
# Check interface compilation
ros2 interface show promoc_assembly_interfaces/msg/YourNewMessage
ros2 interface show promoc_assembly_interfaces/srv/YourNewService
```

## 📚 Related Packages

- [linear_axis_nodes](../linear_axis_nodes/README.md) - Uses linear axis interfaces
- [planar_motor_nodes](../planar_motor_nodes/README.md) - Uses planar motor interfaces
- [promoc_bringup](../promoc_bringup/README.md) - Launch configurations

## 📝 License

TODO: Add license information

## 👥 Maintainers

- ed@todo.todo

## 📋 Changelog

### Version 0.0.0
- Initial interface definitions
- Linear axis services and messages
- Planar motor services and messages
- Basic test infrastructure
