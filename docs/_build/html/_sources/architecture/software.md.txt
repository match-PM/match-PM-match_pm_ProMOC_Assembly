# Software Architecture

## Modularer Aufbau

- **ROS2 Nodes**: Jeder Achsentyp als eigener Node
- **Service Layer**: ROS2-Services für Bewegungsbefehle, Status, Homing
- **Abstraktionsschicht**: Trennung von Hardware und Logik
- **Simulation**: Austauschbare Treiber für Sim/Real/Mock

## Hauptkomponenten

- `linear_axis_nodes`: Steuerung der LTS300-Achsen
- `planar_motor_nodes`: Steuerung des Planar Motors
- `promoc_assembly_interfaces`: Custom ROS2 Nachrichten/Services
- `promoc_bringup`: Launchfiles, URDF, Konfiguration

## Erweiterbarkeit

- Neue Hardware kann durch Implementierung eines Treibers integriert werden
- Zusätzliche Services und Nachrichten können einfach ergänzt werden

## Hinweise

- Siehe API-Referenz für Details zu Nodes und Services
