# System Architecture Overview

The ProMOC Assembly system follows a modular, layered architecture designed for flexibility, maintainability, and scalability.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ Assembly Tasks  │  │ Motion Planning │                  │
│  │ & Coordination  │  │ & Sequencing    │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                     ROS2 Service Layer                      │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ Linear Axis     │  │ Planar Motor    │                  │
│  │ Service Nodes   │  │ Service Nodes   │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                  Hardware Abstraction Layer                 │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ LTS300 Drivers  │  │ PMCLib Drivers  │                  │
│  │ (Real/Sim/Mock) │  │ (Real/Mock)     │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                     Hardware Layer                          │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ Thorlabs LTS300 │  │ Planar Motor    │                  │
│  │ Linear Axes     │  │ System          │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

## Core Design Principles

### 1. **Modular Architecture**
- Each hardware component is a separate ROS2 package
- Clear interfaces between modules
- Easy to add/remove components

### 2. **Hardware Abstraction**
- Uniform interfaces for real and simulated hardware
- Automatic driver selection based on availability
- Seamless sim-to-real transfer

### 3. **ROS2 Native**
- Standard ROS2 services and topics
- Custom message/service definitions
- Integration with ROS2 ecosystem

### 4. **Safety by Design**
- Collision detection and avoidance
- Soft limits and emergency stops
- Continuous health monitoring

## Package Structure

```
promoc_assembly/
├── linear_axis_nodes/              # Linear positioning control
│   ├── drivers/                    # Hardware abstraction
│   │   ├── linear_axis_driver.py   # Base driver interface
│   │   ├── thorlabs_lts300_driver.py # Real hardware
│   │   ├── simulated_linear_axis_driver.py # Simulation
│   │   └── gazebo_linear_axis_driver.py # Gazebo integration
│   └── lts300_service_node.py      # ROS2 service node
├── planar_motor_nodes/             # 2D positioning control
│   ├── mover_service_node.py       # Main service node
│   ├── pmclib_loader.py           # Smart PMCLib loading
│   ├── mock_pmclib.py             # Mock implementation
│   ├── service_callbacks.py       # Service handling
│   └── position_utils.py          # Position management
├── promoc_assembly_interfaces/     # Custom ROS2 interfaces
│   ├── msg/                       # Message definitions
│   └── srv/                       # Service definitions
├── promoc_bringup/                # System integration
│   ├── launch/                    # Launch files
│   ├── config/                    # Configuration files
│   ├── urdf/                      # Robot descriptions
│   └── demo_controller.py         # Demo applications
└── setup/                         # Installation scripts
```

## Communication Architecture

### ROS2 Topics

```
/promoc_assembly/
├── x_axis/
│   ├── linear_axis_info           # Status updates
│   └── joint_states              # Position feedback
├── z_axis/
│   ├── linear_axis_info           # Status updates  
│   └── joint_states              # Position feedback
└── planar_motor/
    ├── mover_status              # Planar motor status
    └── position_feedback         # 2D position data
```

### ROS2 Services

```
/promoc_assembly/
├── x_axis/
│   ├── move_absolute             # Absolute positioning
│   ├── move_relative             # Relative movement
│   ├── get_position             # Position query
│   ├── home                     # Homing operation
│   └── shutdown                 # Safe shutdown
├── z_axis/
│   ├── move_absolute             # Absolute positioning
│   ├── move_relative             # Relative movement
│   ├── get_position             # Position query
│   ├── home                     # Homing operation
│   └── shutdown                 # Safe shutdown
└── planar_motor/
    ├── move_to_position         # 2D positioning
    ├── get_mover_status         # Status query
    └── emergency_stop           # Emergency halt
```

## Driver Architecture

### Linear Axis Drivers

```python
class LinearAxisDriver:
    """Base interface for all linear axis drivers"""
    
    def move_absolute(self, position: float, velocity: float) -> bool
    def move_relative(self, distance: float, velocity: float) -> bool
    def get_position(self) -> tuple[float, str]
    def home(self) -> bool
    def stop(self) -> bool
    def shutdown(self) -> bool
```

### Driver Selection Logic

1. **Hardware Detection**: Check for available hardware
2. **Driver Priority**: Real > Gazebo > Simulation > Mock
3. **Automatic Fallback**: Graceful degradation to simulation
4. **Runtime Switching**: Hot-swap between drivers (future)

## Configuration Management

### Hierarchical Configuration

1. **Default Parameters**: Built-in sensible defaults
2. **Package Configs**: Per-package configuration files
3. **Launch Parameters**: Runtime parameter overrides
4. **Environment Variables**: System-level settings

### Configuration Files

```yaml
# config/dual_lts300_controllers.yaml
controller_manager:
  ros__parameters:
    update_rate: 100
    joint_state_broadcaster:
      type: joint_state_broadcaster/JointStateBroadcaster
    lts300_x_position_controller:
      type: position_controllers/JointPositionController
    lts300_z_position_controller:
      type: position_controllers/JointPositionController
```

## Simulation Architecture

### URDF/Xacro Modularity

```
urdf/
├── properties/                    # Physical properties
│   ├── lts300_properties.xacro   # LTS300 specifications
│   └── materials.xacro           # Visual materials
├── modules/                      # Reusable components
│   ├── lts300_x_axis.urdf.xacro  # X-axis module
│   └── lts300_z_axis.urdf.xacro  # Z-axis module
└── assemblies/                   # Complete systems
    ├── dual_lts300_system.urdf.xacro # Full dual system
    └── test_single_axis.urdf.xacro   # Single axis test
```

### Simulation Stack

1. **Gazebo/Ignition**: Physics simulation
2. **ros2_control**: Control framework
3. **URDF/Xacro**: Robot description
4. **Joint Controllers**: Low-level control
5. **Hardware Interfaces**: Sim/real abstraction

## Security and Safety

### Safety Systems

- **Collision Detection**: Force/torque monitoring
- **Soft Limits**: Software position limits
- **Emergency Stop**: Immediate motion halt
- **Watchdog Timers**: Communication monitoring
- **Health Checks**: Continuous system validation

### Access Control

- **Service Permissions**: Role-based access (future)
- **Hardware Locking**: Exclusive access control
- **Audit Logging**: Operation tracking
- **Secure Communications**: Encrypted ROS2 (future)

## Extensibility

### Adding New Hardware

1. Implement driver interface
2. Create ROS2 service node  
3. Define custom messages/services
4. Add URDF description
5. Create launch files

### Adding New Capabilities

1. Define new service interfaces
2. Implement service callbacks
3. Add configuration parameters
4. Create documentation
5. Add tests

This architecture ensures the ProMOC Assembly system is robust, maintainable, and ready for future expansion.
