## Camera Integration Setup

This guide covers the installation and configuration of IDS cameras using the camera_aravis2 package.

### 1. Install External Dependencies

The camera integration depends on the external `camera_aravis2` package:

```bash
# Navigate to your workspace
cd ~/ros2_ws/src

# Clone camera_aravis2 (if not already done via dependencies.repos)
git clone https://github.com/FraunhoferIOSB/camera_aravis2.git

# Install system dependencies
sudo apt install libaravis-dev aravis-tools
```
### Setup IDS Camera Permissions

For IDS USB3Vision cameras, create udev rules to allow user access:

```bash
sudo tee /etc/udev/rules.d/99-ids-cameras.rules <<EOF
SUBSYSTEM=="usb", ATTRS{idVendor}=="1409", ATTRS{idProduct}=="8000", MODE="0666"
EOF
```

### 2. Use vcs tool (Recommended)

If you have vcs installed, you can use the dependencies file:

```bash
cd ~/ros2_ws/src/match-PM-match_pm_ProMOC_Assembly
vcs import ~/ros2_ws/src < dependencies.repos
```

### 3. Build the packages

```bash
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --packages-select camera_aravis2 camera_nodes
```

### 4. Test the installation

```bash
# Test camera discovery
ros2 run camera_aravis2 camera_finder

# Test your camera manager
ros2 run camera_nodes camera_manager

# Test with launch file
ros2 launch camera_nodes camera_launch.py
```

### 5. Camera Configuration

Find your camera GUID and update the launch files accordingly:

```bash
# List available cameras
arv-tool-0.8

# Or use the ROS2 tool
ros2 run camera_aravis2 camera_finder
```

### External Dependencies

- **camera_aravis2**: https://github.com/FraunhoferIOSB/camera_aravis2
  - License: 3-clause BSD License
  - Maintainer: Fraunhofer IOSB
  - Purpose: GenICam camera driver for GigEVision and USB3Vision cameras

This setup keeps external dependencies separate from your project code while providing seamless integration.

## Callback User Guides

- German: [`docs/callbacks_user_guide_de.md`](docs/callbacks_user_guide_de.md)
- English: [`docs/callbacks_user_guide_en.md`](docs/callbacks_user_guide_en.md)
