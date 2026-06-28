# Handover Status

## Verified

- ROS 2 Jazzy workspace build
- ROS 2 Jazzy workspace tests
- ROS 2 Humble workspace build
- ROS 2 Humble workspace tests
- `python3 tools/check_project.py --quick`
- `python3 tools/check_project.py --full`
- `python3 tools/check_project.py --full --artifact-root <artifact-dir>`
- mock camera
- mock X axis
- mock Z axis
- mock planar motor
- full mock bringup
- partial mock bringup
- system status publication
- `stop_all`
- guarded `reset_stop`

## Not Yet Verified On The Authoritative Target Platform

- real IDS camera on the current simplified runtime
- real Thorlabs axes on the current simplified runtime
- linear-axis serial-number USB scan on the real X/Z hardware pair
- real planar motor on the current simplified runtime
- planar-motor hardware PMCLib connection on a real controller
- planar-motor hardware activation sequence with real XBots
- planar-motor hardware Z-acceleration behavior beyond current PMCLib call
  coverage
- complete mechanical collision safety
- gripper and pneumatics
- controlled parking

## Interpretation

The authoritative target platform is Ubuntu 22.04, ROS 2 Humble, and Python
3.10. The currently recorded verification evidence in this repository includes
successful Humble and Jazzy workspace build/test execution, plus source-level
and mock runtime checks. The full check now also supports an external artifact
root, so the Humble validation can run with a read-only source checkout and
persisted build artifacts outside the repository. This still does not certify
real machine behavior.

Planar-motor PMCLib remains local-only under
`planar_motor_nodes/planar_motor_nodes/drivers/vendor/pmclib/` and is required
only for hardware mode.

Linear-axis hardware mode uses `pylablib`. With the normal config, `serial_port`
is empty and the driver selects the physical X/Z axis by the configured
Thorlabs serial number after scanning `/dev/ttyUSB*` and `/dev/ttyACM*`.

Hardware planar-motor startup defaults to `auto_activate` true, matching the
legacy main-branch startup flow after the explicit PMC connection succeeds. Set
it false when activation should be requested explicitly after status is checked.
