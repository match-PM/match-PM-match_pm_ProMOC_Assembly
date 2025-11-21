# ProMOC Assembly Developer Guide

Welcome to the ProMOC Assembly project! This guide is designed to help you get started with development, understand the architecture, and follow best practices.

## 🏗️ Project Architecture

The project is organized into several key ROS2 packages:

### Core Components
- **`promoc_core`**: The foundation of the system. Contains shared logic, custom exceptions, error handling utilities, and common drivers.
- **`promoc_assembly_interfaces`**: Defines all custom ROS2 messages (`.msg`) and services (`.srv`). No Python code here.

### Functional Nodes
- **`planar_motor_nodes`**: Controls the XBot planar motor system. Interfaces with the .NET-based PMCLib.
- **`linear_axis_nodes`**: Controls the Thorlabs LTS300 linear axes. Handles collision detection and safety limits.
- **`camera_nodes`**: Manages the IDS industrial camera, image processing (MTF calculation), and autofocus.

### System Integration
- **`promoc_bringup`**: Contains launch files and centralized configuration.
    - `launch/system.launch.py`: Main entry point.
    - `config/`: Central location for all `.yaml` configuration files.

## 🚀 Development Workflow

### 1. Environment Setup
Ensure you have ROS2 Humble installed.
```bash
# Source ROS2
source /opt/ros/humble/setup.bash
```

### 2. Building the Workspace
We use `colcon` for building. Always build from the workspace root.
```bash
colcon build --symlink-install
```
*Note: `--symlink-install` allows you to change Python files without rebuilding.*

### 3. Running the System
Source the overlay before running:
```bash
source install/setup.bash  # Linux
call install/setup.bat     # Windows
```

**Simulation Mode (Default for Dev):**
```bash
ros2 launch promoc_bringup system.launch.py sim_mode:=true
```

**Hardware Mode:**
```bash
ros2 launch promoc_bringup system.launch.py sim_mode:=false
```

## 🛡️ Error Handling
We use a centralized error handling system in `promoc_core`.
- **Exceptions**: Import from `promoc_core.promoc_exceptions`.
- **Service Handling**: Use the `@handle_service_errors` decorator from `promoc_core.error_handling`.

Example:
```python
from promoc_core.promoc_exceptions import HardwareError
from promoc_core.error_handling import handle_service_errors

@handle_service_errors
def my_service_callback(self, request, response):
    if not device.is_connected():
        raise HardwareError("Device not connected")
    # ...
```
See `promoc_core/ERROR_HANDLING.md` for full details.

## 🧪 Testing
Run tests using `colcon test`:
```bash
colcon test --packages-select promoc_core
colcon test-result --all
```

## 📝 Configuration
All configuration files are in `promoc_bringup/config`.
- **`linear_axes_params.yaml`**: Axis serial numbers and limits.
- **`camera_node_params.yaml`**: Camera settings (exposure, gain).
- **`mover_node_params.yaml`**: Planar motor settings.

When adding new parameters, add them to the appropriate file in `config/` and update the node to declare them.

## 🖥️ VS Code Configuration
To get the best development experience, we recommend adding the following to your `.vscode/settings.json`:

```json
{
    "python.autoComplete.extraPaths": [
        "${workspaceFolder}/install/promoc_assembly_interfaces/local/lib/python3.10/dist-packages",
        "${workspaceFolder}/promoc_core"
    ],
    "python.analysis.extraPaths": [
        "${workspaceFolder}/install/promoc_assembly_interfaces/local/lib/python3.10/dist-packages",
        "${workspaceFolder}/promoc_core"
    ],
    "python.formatting.provider": "autopep8",
    "editor.formatOnSave": true,
    "files.associations": {
        "*.launch.py": "python",
        "*.xacro": "xml"
    },
    "search.exclude": {
        "**/build": true,
        "**/install": true,
        "**/log": true
    }
}
```
