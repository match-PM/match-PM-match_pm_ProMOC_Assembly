# ProMOC Messstand

Dieser Branch bildet den schlanken Messstand-Zuschnitt des Repos ab. Gepflegt
werden nur noch die real genutzten Hardware-Pfade fuer die IDS-Kamera, die
feste Thorlabs-X-Achse `lts300_x_axis`, die gemeinsamen ROS-Interfaces, das
verschlankte Bringup und ein kleines `promoc_core`.

Der Branch ist bewusst auf den bekannten Labor-PC zugeschnitten. Es gibt keine
gepflegte Simulationsschicht und kein Repo-internes Setup mehr.

## Leitdokumente

- `README.md`: Start, Bedienung und die alltaeglichen Standardbefehle
- [`MTF_PROTOCOL.md`](MTF_PROTOCOL.md): wissenschaftliches Messprotokoll,
  Datenfluss und CSV-Vertrag fuer Vergleichsmessungen

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

## Messstand Starten

In jedem neuen Terminal zuerst:

```bash
source ~/.bashrc
```

Standardablauf am Messstand:

```bash
# Terminal 1: kompletter optischer Messstand
ros2 launch promoc_bringup optical_measurement_system.launch.py

# Terminal 2: ROS-Werkzeuge / Service-Aufrufe
rqt

# Terminal 3: Live-Kamerabild
rqt_image_view
```

Im `rqt_image_view` den Topic `/promoc/assembly_camera/stream0/image_raw`
waehlen.

## MTF Quick Start

- `Auto-ROI`: Quadrat-Target ins Bild bringen, `measure_mtf` ausloesen, die 4
  Kanten werden automatisch bewertet.
- `Manuelle ROI`: ROI direkt im Bild waehlen. Der Analyzer nutzt intern einen
  schmaleren Analyse-Streifen, damit die Winkeldetektion robuster bleibt.
- `Ergebnisse`: Fuer jede Messung entsteht ein Run-Ordner mit `summary.csv`,
  `context.csv`, `selected_edge.txt` und pro Kante benannten
  `*_esf.csv`/`*_lsf.csv`/`*_mtf.csv`/`*_plot.png`/`*_roi.png`.
- Fuer den schnellen Vergleich immer zuerst `summary.csv` oeffnen.
- Fuer wissenschaftliche Vergleichsmessungen ist `context.csv` die kanonische
  Ein-Zeilen-Beschreibung der Messbedingung.

## Benutzerkonfiguration

Die persoenliche Messstand-Konfiguration kommt aus:

```bash
cp promoc_bringup/config/user_config.v2.example.yaml promoc_bringup/config/user_config.yaml
```

Wichtige Felder in `promoc_bringup/config/user_config.yaml`:

- `measurement.operator`: Name fuer Exportordner und Messprotokolle
- `measurement.base_path`: Basisordner fuer alle Messungen

Beispiel:

```yaml
measurement:
  operator: MaxMustermann
  base_path: ~/Dokumente/Messungen
```

MTF-Exporte landen dann unter einem Pfad wie:

```text
~/Dokumente/Messungen/MaxMustermann/mtf_messungen/<run_id>/
```

## Build

Aus dem Repo-Root:

```bash
colcon build --symlink-install --packages-select \
  camera_nodes \
  linear_axis_nodes \
  promoc_core \
  promoc_assembly_interfaces \
  promoc_bringup
source install/setup.bash
```

## Laufzeitbild

Der Messstand hat genau zwei aktive Runtime-Bausteine:

1. `camera_nodes` fuer Kamera, Autofokus, MTF und Export
2. `linear_axis_nodes` fuer die feste Thorlabs-X-Achse `lts300_x_axis`

Es gibt genau einen gepflegten Hauptstart:

```bash
ros2 launch promoc_bringup optical_measurement_system.launch.py
```

## Services

Die oeffentliche Kamera-API des Messstand-Branches besteht nur aus:

- `/promoc/camera/autofocus`
- `/promoc/camera/measure_mtf`
- `/promoc/camera/set_exposure`

Der Achsenpfad bleibt unter:

- `/promoc/linear_axis/lts300_x_axis/*`

Beispiel:

```bash
ros2 service call /promoc/camera/set_exposure promoc_assembly_interfaces/srv/SetExposure "{exposure_time: 12000.0}"
ros2 service call /promoc/linear_axis/lts300_x_axis/get_position promoc_assembly_interfaces/srv/GetPosition "{}"
```

## Wissenschaftliche MTF

`/promoc/camera/measure_mtf` schaltet fuer die Messung in einen eigenen
wissenschaftlichen Raw-Capture-Modus:

- `PixelFormat=BayerRG12`
- `1x1`-Binning
- Auto-Exposure, Auto-Gain und Auto-Whitebalance aus
- Gamma und Farbtransformation aus
- Auswertung nur aus den echten Gruen-Senseln des `RGGB`-Musters

Die ESF wird direkt aus den realen Gruen-Sample-Koordinaten aufgebaut. Es gibt
kein Debayering und kein 2D-Auffuellen fehlender Bayer-Pixel.

Vergleich mehrerer Bedingungen passiert bewusst **ausserhalb von ROS** ueber
`context.csv` und `summary.csv`. Das offizielle Messprotokoll, die SOP fuer
Beam-Splitter-Vergleiche und die Bedeutung der CSV-Spalten stehen in
[`MTF_PROTOCOL.md`](MTF_PROTOCOL.md).

Fuer offizielle Slanted-Edge-Vergleiche gilt dabei die empfohlene Arbeitszone
`3° bis 10°`. Der Node bleibt aus Kompatibilitaetsgruenden technisch bei
`2° bis 10°`, der Standalone-Validator bewertet aber nur `3° bis 10°` als
offiziell akzeptiert.

## Entwicklung

Dieser Branch ist bewusst klein gehalten. Gepflegt werden nur die Pfade, die
fuer Messstand, Autofokus, MTF und Export wirklich gebraucht werden.
