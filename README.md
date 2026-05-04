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
- synthetische MTF-Validation-Demos und Standalone-Validatoren
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
6. MTF zuerst immer ueber `measure_mtf` mit `measurement_mode='auto'` messen.
7. Wenn der Auto-Pfad kein sauberes Target findet: `measure_mtf` mit
   `measurement_mode='roi_search'` verwenden.
8. Nur wenn auch die ROI-Suche nicht passt: `measure_mtf` im direkten
   manuellen Modus verwenden.
9. Fuer die Auswertung zuerst `summary.csv`, danach bei Bedarf `context.csv`,
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

Im `rqt_image_view` den Topic `/promoc/promoc_camera/stream0/image_raw`
waehlen.

## Raw-First Preflight

Vor der ersten Messung am Tag einmal kurz pruefen:

1. Topic liefert `bayer_rggb16`.
2. Bei Vollsensor passt `step = 11072`.
3. Das Livebild ist in `rqt_image_view` sichtbar.
4. Ein kurzer Autofokus-Lauf funktioniert.
5. Je eine kurze Auto-ROI- und manuelle ROI-MTF-Messung erzeugt einen
   vollstaendigen Run-Ordner.

Beispiel fuer den schnellen Topic-Check:

```bash
ros2 topic echo /promoc/assembly_camera/stream0/image_raw --once
```

Wenn `BayerRG12` am realen Stand nicht stabil laeuft, ist die definierte
Fallback-Reihenfolge:

1. `BayerRG8`
2. erst danach `RGB8` als klar markierter Debug-/Notfallmodus

## Service Quick Start

Die studentische Standardnutzung arbeitet direkt ueber die drei sichtbaren
ROS-Services.

Belichtung bei Bedarf anpassen:

```bash
ros2 service call /promoc/camera/set_exposure \
  promoc_assembly_interfaces/srv/SetExposure \
  "{exposure_time: 12000.0}"
```

`exposure_time` ist in `µs`. Beispiel: `30000.0` bedeutet `30.0 ms`.
Werte ausserhalb der Kameragrenzen werden auf den naechsten gueltigen
Bereichswert geklemmt und im Service-Status klar rueckgemeldet.

Der Service schreibt die Belichtung live ueber den laufenden
`camera_aravis2`-Parameterpfad. Wenn der Wunschwert nicht sauber
uebernommen wird, faellt der Messstand sichtbar auf die beim Launch aus
dem Kamera-Profil geladene Start-Belichtung zurueck.

Autofokus im Standardmodus:

```bash
ros2 service call /promoc/camera/autofocus \
  promoc_assembly_interfaces/srv/AutoFocus \
  "{start_position: 0.0, end_position: 25.0, focus_mode: 0, skip_flyover: false, save_best_image: false}"
```

MTF im Standardpfad ueber den kanonischen Service:

```bash
ros2 service call /promoc/camera/measure_mtf \
  promoc_assembly_interfaces/srv/MeasureMTF \
  "{measurement_mode: 'auto', target_edge: 'any'}"
```

MTF-Fallback mit lokaler ROI-Suche nach einer vollstaendigen Quadratkante:

```bash
ros2 service call /promoc/camera/measure_mtf \
  promoc_assembly_interfaces/srv/MeasureMTF \
  "{measurement_mode: 'roi_search', target_edge: 'any'}"
```

MTF-Fallback mit direkter manueller ROI:

```bash
ros2 service call /promoc/camera/measure_mtf \
  promoc_assembly_interfaces/srv/MeasureMTF \
  "{measurement_mode: 'direct_manual', target_edge: 'any'}"
```

Schneller Aufnahme-Pfad ohne direkte MTF-Berechnung:

```bash
ros2 service call /promoc/camera/measure_mtf \
  promoc_assembly_interfaces/srv/MeasureMTF \
  "{measurement_mode: 'capture_only', target_edge: 'any', roi_x: 0, roi_y: 0, roi_width: 0, roi_height: 0}"
```

Noch schneller, wenn die Kanten-ROI schon bekannt ist und keine Quadrat-Suche
mehr laufen soll:

```bash
ros2 service call /promoc/camera/measure_mtf \
  promoc_assembly_interfaces/srv/MeasureMTF \
  "{measurement_mode: 'capture_only_direct', target_edge: 'any', roi_x: 120, roi_y: 240, roi_width: 220, roi_height: 120}"
```

Die spaetere Auswertung eines Capture-Ordners laeuft ohne Kamera:

```bash
ros2 run camera_nodes mtf_batch_analyze \
  --input ~/Dokumente/Messungen/MaxMustermann/mtf_messungen \
  --recursive --overwrite \
  --target-edge top --min-valid-edges 1
```

`--target-edge` ist optional (`top`, `right`, `bottom`, `left`) und waehlt die
gewollte Kante, wenn sie gueltige Samples hat. `--min-valid-edges 1` erlaubt
Teilresultate; die MTF-Werte werden pro Kante ueber alle gueltigen Samples im
Raw-Stack gemittelt. Die technische Analyzer-Winkelgrenze liegt bei `11°`,
waehrend die offizielle SOP-Bewertung weiter `3°...10°` verwendet. Zusaetzlich
entsteht eine `batch_summary.csv`. Nach der Offline-Auswertung werden die
`*_roi.png` als vergroesserte Review-Bilder aus dem Raw-Stack neu geschrieben;
der sichtbare Rahmen zeigt den tatsaechlich analysierten Streifen.

Einmalig ROI-Koordinaten aus dem aktuellen Bild holen:

```bash
ros2 service call /promoc/camera/get_roi_coordinates \
  promoc_assembly_interfaces/srv/GetRoiCoordinates \
  "{window_name: 'Select MTF Search ROI'}"
```

Die Antwortwerte `roi_x`, `roi_y`, `roi_width` und `roi_height` koennen danach
direkt in wiederholten `measure_mtf`-Calls verwendet werden.

## MTF Quick Start

- `Auto-MTF`: Quadrat-Target ins Bild bringen, `measure_mtf` mit
  `measurement_mode='auto'`
  ausloesen, die 4 Kanten werden automatisch bewertet.
- `Capture-only`: `measurement_mode='capture_only'` nutzt dieselbe Raw-Capture-
  Validierung und standardmaessig die lokale Quadrat-Suche in einem Suchfenster.
  Wenn `roi_width`/`roi_height` gesetzt sind, kommt das Suchfenster aus dem
  Request; sonst wird interaktiv ein Rahmen im Bild gezogen. Das gilt auch fuer
  Messungen in der Bildmitte. Gespeichert wird ein Fullframe-Raw zur
  Nachvollziehbarkeit sowie kompakte Raw-ROI-Stacks fuer die Mittelung. Die
  MTF-Berechnung kann danach ueber Nacht mit
  `mtf_batch_analyze` laufen.
- `Capture-only direkt`: `measurement_mode='capture_only_direct'` behandelt
  `roi_x/y/width/height` direkt als Kanten-Crop. Damit entfaellt die
  Quadrat-/Kantensuche pro Messung; ideal fuer feste Serienpositionen.
- `ROI-Suche`: Nutzer markiert nur eine aeussere Such-ROI. Innerhalb dieser ROI
  muss ein vollstaendiges Quadrat liegen; daraus werden lokal wieder die vier
  Kantenkandidaten abgeleitet.
- `Direkte manuelle ROI`: ROI direkt im Bild waehlen. Der Analyzer nutzt intern
  einen schmaleren Analyse-Streifen, damit die Winkeldetektion robuster bleibt.
- `Standardpfad`: Erst `measure_mtf` mit `measurement_mode='auto'` verwenden.
  Wenn kein geeignetes Target gefunden wird oder die Zielkante unklar bleibt,
  `measurement_mode='roi_search'` nutzen. Nur wenn auch das nicht passt,
  `measurement_mode='direct_manual'` verwenden.
- `target_edge`: `any`, `top`, `right`, `bottom`, `left` und `select`
  funktionieren sowohl fuer den Center-Pfad als auch fuer die lokale
  ROI-Suche.
- `Ergebnisse`: Fuer jede Messung entsteht ein Run-Ordner mit `summary.csv`,
  `context.csv`, `selected_edge.txt` und pro Kante benannten
  `*_esf.csv`/`*_lsf.csv`/`*_mtf.csv`/`*_plot.png`/`*_roi.png`.
- `Capture-only Ergebnisse`: Vor der Offline-Auswertung enthaelt der Ordner
  `capture_manifest.json`, `capture_index.csv`, `summary.csv`, `context.csv`,
  `edges_overview.png`, `first_fullframe_raw.npy` und pro Kante
  `*_raw_stack.npy` sowie `*_roi.png`. Die Raw-Stacks enthalten einen
  konfigurierbaren Kontext-Rand um die Kante
  (`mtf.capture_only_context_margin_px`), damit die Offline-Auswertung bei
  knapp erkannten linken/rechten Kanten robuster bleibt.
- `Konservativer Standard`: Der Messstand nutzt im Standardpfad eine
  konservativ geglaettete ESF/LSF-Verarbeitung, um starke MTF-Overshoots
  softwareseitig zu bremsen.
- Fuer den schnellen Vergleich immer zuerst `summary.csv` oeffnen.
- Fuer wissenschaftliche Vergleichsmessungen ist `context.csv` die kanonische
  Ein-Zeilen-Beschreibung der Messbedingung.
- Overshoot-Warnungen bleiben bewusst sichtbar; `mtf_clip_max` ist nicht der
  offizielle Standardfix, sondern hoechstens spaeter ein bewusster
  Debug-/Praesentationshebel.
- `summary.csv` markiert pro Kante zusaetzlich, ob der gemessene Endwinkel in
  der offiziellen SOP-Arbeitszone `3 deg bis 10 deg` liegt.
- `context.csv` spiegelt dieselbe SOP-Wertung fuer genau die Kante, die auch
  an die ROS-Response zurueckgegeben wurde.

## Benutzerkonfiguration

Die persoenliche Messstand-Konfiguration kommt aus:

```bash
cp promoc_bringup/config/user_config.example.yaml promoc_bringup/config/user_config.yaml
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
- `/promoc/camera/measure_mtf_center`
- `/promoc/camera/measure_mtf_roi`
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
- `/promoc/camera/measure_mtf` fuer Auto-ROI, ROI-Suche oder direkte manuelle ROI

`/promoc/camera/measure_mtf_center` und `/promoc/camera/measure_mtf_roi`
bleiben als Kompatibilitaets-Aliase erhalten.

Alle weiteren Modi und Debug-Pfade bleiben fuer Vergleichs- oder
Entwicklungszwecke erhalten, sind aber nicht Teil des Standardablaufs.

## Wissenschaftliche MTF

Der kanonische MTF-Service `/promoc/camera/measure_mtf` und die beiden
Kompatibilitaets-Aliase `/promoc/camera/measure_mtf_center` und
`/promoc/camera/measure_mtf_roi` schalten fuer die Messung in denselben
wissenschaftlichen Raw-Capture-Modus:

- Der Kamerastream startet auf dem Messstand bereits direkt als `BayerRG12`
- Autofokus und Live-/Debug-Pfade leiten daraus intern nur ein `BGR8`-Preview ab
- Der wissenschaftliche MTF-Pfad bleibt dabei auf `raw passthrough`
- `PixelFormat=BayerRG12`
- `1x1`-Binning
- Auto-Exposure, Auto-Gain und Auto-Whitebalance aus
- Gamma und Farbtransformation aus
- Auswertung nur aus den echten Gruen-Senseln des `RGGB`-Musters

Die ESF wird direkt aus den realen Gruen-Sample-Koordinaten aufgebaut. Es gibt
kein Debayering und kein 2D-Auffuellen fehlender Bayer-Pixel.

Vergleich mehrerer Bedingungen passiert bewusst **ausserhalb von ROS** ueber
`context.csv` und `summary.csv`. Das offizielle Messprotokoll und die Bedeutung
der CSV-Spalten stehen in
[`MTF_PROTOCOL.md`](MTF_PROTOCOL.md).

Nur fuer Hardware-Notfaelle gibt es zwei klar getrennte Fallbacks:

- `BayerRG8` als zweites Raw-Startprofil, wenn `BayerRG12` auf der Hardware
  weiter Payload-/Buffer-Probleme macht
- `RGB8` nur als Debug-/Notfallmodus ueber die MTF-Config, nicht als
  offizieller wissenschaftlicher Messpfad

Fuer offizielle Slanted-Edge-Vergleiche gilt dabei die empfohlene Arbeitszone
`3 deg bis 10 deg`. Der Node bleibt aus Kompatibilitaetsgruenden technisch bei
`2 deg bis 10 deg`, aber die Export-CSV trennt jetzt sauber zwischen
technischer Node-Validitaet und offizieller SOP-Akzeptanz auf Basis des
gemessenen Endwinkels.

## Entwicklung

Dieser Branch ist bewusst klein gehalten. Gepflegt werden nur die Pfade, die
fuer Messstand, Autofokus, MTF und Export wirklich gebraucht werden.
