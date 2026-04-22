# START_HERE

<<<<<<< HEAD
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
=======
Primary onboarding entry for new contributors and ROS2 beginners.

## What This Repository Is

ProMOC Assembly is a hardware-first ROS2 repository for:

- camera autofocus and MTF measurement
- Thorlabs LTS300 linear axes
- planar motor mover control
- shared launch/config wiring for the full assembly stack

If you are new to the repo, read this file once from top to bottom, then open the package guide for the first change you want to make.

## How To Think About This Repo

Use this simple mental model:

- `promoc_bringup` starts the system
- runtime packages expose ROS services and topics
- `promoc_assembly_interfaces` defines the ROS contracts
- `promoc_core` contains shared helper code
- package READMEs explain the area you actually want to change
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0

## Build Once

From the repository root:

```bash
make build
source install/setup.bash
```

<<<<<<< HEAD
If you installed the workspace from a parent ROS workspace, source the parent
workspace instead:
=======
If you ran [`../setup/install_all.sh`](../setup/install_all.sh) from a workspace checkout like `<ws>/src/promoc_assembly`, source the parent workspace instead:
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0

```bash
source ../install/setup.bash
```

## Start The System

<<<<<<< HEAD
Official hardware runtime:

```bash
ros2 launch promoc_bringup system.launch.py runtime_mode:=hardware
```

Secondary simulation path:

```bash
ros2 launch promoc_bringup system.launch.py runtime_mode:=sim
```

Convenience wrappers still exist:
=======
Official release path:
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0

```bash
make doctor-hw
make hw
<<<<<<< HEAD
=======
```

Camera-only hardware start:

```bash
make camera-hw
```

Simulation or learning path:

```bash
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
make sim
```

Canonical launch argument:

- `runtime_mode:=hardware|sim`

## First Things To Try

<<<<<<< HEAD
Camera exposure:

```bash
ros2 service call /promoc/camera/set_exposure promoc_assembly_interfaces/srv/SetExposure \
"{exposure_time: 12000.0}"
```

=======
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
Camera autofocus:

```bash
ros2 service call /promoc/camera/autofocus promoc_assembly_interfaces/srv/AutoFocus \
"{start_position: 260.0, end_position: 290.0, focus_mode: 0, skip_flyover: false}"
```

<<<<<<< HEAD
The public `focus_mode` field is still present for transition compatibility, but
the maintained runtime path is Four-Step autofocus.
=======
MTF measurement:

```bash
ros2 service call /promoc/camera/measure_mtf promoc_assembly_interfaces/srv/MeasureMTF \
"{auto_roi: true, target_edge: 'any'}"
```

Exposure update:

```bash
ros2 service call /promoc/camera/set_exposure promoc_assembly_interfaces/srv/SetExposure \
"{exposure_time: 12000.0}"
```
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0

## Choose Your Goal

| If you want to... | Open this first |
|---|---|
| change launch behavior or startup composition | [`../promoc_bringup/README.md`](../promoc_bringup/README.md) |
<<<<<<< HEAD
| change camera autofocus, exposure, or node wiring | [`../camera_nodes/README.md`](../camera_nodes/README.md) |
=======
| change camera behavior, autofocus, MTF, or camera service wiring | [`../camera_nodes/README.md`](../camera_nodes/README.md) |
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
| change linear-axis motion behavior or axis services | [`../linear_axis_nodes/README.md`](../linear_axis_nodes/README.md) |
| change planar-motor mover behavior or motion services | [`../planar_motor_nodes/README.md`](../planar_motor_nodes/README.md) |
| add or change ROS messages or services | [`../promoc_assembly_interfaces/README.md`](../promoc_assembly_interfaces/README.md) |
| add shared validation, conversions, or reusable Python logic | [`../promoc_core/README.md`](../promoc_core/README.md) |

<<<<<<< HEAD
## Keep This Mental Model

- `promoc_bringup` starts the runtime
- runtime packages expose ROS services and topics
- `promoc_assembly_interfaces` defines the ROS contracts
- `promoc_core` contains shared helper code
- package READMEs explain the area you actually want to change
=======
## What You Need To Know

- `promoc_bringup`: launch files, runtime mode, config wiring
- `camera_nodes`: camera node and camera-facing services
- `linear_axis_nodes`: LTS300 axis node and axis services
- `planar_motor_nodes`: planar motor mover node and motion services
- `promoc_assembly_interfaces`: contract-only ROS `srv` and `msg`
- `promoc_core`: shared Python helpers that must stay independent from runtime packages
- `docs`: central onboarding and architecture only
- `setup`: installation and environment checks
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0

## Read Next

- docs map: [`README.md`](README.md)
- Package guide: [`PACKAGES.md`](PACKAGES.md)
- System overview: [`SYSTEM_OVERVIEW.md`](SYSTEM_OVERVIEW.md)
- package README for the area you want to change
<<<<<<< HEAD
=======

## Ground Rules

Keep these stable while working in the repo:

- documented service namespaces stay under `/promoc/...`
- runtime node packages use the canonical `node.py` entry module
- `promoc_assembly_interfaces` stays contract-only
- `promoc_core` stays independent from runtime packages
- business logic belongs in nodes, services, drivers, domain, or adapters, not in launch files
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
