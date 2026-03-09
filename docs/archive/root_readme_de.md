# Archivierte Root-README (DE)

Diese Datei war frueher eine Root-README. Die kanonische Root-Dokumentation ist jetzt [`../../README.md`](../../README.md).

Hardware-first ROS2-Repository fuer praezise Montage mit Kamera-Services, Linearachsen, Planarmotor-Steuerung und gemeinsamer Bringup-Verkabelung.

## Einstieg

Wenn du neu im Repository bist, lies zuerst [`../START_HERE.md`](../START_HERE.md) und nutze danach [`../PROJECT_STRUCTURE.md`](../PROJECT_STRUCTURE.md), um das richtige Package und die erste Datei zu finden.

## Offizieller Runtime-Pfad

- Hardware ist der offizielle Release-Pfad
- Simulation dient dem Lernen, Debugging und isolierten Entwickeln
- kanonisches Launch-Argument: `runtime_mode:=hardware|sim`

## Schnellstart

```bash
cd ~/ros2_ws/src
git clone <repository-url> promoc_assembly
cd promoc_assembly/setup
./install_all.sh
cd ..
source install/setup.bash
make doctor-hw
make hw
```

## Kernbefehle

```bash
make doctor-hw
make hw
make camera-hw
make sim
```

## Package-Ueberblick

- `promoc_bringup`: Launch-Files und Runtime-Wiring
- `camera_nodes`: Autofokus-, MTF-, Exposure- und ROI-Services
- `linear_axis_nodes`: LTS300-Bewegung und Status
- `planar_motor_nodes`: Mover-Bewegungs- und Kontroll-Services
- `promoc_assembly_interfaces`: nur ROS-Vertraege
- `promoc_core`: gemeinsam nutzbare Python-Logik

## Wichtige Doku

- Einstieg: [`../START_HERE.md`](../START_HERE.md)
- Strukturkarte: [`../PROJECT_STRUCTURE.md`](../PROJECT_STRUCTURE.md)
- Architektur: [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
- Setup: [`../../setup/README.md`](../../setup/README.md)
- Migrationshinweise: [`../MIGRATION_NOTES.md`](../MIGRATION_NOTES.md)
