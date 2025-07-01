# 6DOF Motion Service Usage

## Overview
The 6DOF Motion Service allows precise control of XBot position and rotation in 6 degrees of freedom.

## Input Parameters
- **x_pos, y_pos, z_pos**: Position in millimeters
- **rx_pos, ry_pos, rz_pos**: Rotation in degrees
- **xbot_id**: Target XBot ID (use 0 for single XBot systems)

## Special Value for "No Change"
Use **-999999** to keep a parameter unchanged from its current value.

## Examples

### Example 1: Move to specific position with 0° rotation
```bash
ros2 service call /mover_node/six_d_mover_motion promoc_assembly_interfaces/srv/SixDofMotion "{
  xbot_id: 0,
  x_pos: 120.0,
  y_pos: 100.0,
  z_pos: 1.0,
  rx_pos: 0.0,
  ry_pos: 0.0,
  rz_pos: 0.0
}"
```

### Example 2: Keep current position, only rotate RZ to 45°
```bash
ros2 service call /mover_node/six_d_mover_motion promoc_assembly_interfaces/srv/SixDofMotion "{
  xbot_id: 0,
  x_pos: -999999,
  y_pos: -999999,
  z_pos: -999999,
  rx_pos: -999999,
  ry_pos: -999999,
  rz_pos: 45.0
}"
```

### Example 3: Return all rotations to 0° (keep position unchanged)
```bash
ros2 service call /mover_node/six_d_mover_motion promoc_assembly_interfaces/srv/SixDofMotion "{
  xbot_id: 0,
  x_pos: -999999,
  y_pos: -999999,
  z_pos: -999999,
  rx_pos: 0.0,
  ry_pos: 0.0,
  rz_pos: 0.0
}"
```

### Example 4: Move to position (200mm, 150mm) and set RX to 10°, keep others unchanged
```bash
ros2 service call /mover_node/six_d_mover_motion promoc_assembly_interfaces/srv/SixDofMotion "{
  xbot_id: 0,
  x_pos: 200.0,
  y_pos: 150.0,
  z_pos: -999999,
  rx_pos: 10.0,
  ry_pos: -999999,
  rz_pos: -999999
}"
```

## Important Notes
- All position values are in **millimeters**
- All rotation values are in **degrees**
- The system will automatically validate bounds and apply safety constraints
- Use XBot ID 0 for single-XBot systems
- The service will wait for motion completion and report success/failure
