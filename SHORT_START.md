# README_GER

Diese Datei bleibt auf dem `messstand`-Branch nur als kurze Weiterleitung.
Die gepflegte Hauptdoku fuer Start, Bedienung und Service-Beispiele steht in
[README.md](README.md).

## Kurzfassung

- In jedem neuen Terminal zuerst `source ~/.bashrc`
- Messstand starten mit:

```bash
ros2 launch promoc_bringup optical_measurement_system.launch.py
```

- Danach:
  - `rqt`
  - `ros2 run rqt_image_view rqt_image_view `
- Standardablauf:
  - bei Bedarf `set_exposure`
  - dann `autofocus` mit `focus_mode=0`
  - fuer schnelle Serienmessungen die Bilder mit `capture_only` aufnehmen
  - spaeter offline mit `mtf_batch_analyze` auswerten
  - fuer die Auswertung zuerst `batch_summary.csv`, danach `summary.csv` oeffnen

## Empfohlener Aufnahme- und Offline-Ablauf

1. Messstand starten:

```bash
source ~/.bashrc
ros2 launch promoc_bringup optical_measurement_system.launch.py
```

2. Bild kontrollieren:

```bash
ros2 run rqt_image_view rqt_image_view
```

3. Autofokus laufen lassen.

Der normale `autofocus` nutzt die feste Analyse-ROI aus
`promoc_bringup/config/user_config.yaml`:

```yaml
autofocus:
  analysis_roi_x_px: 1979
  analysis_roi_y_px: 1010
  analysis_roi_width_px: 1689
  analysis_roi_height_px: 1624
```

Call:

```bash
ros2 service call /promoc/camera/autofocus \
  promoc_assembly_interfaces/srv/AutoFocus \
  "{start_position: 285.0, end_position: 287.0, focus_mode: 0, skip_flyover: false, save_best_image: false}"
```

Im Log sollte stehen:

```text
AF analysis: mode=configured-roi configured_roi=(1979,1010,1689,1624)
```

4. Rohdaten fuer spaetere Auswertung aufnehmen.

Wenn im ROI ein komplettes Quadrat-Target liegt:

```bash
ros2 service call /promoc/camera/measure_mtf \
  promoc_assembly_interfaces/srv/MeasureMTF \
  "{measurement_mode: 'capture_only', target_edge: 'any', roi_x: 1979, roi_y: 1010, roi_width: 1689, roi_height: 1624}"
```

Wenn die Kanten-ROI schon exakt bekannt ist und keine Quadrat-Suche laufen soll:

```bash
ros2 service call /promoc/camera/measure_mtf \
  promoc_assembly_interfaces/srv/MeasureMTF \
  "{measurement_mode: 'capture_only_direct', target_edge: 'any', roi_x: 1979, roi_y: 1010, roi_width: 1689, roi_height: 1624}"
```

Der Capture-Ordner enthaelt danach unter anderem:

```text
capture_manifest.json
capture_index.csv
first_fullframe_raw.npy
*_raw_stack.npy
*_roi.png
edges_overview.png
summary.csv
context.csv
```

Die MTF-Auswertung nutzt die `*_raw_stack.npy`, nicht die PNGs.
Die Raw-Stacks enthalten einen Kontext-Rand um die Kante. Der Rand wird in
`promoc_bringup/config/user_config.yaml` gesetzt:

```yaml
mtf:
  max_edge_angle: 11.0
  capture_only_context_margin_px: 64
```

`max_edge_angle: 11.0` ist die technische Analyzer-Grenze. Die offizielle
SOP-Bewertung bleibt bei maximal `10.0°`; Kanten knapp ueber `10°` bekommen
dadurch trotzdem MTF-Werte, werden aber im Protokoll als ausserhalb des
SOP-Fensters markiert.

5. Offline auswerten:

```bash
ros2 run camera_nodes mtf_batch_analyze \
  --input "$HOME/Dokumente/Messungen/Yannis Wesser/Test/mtf_messungen" \
  --recursive --overwrite \

```

Ergebnisdateien:

```text
batch_summary.csv
summary.csv
context.csv
selected_edge.txt
*_mtf.csv
*_plot.png
```

Die `*_roi.png` werden nach der Offline-Auswertung als vergroesserte
Review-Bilder neu geschrieben. Gruen/rot markiert die gespeicherte Kanten-ROI,
blau markiert den tatsaechlich analysierten Streifen.

## Weitere Details

- Die kanonische Benutzerkonfiguration ist `promoc_bringup/config/user_config.example.yaml`.
- Wissenschaftliches Protokoll: `MTF_PROTOCOL.md`
- Vollstaendige Bedienanleitung: `README.md`
