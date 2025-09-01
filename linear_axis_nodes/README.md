# Linear Axis Nodes

A ROS2 package for controlling Thorlabs LTS300 linear translation stages. This package provides a comprehensive interface to control X and Z-axis linear actuators with collision detection and safety features.

## 🏗️ Architecture

The package follows a clean, modular architecture with separated concerns:

```
linear_axis_nodes/
├── lts300_node.py         # Main ROS2 node (orchestrator)
├── lts300_interface.py    # Hardware communication layer
├── service_callbacks.py   # ROS service implementations
├── node_config.py         # Configuration management
└── drivers/
    ├── linear_axis_driver.py           # Abstract base interface
    ├── thorlabs_lts300_driver.py       # Hardware driver
    └── simulated_linear_axis_driver.py # Simulation driver
```

### Key Components

- **LTS300Node**: Main ROS2 node that orchestrates all components
- **Lts300Interface**: Abstraction layer for hardware communication
- **ServiceCallbacks**: Implements all ROS service handlers with collision detection
- **ThorlabsLTS300Driver**: Real hardware driver using pylablib
- **Lts300Config**: Configuration dataclass for parameter management

## 📦 Dependencies

### ROS2 Dependencies
- `rclpy` - ROS2 Python client library
- `std_msgs` - Standard ROS2 message types
- `promoc_assembly_interfaces` - Custom interface package

### Hardware Dependencies
- Thorlabs LTS300 linear translation stages
- `pylablib` - Python library for Thorlabs hardware control
- USB connection via serial port (typically `/dev/ttyUSB0`)

## 🚀 Installation

1. **Install Python dependencies:**
   ```bash
   pip install pylablib
   ```

2. **Build the workspace:**
   ```bash
   cd ~/ros2_ws
   colcon build --packages-select linear_axis_nodes promoc_assembly_interfaces
   source install/setup.bash
   ```

3. **Setup hardware permissions:**
   ```bash
   # Add user to dialout group for USB access
   sudo usermod -a -G dialout $USER
   # Logout and login again for changes to take effect
   ```

## 🎮 Usage

### Basic Startup

1. **Start X-axis node:**
   ```bash
   ros2 run linear_axis_nodes lts300_node --ros-args \
     -r __node:=lts300_x_axis \
     -p serial_port:=/dev/ttyUSB0 \
     -p serial_number:=45874027 \
     -p debug_mode:=true
   ```

2. **Start Z-axis node:**
   ```bash
   ros2 run linear_axis_nodes lts300_node --ros-args \
     -r __node:=lts300_z_axis \
     -p serial_port:=/dev/ttyUSB1 \
     -p serial_number:=45874029 \
     -p debug_mode:=true
   ```

3. **Using launch files:**
   ```bash
   ros2 launch promoc_bringup promoc_assembly_launch.py
   ```

### Service Interface

#### Motion Control Services

**Move to Absolute Position:**
```bash
ros2 service call /lts300_x_axis/move_absolute promoc_assembly_interfaces/srv/MoveAbsolute "{
  axis_position: 50.0
}"
```

**Move Relative Distance:**
```bash
ros2 service call /lts300_x_axis/move_relative promoc_assembly_interfaces/srv/MoveRelativ "{
  axis_distance: 10.0
}"
```

**Home the Axis:**
```bash
ros2 service call /lts300_x_axis/home promoc_assembly_interfaces/srv/Home "{}"
```

**Get Current Position:**
```bash
ros2 service call /lts300_x_axis/get_position promoc_assembly_interfaces/srv/GetPosition "{}"
```

**Set Velocity Parameters:**
```bash
ros2 service call /lts300_x_axis/set_velocity_parameters promoc_assembly_interfaces/srv/SetVelocityParameters "{
  max_velocity: 50.0,
  acceleration: 100.0
}"
```

**Get Velocity Parameters:**
```bash
ros2 service call /lts300_x_axis/get_velocity_parameters promoc_assembly_interfaces/srv/GetVelocityParameters "{}"
```

### Topic Interface

**Monitor Axis Position:**
```bash
ros2 topic echo /promoc_assembly/lts300_x_axis/position
ros2 topic echo /promoc_assembly/lts300_z_axis/position
```

**List all available services:**
```bash
ros2 service list | grep lts300
```

## ⚙️ Configuration

### ROS Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `debug_mode` | bool | `false` | Enable debug logging |
| `use_sim_time` | bool | `false` | Use simulation instead of hardware |
| `serial_port` | string | `/dev/ttyUSB0` | USB serial port for communication |
| `serial_number` | string | `00000000` | Hardware serial number |
| `collision_threshold` | float | `300.0` | Safety distance threshold (mm) |
| `namespace` | string | `promoc_assembly` | ROS topic namespace |

### Example Parameter Files

**X-Axis Configuration (`config/x_axis_params.yaml`):**
```yaml
lts300_x_axis:
  ros__parameters:
    debug_mode: true
    serial_port: "/dev/ttyUSB0"
    serial_number: "45874027"
    collision_threshold: 280.0
    namespace: "promoc_assembly"
```

**Z-Axis Configuration (`config/z_axis_params.yaml`):**
```yaml
lts300_z_axis:
  ros__parameters:
    debug_mode: true
    serial_port: "/dev/ttyUSB1"
    serial_number: "45874029"
    collision_threshold: 300.0
    namespace: "promoc_assembly"
```

## 🛡️ Safety Features

### Collision Detection

The package includes intelligent collision detection between X and Z axes:

- **Cross-axis monitoring**: Each axis monitors the other's position
- **Safety thresholds**: Configurable collision thresholds prevent crashes
- **Automatic prevention**: Motion commands are rejected if collision risk detected
- **Status feedback**: Clear error messages indicate collision risks

### Hardware Limits

- **End-stop detection**: Automatic detection of travel limits
- **Homing capability**: Safe return to reference position
- **Velocity limits**: Configurable speed and acceleration constraints

## 🔧 Development

### Simulation Mode

Test without hardware using simulation mode:

```bash
ros2 run linear_axis_nodes lts300_node --ros-args \
  -p use_sim_time:=true \
  -p debug_mode:=true
```

### Adding New Services

1. Define the service in `promoc_assembly_interfaces`
2. Add the callback method to `ServiceCallbacks` class
3. Register the service in `LTS300Node._setup_ros_communication()`

### Hardware Integration

The driver automatically detects axis type (X or Z) based on serial number:
- Connects to hardware via pylablib
- Handles unit conversions (mm ↔ device units)
- Manages communication protocols

## 🧪 Testing

Run the package tests:
```bash
cd ~/ros2_ws
colcon test --packages-select linear_axis_nodes
colcon test-result --verbose
```

Available tests:
- Copyright compliance
- Code style (flake8)
- Docstring style (pep257)

## 🚨 Troubleshooting

### Common Issues

**"Failed to connect to hardware"**
- Check USB cable connections
- Verify correct serial port (`/dev/ttyUSB0`, `/dev/ttyUSB1`)
- Ensure user is in `dialout` group
- Check hardware power supply

**"Permission denied on serial port"**
```bash
sudo chmod 666 /dev/ttyUSB0
# Or permanently:
sudo usermod -a -G dialout $USER
```

**"Collision detected"**
- Check current positions: `ros2 topic echo /promoc_assembly/lts300_x_axis/position`
- Adjust collision threshold parameter
- Home both axes to reset positions

**"Service call timeout"**
- Verify node is running: `ros2 node list | grep lts300`
- Check hardware connection status
- Enable debug mode for detailed logging

### Debug Commands

```bash
# Check node status
ros2 node info /lts300_x_axis

# Monitor all topics
ros2 topic list | grep lts300

# Check service availability
ros2 service list | grep lts300

# View parameter values
ros2 param list /lts300_x_axis
ros2 param get /lts300_x_axis serial_number

# Test hardware connection
ros2 service call /lts300_x_axis/get_position promoc_assembly_interfaces/srv/GetPosition "{}"
```

### Hardware Verification

```bash
# Check USB devices
lsusb | grep Thorlabs

# Check serial ports
ls -la /dev/ttyUSB*

# Test serial communication
sudo dmesg | grep ttyUSB
```

## 📚 Additional Resources

- [ProMOC Assembly Interfaces](../promoc_assembly_interfaces/README.md)
- [Thorlabs LTS300 Manual](https://www.thorlabs.com/)
- [PyLabLib Documentation](https://pylablib.readthedocs.io/)
- [Launch Files](../promoc_bringup/README.md)

## 📝 License

TODO: Add license information

## 👥 Maintainers

- promoc@todo.todo
