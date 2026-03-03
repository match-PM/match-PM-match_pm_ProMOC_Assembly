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

## Canonical v2 Keys (Release N)

- `runtime.mode`: `hardware` or `sim`
- `measurement.operator`: operator/user name
- `measurement.base_path`: output base path
- `camera.pixel_size_um`
- `autofocus.*`
- `mtf.*`
- `measurement_conditions.*`

## Legacy Keys (Still accepted in Release N)

- `user.name`
- `user.measurement_base_path`
- `camera.mtf_csv_path` (deprecated and ignored; use `mtf.debug_export_dir`)

Legacy keys trigger deprecation warnings during launch/config load.

## Note

`user_config.yaml` is git-ignored and remains local to each workstation.
