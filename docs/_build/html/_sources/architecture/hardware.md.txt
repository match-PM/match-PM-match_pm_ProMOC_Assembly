# Hardware Architecture

## Supported Hardware

- **Thorlabs LTS300**: Linear precision axes (X/Z)
- **Planar Motor**: 2D positioning system (PMCLib-compatible)
- **Sensors**: Endstops, encoders, safety switches
- **Safety Systems**: Collision detection, emergency stop

## Hardware Abstraction

- Treiber-Layer für Simulation und reale Hardware
- Austauschbare Treiber für verschiedene Achsentypen
- Mock- und Simulations-Treiber für Entwicklung

## Verkabelung und Aufbau

- USB-Verbindung für LTS300
- Ethernet für Planar Motor
- Standardisierte Stecker für Sensorik

## Hinweise

- Details zur Inbetriebnahme siehe Installationsanleitung
- Hardware-Validierung über das Validierungsskript
