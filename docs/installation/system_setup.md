# System Setup

## Initial System Configuration

### Update System Packages
```bash
sudo apt update && sudo apt upgrade -y
```

### Install Essential Build Tools
```bash
sudo apt install -y \
    build-essential \
    cmake \
    git \
    python3-dev \
    python3-pip \
    curl \
    wget \
    software-properties-common
```

### Configure Git (if not already done)
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

## Python Environment Setup

### Install Python Package Manager
```bash
# Ensure pip is up to date
python3 -m pip install --upgrade pip

# Install virtual environment tools
sudo apt install -y python3-venv python3-virtualenv
```

### Create Project Virtual Environment (Optional but Recommended)
```bash
# Create virtual environment
python3 -m venv ~/promoc_venv

# Activate virtual environment
source ~/promoc_venv/bin/activate

# Upgrade pip in virtual environment
pip install --upgrade pip
```

## Workspace Setup

### Create ROS2 Workspace
```bash
# Create workspace directory
mkdir -p ~/ros2_ws/src

# Navigate to workspace
cd ~/ros2_ws
```

### Set Workspace Permissions
```bash
# Ensure proper permissions
sudo chown -R $USER:$USER ~/ros2_ws
chmod -R 755 ~/ros2_ws
```

## System Configuration Files

### Configure Environment Variables
Add the following to your `~/.bashrc`:

```bash
# ROS2 Environment
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=1

# ProMOC Assembly Workspace
export PROMOC_WS=~/ros2_ws
alias promoc_ws='cd $PROMOC_WS'

# Python Path (if using virtual environment)
# export PYTHONPATH=$PROMOC_WS/install/lib/python3.10/site-packages:$PYTHONPATH
```

### Reload Environment
```bash
source ~/.bashrc
```

## Hardware-Specific Setup

### USB Device Permissions (for Thorlabs LTS300)
```bash
# Add user to dialout group for USB access
sudo usermod -a -G dialout $USER

# Create udev rule for Thorlabs devices
sudo tee /etc/udev/rules.d/99-thorlabs.rules << EOF
# Thorlabs LTS300 Linear Translation Stage
SUBSYSTEM=="usb", ATTRS{idVendor}=="1313", MODE="0666", GROUP="dialout"
EOF

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Network Configuration (for Planar Motor)
If using Ethernet-connected planar motor:

```bash
# Configure static IP (adjust interface name and IP as needed)
sudo tee /etc/netplan/99-planar-motor.yaml << EOF
network:
  version: 2
  ethernets:
    enp0s3:  # Replace with your actual interface name
      dhcp4: false
      addresses:
        - 192.168.1.100/24
      gateway4: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
EOF

# Apply network configuration
sudo netplan apply
```

## Verification

### Test System Configuration
```bash
# Check Python version
python3 --version

# Check Git configuration
git config --list

# Check USB devices (should show Thorlabs if connected)
lsusb | grep -i thorlabs

# Check network interfaces
ip addr show
```

### Test Permissions
```bash
# Test USB access
ls -la /dev/ttyUSB* || echo "No USB devices found"

# Test workspace access
touch $PROMOC_WS/test_file && rm $PROMOC_WS/test_file && echo "Workspace writable"
```

## Troubleshooting

### Permission Issues
If you encounter permission errors:
```bash
# Re-add user to groups
sudo usermod -a -G dialout,plugdev $USER

# Log out and log back in to apply group changes
```

### Network Issues
If planar motor network connection fails:
```bash
# Check network interface
ip link show

# Test connectivity
ping -c 3 192.168.1.1  # Replace with your gateway
```

## Next Steps
After completing system setup, proceed to {doc}`ros2_installation`.
