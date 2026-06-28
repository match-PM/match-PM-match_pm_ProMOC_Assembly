# promoc_core

## Purpose

`promoc_core` holds small shared status/error helpers plus the optional system
controller. It should not become a generic dump for hardware-specific runtime
logic.

## Executable

- `ros2 run promoc_core promoc_system_controller`

This optional node is started only when shared system status or coordinated
stop/reset behavior is needed:

```bash
ros2 launch promoc_bringup system.launch.py driver_mode:=mock system_controller:=true
```

The default device-stack launch leaves it off.

## Configuration

- `config/system_controller.yaml`

Important keys:

- `required_devices`
- status topic names
- stop service names
- `planar_motor_xbot_id`
- `status_timeout_sec`
- `service_call_timeout_sec`
- `status_publication_rate_hz`

The system controller declares these ROS parameters directly in
`promoc_core/system_controller.py`. There is no separate parameter-defaults
registry.

## Primary Topic

- `/promoc/system/status`

## Primary Services

- `/promoc/system/stop_all`
- `/promoc/system/reset_stop`

Service response fields:

- `success`
- `error_code`
- `status_message`

## Current Limitations

- this is a software coordination layer, not certified functional safety
- it does not implement complete cross-device collision prevention
- it does not implement automatic safe parking

## Related Docs

- [`../docs/SYSTEM_OVERVIEW.md`](../docs/SYSTEM_OVERVIEW.md)
- [`../docs/INTERFACES.md`](../docs/INTERFACES.md)
- [`../docs/SAFETY.md`](../docs/SAFETY.md)
- [`ERROR_HANDLING.md`](ERROR_HANDLING.md)
- [`QUICK_REFERENCE.md`](QUICK_REFERENCE.md)
