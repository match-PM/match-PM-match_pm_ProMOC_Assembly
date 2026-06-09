float64 axis_position      # Current position in mm
string axis_type          # 'x' or 'z'
string serial_number     # Device serial number
string operation_status  # Current operation: idle, homing, moving, jogging, error, emergency_stop
DeviceStatus device_status
uint8 AXIS_STATE_UNKNOWN=0
uint8 AXIS_UNHOMED=1
uint8 AXIS_HOMING=2
uint8 AXIS_HOMED=3
uint8 axis_state
