# camera_nodes

## Purpose

`camera_nodes` owns the current reduced camera runtime:

- raw image republishing
- camera status publication
- mock and hardware driver selection behind one node

The maintained runtime path does not currently wire autofocus or exposure
services into `camera_node`.

## Executable

- `ros2 run camera_nodes camera_node`

The usual startup path is through:

```bash
ros2 launch promoc_bringup camera.launch.py driver_mode:=mock
```

or the full system bringup.

## Configuration

Main config:

- `config/camera.yaml`

Important keys:

- `driver_mode`
- `source_image_topic`
- `image_topic`
- `status_topic`
- `publish_rate_hz`
- `frame_timeout_s`
- `status_publish_rate_hz`
- `mock.width`
- `mock.height`
- `mock.encoding`

Hardware camera profiles are selected through:

- `promoc_bringup/config/cameras/*.yaml`

## Primary Topics

- `/promoc/camera/image_raw`
- `/promoc/camera/status`

## Hardware And Mock Behavior

- `driver_mode:=mock`
  publishes a synthetic image stream and status without vendor drivers
- `driver_mode:=hardware`
  expects the hardware driver chain from `camera.launch.py`
- any other `driver_mode`
  is rejected instead of silently starting the wrong backend

Driver classes are imported directly from their modules:
`camera_nodes.drivers.mock` and `camera_nodes.drivers.hardware`. The
`drivers/__init__.py` file is only a package marker.

## Current Limitations

- the current reduced runtime does not expose autofocus or exposure services
- mock mode validates wiring, not optical behavior
- real hardware verification is not yet complete for this handover

## Related Docs

- [`../docs/START_HERE.md`](../docs/START_HERE.md)
- [`../docs/CONFIGURATION.md`](../docs/CONFIGURATION.md)
- [`../docs/INTERFACES.md`](../docs/INTERFACES.md)
- [`../docs/MOCK_MODE.md`](../docs/MOCK_MODE.md)
