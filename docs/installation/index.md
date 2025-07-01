# Installation Guide

This guide covers the complete installation of the ProMOC Assembly system.

```{toctree}
:maxdepth: 2

prerequisites
system_setup
ros2_installation
dependencies
building
validation
```

## Overview

The ProMOC Assembly system requires several components:

1. **ROS2 Environment** - Humble Hawksbill or newer
2. **System Dependencies** - .NET/Mono, build tools
3. **Python Dependencies** - Hardware control libraries
4. **PMCLib** - Proprietary planar motor library (optional)

## Quick Installation

For experienced users, use the automated installer:

```bash
cd setup/
./install_all.sh
```

## Step-by-Step Installation

For detailed control or troubleshooting, follow the individual guides:

1. {doc}`prerequisites` - Check system requirements
2. {doc}`system_setup` - Install system dependencies  
3. {doc}`ros2_installation` - Install/configure ROS2
4. {doc}`dependencies` - Install Python dependencies
5. {doc}`building` - Build the workspace
6. {doc}`validation` - Validate installation

## Installation Modes

### Development Mode
- No hardware required
- Uses simulation and mock drivers
- Fastest setup for development

### Hardware Mode  
- Requires actual hardware
- Needs PMCLib for planar motor
- Full functionality

### Hybrid Mode
- Mix of real and simulated components
- Useful for partial hardware testing

```{note}
The system automatically detects available hardware and switches between real and mock drivers as needed.
```
