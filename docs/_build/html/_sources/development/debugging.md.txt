# Debugging

## Tipps
- ROS2-Logs nutzen: `ros2 run ... --ros-args --log-level debug`
- Python-Debugger: `import pdb; pdb.set_trace()`
- Launchfiles mit `--show-args` prüfen
- Gazebo-Logs bei Simulationsproblemen prüfen

## Häufige Fehlerquellen
- Nicht gesourcte Workspaces
- Fehlende Abhängigkeiten
- USB/Netzwerk-Probleme bei Hardware

## Tools
- `rqt_graph`, `rqt_console`, `rqt_logger_level`
- `ros2 topic echo`, `ros2 service call`
- `pytest`, `flake8`, `pep257`

## Hinweise
- Siehe Troubleshooting-Abschnitt in der Doku
