# ProMOC User Configuration

## Quick Start

1. Copy a template:
```bash
cd promoc_bringup/config
cp user_config.v2.example.yaml user_config.yaml
```

2. Edit values:
```bash
nano user_config.yaml
```

3. Use the system with your config:
```bash
ros2 launch promoc_bringup system.launch.py runtime_mode:=hardware
```

<<<<<<< HEAD
## Canonical v2 Keys

- `runtime.mode`: `hardware` or `sim`
- `measurement.operator`: operator or user name
- `measurement.base_path`: output base path
- `camera.pixel_size_um`
- `autofocus.*`
=======
## Canonical v2 Keys (Release N+1)

- `runtime.mode`: `hardware` or `sim`
- `measurement.operator`: operator/user name
- `measurement.base_path`: output base path
- `camera.pixel_size_um`
- `autofocus.*`
- `mtf.*`
>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
- `measurement_conditions.*`

## Note

`user_config.yaml` is git-ignored and remains local to each workstation.
