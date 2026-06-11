# START_HERE

Primary onboarding page for the CS runtime branch.

## What This Branch Is

This branch is a specialized ROS2 runtime for the CS setup:

- camera with Four-Step autofocus and exposure control
- two Thorlabs linear axes
- planar motor mover control
- shared bringup wiring for the runtime stack
- room for additional runtime nodes without changing the overall structure

This branch is **not** the MTF measurement branch. If you are looking for
optical sharpness measurement, ROI-based edge selection, or MTF export flows,
that belongs elsewhere.
## Build Once

From the repository root:

```bash
make build
source install/setup.bash
```

If you installed the workspace from a parent ROS workspace, source the parent
workspace instead:
```bash
source ../install/setup.bash
```

## Start The System

Official hardware runtime:

```bash
ros2 launch promoc_bringup system.launch.py runtime_mode:=hardware
```

Secondary simulation path:

```bash
ros2 launch promoc_bringup system.launch.py runtime_mode:=sim
```

Convenience wrappers still exist:
```bash
make doctor-hw
make hw
make sim
```

Canonical launch argument:

- `runtime_mode:=hardware|sim`

## First Things To Try

Camera exposure:

```bash
ros2 service call /promoc/camera/set_exposure promoc_assembly_interfaces/srv/SetExposure \
"{exposure_time: 12000.0}"
```

## Choose Your Goal

| If you want to... | Open this first |
|---|---|
| change launch behavior or startup composition | [`../promoc_bringup/README.md`](../promoc_bringup/README.md) |
| change camera autofocus, exposure, or node wiring | [`../camera_nodes/README.md`](../camera_nodes/README.md) || change linear-axis motion behavior or axis services | [`../linear_axis_nodes/README.md`](../linear_axis_nodes/README.md) |
| change planar-motor mover behavior or motion services | [`../planar_motor_nodes/README.md`](../planar_motor_nodes/README.md) |
| add or change ROS messages or services | [`../promoc_assembly_interfaces/README.md`](../promoc_assembly_interfaces/README.md) |
| add shared validation, conversions, or reusable Python logic | [`../promoc_core/README.md`](../promoc_core/README.md) |

## Keep This Mental Model

- `promoc_bringup` starts the runtime
- runtime packages expose ROS services and topics
- `promoc_assembly_interfaces` defines the ROS contracts
- `promoc_core` contains shared helper code
- package READMEs explain the area you actually want to change
## Read Next

- docs map: [`README.md`](README.md)
- Package guide: [`PACKAGES.md`](PACKAGES.md)
- System overview: [`SYSTEM_OVERVIEW.md`](SYSTEM_OVERVIEW.md)
- package README for the area you want to change
