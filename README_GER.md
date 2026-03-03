# ProMOC Assembly ROS2 System

Hardware-first ROS2-System fuer praezise Montage mit:
- Linearachsen (Thorlabs LTS300)
- Planarmotor-Steuerung
- Kamera-Services fuer Autofokus und MTF-Messung

## Offizieller Runtime-Pfad

Hardware ist der offizielle Release-Pfad.
Simulation ist fuer Lernen und Debugging verfuegbar.

Primaerer Einstieg:
- [`START_HERE.md`](START_HERE.md)

## Quick Start (Offizielle Hardware)

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

## Kernbefehle (Vereinheitlicht)

```bash
make doctor-hw   # Hardware-Readiness-Checks
make hw          # Komplettsystem im Hardware-Modus
make camera-hw   # Kamera-Stack im Hardware-Modus
make sim         # optionale/experimentelle Simulation
```

Kanonisches Launch-Argument:
- `runtime_mode:=hardware|sim`

## Dokumentation

- Architekturkarte: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Einstieg: [`START_HERE.md`](START_HERE.md)
- Lernpfad (DE): [`docs/learning_path_de.md`](docs/learning_path_de.md)
- Lernpfad (EN): [`docs/learning_path_en.md`](docs/learning_path_en.md)
- Migrationshinweise: [`MIGRATION_NOTES.md`](MIGRATION_NOTES.md)
- Setup-Skripte: [`setup/README.md`](setup/README.md)
- Bringup/Launch: [`promoc_bringup/README.md`](promoc_bringup/README.md)
- Kamera-Package: [`camera_nodes/README.md`](camera_nodes/README.md)
- Interfaces: [`promoc_assembly_interfaces/README.md`](promoc_assembly_interfaces/README.md)
