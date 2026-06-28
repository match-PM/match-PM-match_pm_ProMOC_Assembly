# Safety

## Read This First

This repository contains software safety checks and software stop paths. It does
not provide certified functional safety.

## Local Device Safety

Current local device protections in the source include:

- connection and startup checks in the device nodes
- axis homing requirements before certain motion paths
- axis soft limits from the package config files
- motion-request validation
- busy-state rejection
- local stop services
- driver timeouts and driver error reporting

These protections are useful, but they are still software behavior inside the
device packages.

## System-Level Safety

The optional system controller adds a second layer when started with
`system_controller:=true`:

- monitors device status topics
- tracks stale or missing status
- exposes `/promoc/system/stop_all`
- latches a system stop state
- exposes a guarded `/promoc/system/reset_stop`

`reset_stop` is rejected if required device state is:

- missing
- stale
- busy
- in an error state
- not considered safe for reset

## Local Versus System-Wide Safety

Local safety answers:

- is this single device connected
- is this single motion command valid
- is this single device already busy

System-level safety answers:

- are all required devices currently reporting
- is the system in a latched stop state
- should stop requests be dispatched together
- should a reset be blocked

## Not Yet Implemented

The current repository does not yet provide:

- hardware-certified emergency stop
- complete cross-device collision prevention
- workspace-zone approval
- automatic safe parking
- gripper or pneumatics safety
- full real-hardware validation of every path

Do not describe the current implementation as SIL-, PL-, or certification-ready.
