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

## Messablauf Fuer Studierende

Der offizielle Standardablauf ist bewusst kurz:

1. In jedem neuen Terminal `source ~/.bashrc` ausfuehren.
2. Den Messstand mit dem Haupt-Launch starten.
3. In `rqt_image_view` das Livebild pruefen.
4. Bei Bedarf die Belichtung mit `set_exposure` nachziehen.
5. Autofokus im Standardmodus ausfuehren.
6. MTF zuerst immer mit `auto_roi=true` messen.
7. Nur wenn Auto-ROI kein sauberes Target findet: auf manuelle ROI wechseln.
8. Fuer die Auswertung zuerst `summary.csv`, danach bei Bedarf `context.csv`,
   `*_plot.png`, `*_roi.png`, `*_esf.csv`, `*_lsf.csv` und `*_mtf.csv`
   oeffnen.

## Architektur In Kurzform

Der MTF-Pfad bleibt absichtlich einfach:

```text
launch -> camera node -> MTF handler -> shared analyzer -> export folder
```

- `launch`: startet Kamera, Achse und den sichtbaren Messstand-Pfad
- `camera node`: stellt die ROS-Services fuer Autofokus, MTF und Belichtung bereit
- `MTF handler`: orchestriert Request, Capture-Validierung, ROI, Messung und Response
- `shared analyzer`: berechnet Winkel, ESF, LSF und MTF
- `export folder`: schreibt den Run-Ordner mit CSV, Plots und ROI-Artefakten

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

## Service Quick Start

Die studentische Standardnutzung arbeitet direkt ueber die drei sichtbaren
ROS-Services.

Belichtung bei Bedarf anpassen:

```bash
ros2 service call /promoc/camera/set_exposure \
  promoc_assembly_interfaces/srv/SetExposure \
  "{exposure_time: 12000.0}"
```

Autofokus im Standardmodus:

```bash
ros2 service call /promoc/camera/autofocus \
  promoc_assembly_interfaces/srv/AutoFocus \
  "{start_position: 0.0, end_position: 25.0, focus_mode: 0, skip_flyover: false, save_best_image: false}"
```

MTF im Standardpfad mit Auto-ROI:

```bash
ros2 service call /promoc/camera/measure_mtf \
  promoc_assembly_interfaces/srv/MeasureMTF \
  "{pixel_size_um: 0.0, auto_roi: true, target_edge: 'any'}"
```

MTF-Fallback mit manueller ROI:

```bash
ros2 service call /promoc/camera/measure_mtf \
  promoc_assembly_interfaces/srv/MeasureMTF \
  "{pixel_size_um: 0.0, auto_roi: false, target_edge: 'any'}"
```

## MTF Quick Start

- `Auto-ROI`: Quadrat-Target ins Bild bringen, `measure_mtf` ausloesen, die 4
  Kanten werden automatisch bewertet.
- `Manuelle ROI`: ROI direkt im Bild waehlen. Der Analyzer nutzt intern einen
  schmaleren Analyse-Streifen, damit die Winkeldetektion robuster bleibt.
- `Standardpfad`: Erst `auto_roi=true` verwenden. Nur wenn kein geeignetes
  Target gefunden wird oder die Zielkante unklar bleibt, auf manuelle ROI
  wechseln.
- `Ergebnisse`: Fuer jede Messung entsteht ein Run-Ordner mit `summary.csv`,
  `context.csv`, `selected_edge.txt` und pro Kante benannten
  `*_esf.csv`/`*_lsf.csv`/`*_mtf.csv`/`*_plot.png`/`*_roi.png`.
- Fuer den schnellen Vergleich immer zuerst `summary.csv` oeffnen.
- Fuer wissenschaftliche Vergleichsmessungen ist `context.csv` die kanonische
  Ein-Zeilen-Beschreibung der Messbedingung.
- `summary.csv` markiert pro Kante zusaetzlich, ob der gemessene Endwinkel in
  der offiziellen SOP-Arbeitszone `3 deg bis 10 deg` liegt.
- `context.csv` spiegelt dieselbe SOP-Wertung fuer genau die Kante, die auch
  an die ROS-Response zurueckgegeben wurde.

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

Der offizielle Bedienpfad fuer Studierende nutzt nur:

- `/promoc/camera/set_exposure`
- `/promoc/camera/autofocus` mit `focus_mode=0`
- `/promoc/camera/measure_mtf` zuerst mit `auto_roi=true`

Alle weiteren Modi und Debug-Pfade bleiben fuer Vergleichs- oder
Entwicklungszwecke erhalten, sind aber nicht Teil des Standardablaufs.

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

Entwickler- und Validator-Werkzeuge wie `mtf_synthetic_validation.py` bleiben
im Repo erhalten, sind aber **nicht** Teil des normalen studentischen
Messablaufs am Labor-PC.

Fuer offizielle Slanted-Edge-Vergleiche gilt dabei die empfohlene Arbeitszone
`3 deg bis 10 deg`. Der Node bleibt aus Kompatibilitaetsgruenden technisch bei
`2 deg bis 10 deg`, aber die Export-CSV trennt jetzt sauber zwischen
technischer Node-Validitaet und offizieller SOP-Akzeptanz auf Basis des
gemessenen Endwinkels.

## Entwicklung

Dieser Branch ist bewusst klein gehalten. Gepflegt werden nur die Pfade, die
fuer Messstand, Autofokus, MTF und Export wirklich gebraucht werden.
