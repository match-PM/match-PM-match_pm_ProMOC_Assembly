# ROS2 Installation

## Install ROS2 Humble Hawksbill

### Add ROS2 APT Repository
```bash
# Ensure locale supports UTF-8
sudo apt update && sudo apt install locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# Add ROS2 GPG key
sudo apt install software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install curl -y
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg

# Add ROS2 repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
```

### Install ROS2 Packages
```bash
# Update package list
sudo apt update

# Install ROS2 Desktop (full installation)
sudo apt install ros-humble-desktop

# Install development tools
sudo apt install \
    ros-dev-tools \
    ros-humble-gazebo-ros-pkgs \
    ros-humble-control-msgs \
    ros-humble-controller-manager \
    ros-humble-hardware-interface \
    ros-humble-joint-state-publisher \
    ros-humble-robot-state-publisher \
    ros-humble-xacro
```

### Install Additional ROS2 Tools
```bash
# Install colcon build tool
sudo apt install python3-colcon-common-extensions

# Install rosdep for dependency management
sudo apt install python3-rosdep
sudo rosdep init
rosdep update

# Install vcstool for repository management
sudo apt install python3-vcstool

# Install testing tools
sudo apt install \
    python3-pytest \
    python3-pytest-cov \
    ros-humble-launch-testing \
    ros-humble-launch-testing-ament-cmake
```

## Environment Setup

### Configure ROS2 Environment
Add the following to your `~/.bashrc`:

```bash
# Source ROS2 setup
source /opt/ros/humble/setup.bash

# Source workspace (add this after building the workspace)
# source ~/ros2_ws/install/setup.bash

# ROS2 Environment Variables
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=1

# Gazebo model path (for simulation)
export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:~/ros2_ws/src/promoc_assembly/models
```

### Reload Environment
```bash
source ~/.bashrc
```

## Verify ROS2 Installation

### Test ROS2 Commands
```bash
# Check ROS2 version
ros2 --version

# List available ROS2 commands
ros2 -h

# Test node discovery
ros2 node list

# Test topic functionality
ros2 topic list
```

### Test ROS2 Communication
Open two terminals and run:

**Terminal 1:**
```bash
source /opt/ros/humble/setup.bash
ros2 run demo_nodes_cpp talker
```

**Terminal 2:**
```bash
source /opt/ros/humble/setup.bash
ros2 run demo_nodes_py listener
```

You should see messages being passed between the nodes.

### Test Gazebo Integration
```bash
# Test Gazebo launch
ros2 launch gazebo_ros gazebo.launch.py

# In another terminal, verify Gazebo is running
ros2 service list | grep gazebo
```

## Alternative ROS2 Versions

### ROS2 Iron (Alternative)
If you need ROS2 Iron instead of Humble:

```bash
# Replace 'humble' with 'iron' in all commands above
sudo apt install ros-iron-desktop
source /opt/ros/iron/setup.bash
```

### ROS2 Jazzy (Experimental)
For the latest ROS2 Jazzy (Ubuntu 24.04 only):

```bash
# Replace 'humble' with 'jazzy' in repository setup
sudo apt install ros-jazzy-desktop
source /opt/ros/jazzy/setup.bash
```

## Build Dependencies

### Install Core Build Dependencies
```bash
# Install Python build dependencies
pip3 install \
    setuptools \
    wheel \
    pycparser \
    empy \
    lark

# Install ROS2 Python dependencies
sudo apt install \
    python3-flake8 \
    python3-pytest \
    python3-setuptools \
    python3-pip
```

### Install Workspace-Specific Dependencies
```bash
# Navigate to workspace
cd ~/ros2_ws

# Install dependencies for all packages
rosdep install --from-paths src --ignore-src -r -y
```

## Troubleshooting

### Common Installation Issues

#### GPG Key Errors
```bash
# If you get GPG key errors, try:
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654
```

#### Package Not Found
```bash
# Update package lists and try again
sudo apt update
sudo apt-cache search ros-humble
```

#### Environment Sourcing Issues
```bash
# Verify ROS2 installation path
ls /opt/ros/
ls /opt/ros/humble/setup.bash

# Manually source and test
source /opt/ros/humble/setup.bash
echo $ROS_DISTRO
```

#### Permission Issues with rosdep
```bash
# Fix rosdep permissions
sudo rm -rf /etc/ros/rosdep/
sudo rosdep init
rosdep update
```

### Performance Optimization

#### DDS Configuration
For better performance, configure DDS:

```bash
# Add to ~/.bashrc for FastDDS
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTRTPS_DEFAULT_PROFILES_FILE=/path/to/fastdds_profile.xml
```

#### Memory Limits
For large workspaces:

```bash
# Increase memory limits for compilation
export MAKEFLAGS=-j$(nproc --ignore=2)
```

## Next Steps
After ROS2 installation, proceed to {doc}`dependencies` to install project-specific dependencies.
