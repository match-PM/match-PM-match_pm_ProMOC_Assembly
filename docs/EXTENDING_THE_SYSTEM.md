# Extending The System

## Keep Package Boundaries Clean

When you add new functionality, keep it in the package that owns that concern.

Good placement rules:

- hardware-driver logic stays in the device package
- launch composition stays in `promoc_bringup`
- shared helpers stay in `promoc_core`
- message and service contracts stay in `promoc_assembly_interfaces`

## Where New Features Should Go

Future functionality should be added like this:

- gripper or pneumatics
  new dedicated device package
- part detection and pose estimation
  separate vision nodes
- assembly sequencing
  process or client nodes above the hardware packages
- workspace zones and movement approval
  `promoc_core` system-level safety layer
- Gazebo or richer simulation
  `promoc_simulation`

## What Not To Do

Avoid these shortcuts:

- do not add process logic to hardware nodes
- do not hide behavior inside launch files
- do not put hardware-specific logic into `promoc_core`
- do not casually rename public topics or services
- do not treat mock-only behavior as proof of real-hardware safety
