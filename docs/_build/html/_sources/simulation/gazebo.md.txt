# Simulation: Gazebo

## Gazebo-Integration
- Simulation der LTS300-Achsen und Planar Motor
- Launchfiles für Gazebo im Verzeichnis `launch/`

## Starten der Simulation
```bash
ros2 launch promoc_bringup dual_lts300_gazebo.launch.py
```

## Hinweise
- URDF/Xacro-Modelle werden automatisch geladen
- Controller-Konfigurationen in `config/`
