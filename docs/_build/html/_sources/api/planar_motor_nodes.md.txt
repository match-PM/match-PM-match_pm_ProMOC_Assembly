# Planar Motor Nodes API

## Hauptmodul: `planar_motor_nodes`

### Wichtige Komponenten
- `mover_service_node.py`: Haupt-Service-Node für Planar Motor
- `pmclib_loader.py`: Dynamisches Laden der PMCLib
- `mock_pmclib.py`: Mock-Implementierung für Simulation
- `service_callbacks.py`: Service-Handler
- `position_utils.py`: Hilfsfunktionen für Koordinaten

### Services
- `MoveTo`: 2D-Positionierung
- `GetPosition`: Aktuelle Position abfragen
- `Home`: Referenzfahrt

### Beispiel-Serviceaufruf
```bash
ros2 service call /promoc_assembly/planar_motor/move_to \
  promoc_assembly_interfaces/srv/planar_motor/MoveTo \
  "{target_x: 0.1, target_y: 0.2, velocity: 0.01}"
```

### Hinweise
- Für Hardwarebetrieb muss PMCLib installiert sein
- Im Simulationsmodus wird `mock_pmclib.py` verwendet
