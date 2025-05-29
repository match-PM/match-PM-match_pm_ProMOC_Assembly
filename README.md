# ProMOC Assembly Workspace

## Overview

This workspace contains ROS 2 packages for controlling and coordinating the ProMOC Assembly system, which consists of Thorlabs LTS300 and a PlanaMotor. The system is designed to work under ROS 2 Humble.

## Packages

The workspace contains the following packages:

### 1. linear_axis_nodes

Contains nodes for controlling Thorlabs LTS300 linear stages. The main node (`lts300_service_node.py`) provides services for:
- Moving to absolute positions
- Moving relative distances
- Homing the device
- Getting the current position
- Setting velocity parameters
- Shutting down the device

### 2. planar_motor_nodes

Contains nodes for controlling planar motors (XBots). The main node (`mover_service_node.py`) provides services for:
- Linear motion
- Six degrees of freedom motion
- Arc motion
- Rotary motion
- Activating/deactivating XBots
- Controlling levitation
- Setting velocity and acceleration parameters
- Stopping motion

### 3. promoc_assembly_interfaces

Contains the message and service definitions used by the other packages:
- Linear axis messages and services
- Planar motor messages and services

### 4. promoc_bringup

Contains launch files and configuration for starting the entire system.

## Installation

### Prerequisites

- ROS 2 Humble
- Python 3.8 or newer
- For linear_axis_nodes: Thorlabs Kinesis Motor library
- For planar_motor_nodes: pmclib (or use the included mock_pmclib for testing)

### Building the Workspace

```bash
# Clone the repository
cd ~/Development/Ros2/
git clone <repository-url> promoc_assembly

# Navigate to the workspace
cd promoc_assembly

# Build the workspace
colcon build

# Source the workspace
source install/setup.bash
```

## Usage

### Starting the Complete System

```bash
ros2 launch promoc_bringup promoc_assembly_launch.py
```

### Using Individual Nodes

#### Linear Axis Control

```bash
# Start the linear axis node
ros2 run linear_axis_nodes lts300_service_node

# Example: Move to an absolute position
ros2 service call /lts300_x_axis/move_absolute promoc_assembly_interfaces/srv/linear_axis/MoveAbsolute "{axis_position: 10.0}"
```

#### Planar Motor Control

```bash
# Start the planar motor node
ros2 run planar_motor_nodes mover_service_node

# Example: Perform a linear motion
ros2 service call /mover_node/linear_mover_motion promoc_assembly_interfaces/srv/planar_motor/LinearMotionSi "{xbot_id: 0, x_pos: 100.0, y_pos: 100.0}"
```

## Troubleshooting

### Linear Axis Issues

- If you can not connect to the LTS300 device, try restarting it by turning it off and on.
- Check that the correct serial number is configured in the parameters file.

### Planar Motor Issues

- If XBots are not responding, check the network connection to the PMC system.
- The mock_pmclib can be used for testing when hardware is not available.

## License

[Add license information here]

## Contact

[Add contact information here]
