# promoc_core

## Purpose

`promoc_core` holds shared helpers and the system controller. It should not
become a generic dump for hardware-specific runtime logic.

## Executable

- `ros2 run promoc_core promoc_system_controller`

This node is normally started by:

```bash
ros2 launch promoc_bringup system.launch.py driver_mode:=mock
```

or hardware mode.

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
