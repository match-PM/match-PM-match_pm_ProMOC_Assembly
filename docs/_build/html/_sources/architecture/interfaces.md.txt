# Interfaces

## ROS2 Nachrichten und Services

### Linear Axis Interfaces
- `MoveAbsolute` (Service): Absolutpositionierung
- `GetPosition` (Service): Abfrage der aktuellen Position
- `Home` (Service): Referenzfahrt
- `LinearAxisInfo` (Message): Statusinformationen

### Planar Motor Interfaces
- `MoveTo` (Service): 2D-Positionierung
- `GetPosition` (Service): Abfrage der aktuellen 2D-Position
- `Home` (Service): Referenzfahrt
- `PlanarMotorInfo` (Message): Statusinformationen

## Custom Messages
- Definiert in `promoc_assembly_interfaces/msg/` und `promoc_assembly_interfaces/srv/`

## Hinweise
- Details siehe API-Referenz und Quellcode
