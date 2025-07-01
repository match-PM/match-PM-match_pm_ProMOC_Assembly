# Troubleshooting

## Häufige Probleme

### ROS2 nicht gefunden
- Lösung: `source /opt/ros/humble/setup.bash`

### Package nicht gefunden
- Lösung: `source install/setup.bash`

### Build-Fehler
- Lösung: `rm -rf build install log && cd setup && ./install_all.sh`

### Permissions
- Lösung: `chmod +x setup/*.sh`

### Dependencies
- Lösung: `cd setup && ./validate_setup_enhanced.sh`

## Weitere Hilfe
- Siehe VALIDATION_REPORT.md nach dem Ausführen des Validierungsskripts
- GitHub Issues für nicht lösbare Probleme
