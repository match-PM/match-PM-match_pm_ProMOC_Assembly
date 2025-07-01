# Prerequisites

## System Requirements

### Operating System
- **Ubuntu 20.04 LTS** (Focal Fossa) - Recommended
- **Ubuntu 22.04 LTS** (Jammy Jellyfish) - Supported  
- **Ubuntu 24.04 LTS** (Noble Numbat) - Supported

### Hardware Requirements
- **Minimum**: 4GB RAM, 2 CPU cores, 20GB disk space
- **Recommended**: 8GB RAM, 4 CPU cores, 50GB disk space
- **USB ports**: For Thorlabs LTS300 controllers
- **Network**: For planar motor communication

### Software Dependencies
- **Python**: 3.8 or newer
- **Git**: For source code management
- **Build tools**: GCC, CMake, Make

## ROS2 Compatibility
- **ROS2 Humble Hawksbill** (Recommended)
- **ROS2 Iron Irwini** (Supported)
- **ROS2 Jazzy Jalisco** (Experimental)

## Hardware Compatibility

### Supported Linear Axes
- **Thorlabs LTS300** - Primary supported controller
- **Generic linear stages** - Via driver abstraction layer

### Supported Planar Motors
- PMCLib-compatible planar motor systems
- Custom planar motor implementations via driver interface

## Optional Components
- **Gazebo Classic** - For simulation
- **RViz2** - For visualization
- **MoveIt2** - For motion planning (future integration)

## Next Steps
After verifying your system meets these requirements, proceed to the {doc}`system_setup` guide.
