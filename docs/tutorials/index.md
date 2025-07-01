# Tutorials

## Schritt-für-Schritt-Anleitungen

### 1. Erste Simulation starten
- Installiere alle Abhängigkeiten (`./setup/install_all.sh`)
- Workspace sourcen (`source install/setup.bash`)
- Starte die Simulation (`ros2 launch promoc_bringup dual_lts300_gazebo.launch.py`)

### 2. Service-Calls testen
- Bewege die X-Achse:
```bash
ros2 service call /promoc_assembly/x_axis/move_absolute \
  promoc_assembly_interfaces/srv/linear_axis/MoveAbsolute \
  "{target_position: 0.05, velocity: 0.01}"
```
- Position abfragen:
```bash
ros2 service call /promoc_assembly/x_axis/get_position \
  promoc_assembly_interfaces/srv/linear_axis/GetPosition
```

### 3. Hardware-Integration
- Hardware anschließen und validieren (`./setup/validate_setup_enhanced.sh`)
- Launchfile für Hardwarebetrieb anpassen

### 4. Eigene Nodes entwickeln
- Siehe API- und Architektur-Doku
- Beispiel-Nodes im Quellcode

## Weitere Tutorials folgen!
