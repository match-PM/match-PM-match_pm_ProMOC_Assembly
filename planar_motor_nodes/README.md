# Planar Motor Nodes

A ROS2 package for controlling planar motor systems with XBot robots. This package provides a comprehensive interface to interact with the PMC (Planar Motor Controller) hardware through standardized ROS2 services and topics.

## 🏗️ Architecture

The package follows a clean, modular architecture with separated concerns:

```
planar_motor_nodes/
├── mover_node.py          # Main ROS2 node (orchestrator)
├── pmc_interface.py       # Hardware communication layer
├── position_utils.py      # Position calculations and utilities
├── service_callbacks.py   # ROS service implementations
├── node_config.py         # Configuration management
└── drivers/
    ├── mock_pmclib.py     # Simulation driver
    └── match_pm_xBot/     # Hardware driver library
```

### Key Components

- **MoverServiceNode**: Main ROS2 node that orchestrates all components
- **PmcInterface**: Abstraction layer for PMC hardware communication
- **PositionUtils**: Utility class for position management and calculations
- **ServiceCallbacks**: Implements all ROS service handlers
- **NodeConfig**: Configuration dataclass for parameter management

## 📦 Dependencies

### ROS2 Dependencies
- `rclpy` - ROS2 Python client library
- `std_msgs` - Standard ROS2 message types
- `promoc_assembly_interfaces` - Custom interface package

### Hardware Dependencies
- PMC hardware controller (IP: 192.168.10.100)
- PMCLIB.dll (for full functionality, use the match_PM_xBot repo and clone it into the drivers folder)


## 🚀 Installation

1. **Clone and build the workspace:**
   ```bash
   cd ~/ros2_ws/src
   # Package should already be present in your workspace
   cd ~/ros2_ws
   colcon build --packages-select planar_motor_nodes promoc_assembly_interfaces
   source install/setup.bash
   ```

2. **Install system dependencies:**
   ```bash
   # Follow setup instructions in ../../setup/README.md
   ./setup/install_all.sh
   ```

## 🎮 Usage

### Basic Startup

1. **Start the mover node:**
   ```bash
   ros2 run planar_motor_nodes mover_node
   ```

2. **With custom parameters:**
   ```bash
   ros2 run planar_motor_nodes mover_node --ros-args \
     -p use_mock:=true \
     -p debug_mode:=true \
     -p xbot_id:=0
   ```

3. **Using launch files:**
   ```bash
   ros2 launch promoc_bringup promoc_assembly_launch.py
   ros2 launch promoc_bringup promoc_assembly_demo_launch.py
   ```

### Service Interface

#### Motion Control Services

**Activate XBots:**
```bash
ros2 service call /mover_node/activate_xbots promoc_assembly_interfaces/srv/ActivateXbots "{activate: true}"
```

**Enable Levitation:**
```bash
ros2 service call /mover_node/levitation_xbots promoc_assembly_interfaces/srv/LevitationXbots "{levitate: true}"
```

**Linear Motion (SI units):**
```bash
ros2 service call /mover_node/linear_motion_si promoc_assembly_interfaces/srv/LinearMotionSi "{
  x_pos: 10.0,
  y_pos: 20.0,
  z_pos: 5.0,
  xbot_id: 0
}"
```

**6DOF Motion:**
```bash
ros2 service call /mover_node/six_dof_motion promoc_assembly_interfaces/srv/SixDofMotion "{
  x_pos: 10.0, y_pos: 20.0, z_pos: 5.0,
  rx_pos: 0.0, ry_pos: 0.0, rz_pos: 0.1,
  xbot_id: 0
}"
```

**Rotary Motion:**
```bash
ros2 service call /mover_node/rotary_motion promoc_assembly_interfaces/srv/RotaryMotion "{
  angle: 1.57,  # 90 degrees in radians
  xbot_id: 0
}"
```

**Stop Motion:**
```bash
ros2 service call /mover_node/stop_motion promoc_assembly_interfaces/srv/StopMotion "{}"
```

**Set Velocity/Acceleration:**
```bash
ros2 service call /mover_node/set_velocity_acceleration promoc_assembly_interfaces/srv/SetVelocityAcceleration "{
  velocity: 50.0,
  acceleration: 100.0,
  xbot_id: 0
}"
```

### Topic Interface

**Monitor XBot Status:**
```bash
ros2 topic echo /xbot_info
```

**List all available services:**
```bash
ros2 service list | grep mover_node
```

## ⚙️ Configuration

### ROS Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_mock` | bool | `false` | Use simulation instead of hardware |
| `debug_mode` | bool | `false` | Enable debug logging |
| `xbot_id` | int | `0` | Default XBot ID to control |
| `publish_rate` | float | `10.0` | Rate for position publishing (Hz) |
| `connection_timeout` | float | `5.0` | PMC connection timeout (seconds) |

### Example Parameter File

Create `config/mover_node_params.yaml`:
```yaml
mover_node:
  ros__parameters:
    use_mock: false
    debug_mode: true
    xbot_id: 0
    publish_rate: 20.0
    connection_timeout: 10.0
```

## 🔧 Development

### Mock Mode for Testing

The package includes a mock driver for testing without hardware:

```bash
ros2 run planar_motor_nodes mover_node --ros-args -p use_mock:=true
```

### Adding New Services

1. Define the service in `promoc_assembly_interfaces`
2. Add the callback method to `ServiceCallbacks` class
3. Register the service in `MoverServiceNode._setup_services()`

### Debugging

Enable debug mode for verbose logging:
```bash
ros2 run planar_motor_nodes mover_node --ros-args -p debug_mode:=true
```

## 🧪 Testing

Run the package tests:
```bash
cd ~/ros2_ws
colcon test --packages-select planar_motor_nodes
colcon test-result --verbose
```

Available tests:
- Copyright compliance
- Code style (flake8)
- Docstring style (pep257)

## 🚨 Troubleshooting

### Common Issues

**"PMC Connection Failed"**
- Check network connection to 192.168.10.100
- Verify PMC hardware is powered and accessible
- We usually perform repeated connection attempts to the PMC; this can take some time while we try different ports on the device's IP address (192.168.10.100).
- Try power-cycling the PMC (turn it off and on); this often resolves connection issues.
- Try using mock mode: `use_mock:=true`

**"XBot not available"**
- Check if XBots are properly connected to PMC
- Verify correct `xbot_id` parameter
- Check XBot status via `/xbot_info` topic

**"Service call failed"**
- Ensure XBots are activated (`activate_xbots` service)
- Check motion parameters are within valid ranges

### Debug Commands

```bash
# Check node status
ros2 node info /mover_node

# Monitor all topics
ros2 topic list

# Check service availability
ros2 service list | grep mover

# View parameter values
ros2 param list /mover_node
ros2 param get /mover_node use_mock
```

## 📚 Additional Resources

- [ProMOC Assembly Interfaces](../promoc_assembly_interfaces/README.md)
- [Setup Guide](../../setup/README.md)
- [Launch Files](../promoc_bringup/README.md)

## 📝 License

TODO: Add license information

## 👥 Maintainers

- pmlab_mover@todo.todo
