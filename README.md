# ProMOC Messstand

Dieser Branch bildet den schlanken Messstand-Zuschnitt des Repos ab. Gepflegt
werden nur noch die real genutzten Hardware-Pfade fuer die IDS-Kamera, die
feste Thorlabs-X-Achse `lts300_x_axis`, die gemeinsamen ROS-Interfaces, das
verschlankte Bringup und ein kleines `promoc_core`.

Der Branch ist bewusst auf den bekannten Labor-PC zugeschnitten. Es gibt keine
gepflegte Simulationsschicht und kein Repo-internes Setup mehr.

## Ziel des Branches

- Kamera und Messachse fuer den Messstand betreiben
- stabile ROS-Schnittstellen unter `/promoc/...` erhalten
- so wenig allgemeine Infrastruktur wie moeglich mitziehen
- gemeinsame Hilfslogik in `promoc_core` klein und klar halten

Nicht mehr Teil dieses Branches:

- `setup/` und Repo-interne Installationsskripte
- simulierte Kamera- oder Achsenpfade
- planar-motor- bzw. mover-bezogene Laufzeitpakete
- verteilte Hauptdokumentation in `docs/`

## Paketuebersicht

| Paket | Aufgabe |
| --- | --- |
| `promoc_bringup` | kanonische Launch-Dateien und Parametrierung fuer den Messstand |
| `camera_nodes` | IDS-Kamera-Node mit Autofokus, MTF, ROI und Exposure-Service |
| `linear_axis_nodes` | Anbindung der Thorlabs-LTS300-Achse |
| `promoc_assembly_interfaces` | ROS2-Services und Messages |
| `promoc_core` | kleine gemeinsame Python-Helfer fuer Logging, Exceptions, Error Handling und Validation |

## Schnellstart

Voraussetzung ist ein bereits eingerichteter Labor-PC mit den benoetigten
Systemabhaengigkeiten und verfuegbarer Hardware.

Build aus dem Repo-Root:

```bash
colcon build --symlink-install
source install/setup.bash
```

Kamera-Stack starten:

```bash
ros2 launch promoc_bringup camera.launch.py runtime_mode:=hardware
```

Live-Bild in einem zweiten Terminal mit `rqt_image_view` oeffnen:

```bash
source install/setup.bash
ros2 run rqt_image_view rqt_image_view
```

Im `rqt_image_view` dann den Topic
`/promoc/assembly_camera/stream0/image_raw` auswaehlen.

Gesamten Messstand starten:

```bash
ros2 launch promoc_bringup system.launch.py runtime_mode:=hardware
```

Der Launch-Parameter `runtime_mode` bleibt aus Kompatibilitaetsgruenden sichtbar,
unterstuetzt aber nur noch `hardware`. Andere Werte werden intern auf
`hardware` zurueckgefuehrt.

## Architektur

Der Messstand besteht zur Laufzeit aus genau zwei aktiven Runtime-Bausteinen:

1. `camera_nodes` fuer die reale IDS-Kamera
2. `linear_axis_nodes` fuer die feste X-Achse `lts300_x_axis`

`promoc_bringup/launch/system.launch.py` ist der kanonische Startpfad fuer
beide Komponenten zusammen. `promoc_bringup/launch/camera.launch.py` startet
nur den Kamera-Stack. `promoc_bringup/launch/optical_measurement_system.launch.py`
ist ein auf denselben Hardware-Only-Zuschnitt reduzierter Spezial-Wrapper.

In `camera_nodes` gibt es keine Simulation mehr:

- kein `use_simulator`
- kein `camera_simulator`
- keine variable Achsenverdrahtung

Die Kamera ist fest mit dem Achsenpfad
`/promoc/linear_axis/lts300_x_axis/...` verdrahtet.

## Konfiguration

Variabel bleibt nur noch die konkrete IDS-Kamerakonfiguration. Diese wird ueber
`camera_type` ausgewaehlt und aus `promoc_bringup/config/cameras/` geladen.

Wichtige Konfigurationsdateien:

- `promoc_bringup/config/user_config.v2.example.yaml`
- `promoc_bringup/config/cameras/ids_u3_3800cp_hq.yaml`
- `promoc_bringup/config/linear_axes_params.yaml`

Typischer Kamera-Start mit explizitem Profil:

```bash
ros2 launch promoc_bringup camera.launch.py runtime_mode:=hardware camera_type:=ids_u3_3800cp_hq
```

## ROS-Namespaces und Services

Stabil gehaltene Kamera-Services:

- `/promoc/camera/autofocus`
- `/promoc/camera/autofocus_comparison`
- `/promoc/camera/measure_mtf`
- `/promoc/camera/detect_rois`
- `/promoc/camera/select_roi`
- `/promoc/camera/set_exposure`

Wichtige Punkte dazu:

- `focus_mode=0` bedeutet im Messstand-Branch standardmaessig `FourStep`
- `/promoc/camera/set_exposure` ist der einzige gepflegte manuelle
  Exposure-Endpunkt
- die Kamera-Namespace-Struktur unter `/promoc/camera/*` bleibt stabil

Stabil gehaltener Achsen-Namespace:

- `/promoc/linear_axis/lts300_x_axis/*`

Beispiele:

```bash
ros2 service call /promoc/camera/set_exposure promoc_assembly_interfaces/srv/SetExposure "{exposure_time: 12000.0}"
ros2 service call /promoc/linear_axis/lts300_x_axis/get_position promoc_assembly_interfaces/srv/GetPosition "{}"
```

## `promoc_core`

`promoc_core` bleibt absichtlich klein. In diesem Branch gelten nur diese
Module als unterstuetzte gemeinsame Python-Oberflaeche:

- `promoc_core.logging`
- `promoc_core.promoc_exceptions`
- `promoc_core.error_handling`
- `promoc_core.validation`

Nicht mehr gepflegt und nicht mehr Bestandteil des Branch-Vertrags:

- `promoc_core.motion`
- `promoc_core.motion_interface`
- `promoc_core.conversions`

## Entwicklung und Checks

Nuetzliche Kommandos aus dem Repo-Root:

```bash
colcon build --symlink-install
colcon test --packages-select camera_nodes linear_axis_nodes promoc_core promoc_assembly_interfaces promoc_bringup
colcon test-result --all
python3 promoc_bringup/scripts/release_n_check.py
python3 promoc_bringup/scripts/release_n_smoke.py --mode hardware
```

Paket-Build fuer den Messstand-Zuschnitt:

```bash
colcon build --symlink-install --packages-select \
  camera_nodes \
  linear_axis_nodes \
  promoc_core \
  promoc_assembly_interfaces \
  promoc_bringup
```

Launch-Sanity-Checks:

```bash
ros2 launch promoc_bringup camera.launch.py runtime_mode:=hardware --show-args
ros2 launch promoc_bringup system.launch.py runtime_mode:=hardware --show-args
```

## Dokumentationsregel

Diese Datei ist die einzige gepflegte inhaltliche Gesamtdokumentation des
Messstand-Branches. Paket-READMEs duerfen als kurze Wegweiser bestehen bleiben,
tragen aber keine eigene inhaltliche Hauptdokumentation mehr.
