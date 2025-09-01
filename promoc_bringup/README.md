# ProMOC Bringup

A ROS2 launch package for the ProMOC assembly system. This package provides launch files, configuration files, and utilities to start the complete system including planar motors (XBots) and linear translation stages (LTS300).

## 📋 Overview

The `promoc_bringup` package serves as the main entry point for launching the ProMOC assembly system. It coordinates the startup of:

- **Planar Motor System** - XBot robot control nodes
- **Linear Axis System** - LTS300 translation stage nodes with auto-discovery
- **Demo Controllers** - Automated demonstration sequences
- **System Configuration** - Centralized parameter management

## 📦 Package Structure

```
promoc_bringup/
├── launch/
│   ├── promoc_assembly_launch.py       # Main system launch
│   ├── promoc_assembly_demo_launch.py  # Demo system launch
│   └── planar_motor_demo_launch.py     # Planar motor only demo
├── config/
│   ├── mover_node_params.yaml          # Planar motor configuration
│   ├── linear_axes_params.yaml         # Linear axes configuration
│   └── demo_controller.yaml            # Demo controller settings
├── promoc_bringup/
│   ├── demo_controller.py              # Automated demo controller
│   └── pm_demo.py                      # Planar motor demo utilities
└── urdf/
    ├── assemblies/                     # Complete system descriptions
    ├── modules/                        # Individual component models
    └── properties/                     # Material and property definitions
```

## 🚀 Quick Start

### 1. Basic System Launch

Start the complete ProMOC assembly system:

```bash
ros2 launch promoc_bringup promoc_assembly_launch.py
```

This will:
- Auto-discover connected LTS300 devices via USB serial
- Launch planar motor node with configuration
- Start linear axis nodes for detected hardware
- Provide all ROS services for system control

### 2. Demo System Launch

Start the system with automated demo controller:

```bash
ros2 launch promoc_bringup promoc_assembly_demo_launch.py
```

This includes everything from the basic launch plus:
- Automated demo controller node
- Predefined motion sequences
- Continuous demonstration loop

### 3. Planar Motor Only Demo

Launch only the planar motor system for testing:

```bash
ros2 launch promoc_bringup planar_motor_demo_launch.py
```

## 🔧 Launch Files

### promoc_assembly_launch.py

**Main system launch file with intelligent hardware discovery.**

**Features:**
- **Auto-discovery**: Scans `/dev/serial/by-id/` for Thorlabs devices
- **Dynamic configuration**: Matches detected hardware to configured axes
- **Stable device paths**: Uses persistent USB identifiers
- **Graceful handling**: Skips missing hardware with warnings

**Hardware Detection:**
```bash
# Shows detected devices during launch
🛰️  Scanning for connected devices in /dev/serial/by-id/...
  -> Detected device: usb-Thorlabs_APT_Stepper_Motor_Controller_45407924 (serial: 45407924)
  -> Found 2 device(s).

🛰️  Matching connected devices to launch dynamic nodes:
  ✅ 'lts300_x_axis' is connected. Creating node.
  ✅ 'lts300_z_axis' is connected. Creating node.
```

### promoc_assembly_demo_launch.py

**Complete system with automated demonstration.**

Extends the base system launch with:
- Demo controller node for automated sequences
- Predefined motion patterns
- Continuous operation mode

### planar_motor_demo_launch.py

**Simplified launch for planar motor development.**

Includes only:
- Planar motor node
- Basic demo functionality
- No linear axis dependencies

## ⚙️ Configuration Files

### mover_node_params.yaml

**Planar motor system configuration.**

```yaml
mover_node:
  ros__parameters:
    node_name: 'mover_node'
    debug_mode: false
    # Movement boundaries (meters)
    x_min: 0.055
    x_max: 0.420
    y_min: -0.055
    y_max: 0.180
    z_min: 0.000
    z_max: 0.004
    # Tolerances (meters)
    xy_tolerance: 0.001
    six_d_tolerance: 0.001
    # Standard velocity parameters
    standard_velocities:
      xy_vel: 1.00        # m/s
      z_vel: 0.10         # m/s
      rx_vel: 0.10        # rad/s
      ry_vel: 0.10        # rad/s
      rz_vel: 0.10        # rad/s
      xy_max_accel: 5.00  # m/s²
      z_max_accel: 1.00   # m/s²
```

### linear_axes_params.yaml

**Linear axis system configuration.**

```yaml
lts300_z_axis:
  ros__parameters:
    debug_mode: false
    serial_number: '45407924'           # Hardware serial number
    collision_threshold: 200.0          # Safety distance (mm)
    device_units_per_mm: 409600.0      # Hardware scaling factor

lts300_x_axis:
  ros__parameters:
    debug_mode: false
    serial_number: '45456044'
    collision_threshold: 200.0
    device_units_per_mm: 409600.0
```

## 🤖 Demo Controller

### Automated Demo Sequences

The demo controller provides automated demonstration of system capabilities:

**Features:**
- **Multi-axis coordination**: Synchronized motion between planar and linear systems
- **Safety integration**: Collision detection and prevention
- **Continuous operation**: Endless demo loop with configurable delays
- **Status monitoring**: Real-time position and state feedback

**Demo Sequence:**
1. **System Initialization**
   - Activate XBots
   - Enable levitation
   - Home all linear axes

2. **Coordinated Motion**
   - Move XBot to predefined positions
   - Coordinate with linear axis movements
   - Demonstrate 6DOF capabilities

3. **Safety Demonstrations**
   - Show collision detection
   - Display emergency stop functionality
   - Validate safety thresholds

### Demo Controller Parameters

```yaml
demo_controller:
  ros__parameters:
    axes: ['lts300_x_axis', 'lts300_z_axis']
    xbot_id: 1
    cycle_delay: 5.0          # Seconds between demo cycles
    demo_positions:           # Predefined motion targets
      - [100.0, 150.0, 10.0]  # XBot positions [x, y, z]
      - [200.0, 100.0, 15.0]
      - [150.0, 200.0, 5.0]
```

## 🔍 System Monitoring

### Runtime Monitoring Commands

```bash
# Check all running nodes
ros2 node list

# Monitor system status
ros2 topic echo /xbot_info
ros2 topic echo /promoc_assembly/lts300_x_axis/position
ros2 topic echo /promoc_assembly/lts300_z_axis/position

# List available services
ros2 service list | grep -E "(mover_node|lts300)"

# Check parameter values
ros2 param list /mover_node
ros2 param get /mover_node debug_mode
```

### Hardware Verification

```bash
# Check connected USB devices
lsusb | grep Thorlabs

# Verify stable device paths
ls -la /dev/serial/by-id/usb-Thorlabs*

# Check system log for device detection
ros2 launch promoc_bringup promoc_assembly_launch.py 2>&1 | grep -E "(Detected|Found|connected)"
```

## 🛠️ Development

### Custom Launch Files

Create custom launch configurations:

```python
# my_custom_launch.py
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    bringup_share = get_package_share_directory('promoc_bringup')
    
    # Include base system
    base_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, 'launch', 'promoc_assembly_launch.py')
        )
    )
    
    # Add custom nodes here
    
    return LaunchDescription([base_launch])
```

### Adding New Hardware

1. **Update configuration:**
   ```yaml
   # In linear_axes_params.yaml
   lts300_new_axis:
     ros__parameters:
       debug_mode: false
       serial_number: 'YOUR_SERIAL_HERE'
       collision_threshold: 200.0
   ```

2. **Hardware detection:**
   The launch system will automatically detect and configure new hardware based on USB serial numbers.

### Parameter Overrides

Override parameters at launch time:

```bash
ros2 launch promoc_bringup promoc_assembly_launch.py \
  mover_node.debug_mode:=true \
  lts300_x_axis.collision_threshold:=150.0
```

## 🧪 Testing

### System Integration Tests

```bash
# Test hardware discovery
ros2 launch promoc_bringup promoc_assembly_launch.py --show-args

# Verify all services are available
ros2 service list | grep -c -E "(mover_node|lts300)" && echo "All services detected"

# Test basic functionality
ros2 service call /mover_node/activate_xbots promoc_assembly_interfaces/srv/ActivateXbots "{activation_status: true}"
```

### Simulation Mode

Run without hardware for development:

```bash
# Mock mode for development
ros2 launch promoc_bringup promoc_assembly_launch.py \
  use_sim_time:=true \
  debug_mode:=true
```

## 🚨 Troubleshooting

### Common Issues

**"No devices found"**
- Check USB connections
- Verify device permissions: `sudo usermod -a -G dialout $USER`
- Check if devices appear: `lsusb | grep Thorlabs`

**"Node not starting"**
- Check configuration file paths
- Verify package dependencies are built
- Enable debug mode for detailed logging

**"Service calls failing"**
- Ensure all nodes are running: `ros2 node list`
- Check service availability: `ros2 service list`
- Verify hardware is connected and responding

### Debug Mode

Enable comprehensive logging:

```bash
ros2 launch promoc_bringup promoc_assembly_launch.py \
  mover_node.debug_mode:=true \
  lts300_x_axis.debug_mode:=true \
  lts300_z_axis.debug_mode:=true
```

## 📚 Related Packages

- [promoc_assembly_interfaces](../promoc_assembly_interfaces/README.md) - Message and service definitions
- [planar_motor_nodes](../planar_motor_nodes/README.md) - XBot control nodes
- [linear_axis_nodes](../linear_axis_nodes/README.md) - LTS300 control nodes

## 📝 License

TODO: Add license information

## 👥 Maintainers

- your_email@example.com

## 📋 Changelog

### Version 0.1.0
- Initial bringup package
- Hardware auto-discovery
- Demo controller implementation
- Configuration management
- URDF models and descriptions
