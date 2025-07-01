# Testing

## Testarten
- Unit-Tests für Hilfsfunktionen
- Integrationstests für Nodes und Services
- Systemtests (Simulation und Hardware)

## Testausführung

```bash
colcon test
colcon test --packages-select linear_axis_nodes
pytest test/
```

## Automatisierte Validierung

```bash
cd setup/
./validate_setup_enhanced.sh
```

## Hinweise
- Testbeispiele im `test/`-Verzeichnis
- Neue Features immer mit Tests abdecken
