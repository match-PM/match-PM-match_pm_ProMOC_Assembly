# Learning Path (EN, 30 Minutes)

## Goal
Run a full simulation workflow in 30 minutes and understand the core camera services.

## Step 1: Build (5 min)

```bash
colcon build --symlink-install
source install/setup.bash
```

## Step 2: Start simulation (5 min)

```bash
make sim
```

## Step 3: Run autofocus (10 min)

```bash
ros2 service call /promoc/camera/autofocus promoc_assembly_interfaces/srv/AutoFocus \
"{start_position: 260.0, end_position: 290.0, focus_mode: 0, skip_flyover: false}"
```

## Step 4: Run MTF measurement (10 min)

```bash
ros2 service call /promoc/camera/measure_mtf promoc_assembly_interfaces/srv/MeasureMTF \
"{auto_roi: true, target_edge: 'any'}"
```

## Step 5: Understand the module boundaries (5 min)

- Project structure map: [`docs/PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md)
- Architecture map: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
- Entry flow: [`START_HERE.md`](START_HERE.md)

## Next Step

- Switch to hardware: `make hw`
