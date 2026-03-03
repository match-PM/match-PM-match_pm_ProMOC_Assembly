# Lernpfad (DE, 30 Minuten)

## Ziel
In 30 Minuten einen kompletten Simulationslauf ausfuehren und die wichtigsten Kamera-Services verstehen.

## Schritt 1: Build (5 min)

```bash
colcon build --symlink-install
source install/setup.bash
```

## Schritt 2: Simulation starten (5 min)

```bash
make sim
```

## Schritt 3: Autofokus testen (10 min)

```bash
ros2 service call /promoc/camera/autofocus promoc_assembly_interfaces/srv/AutoFocus \
"{start_position: 260.0, end_position: 290.0, focus_mode: 0, skip_flyover: false}"
```

## Schritt 4: MTF testen (10 min)

```bash
ros2 service call /promoc/camera/measure_mtf promoc_assembly_interfaces/srv/MeasureMTF \
"{auto_roi: true, target_edge: 'any'}"
```

## Schritt 5: Modulgrenzen verstehen (5 min)

- Architekturkarte: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
- Einstiegsablauf: [`START_HERE.md`](../START_HERE.md)

## Naechster Schritt

- Wechsel zu Hardware: `make hw`
