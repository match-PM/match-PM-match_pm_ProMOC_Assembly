# MTF Protocol

Dieses Dokument beschreibt den offiziellen wissenschaftlichen Arbeitsablauf
fuer den Messstand-Branch. Ziel ist ein lehrfreundlicher, aber belastbarer
**vergleichender Slanted-Edge-MTF-Teststand**.

## Zielbild

- Das Repo liefert **relative wissenschaftliche Validitaet** fuer
  Vergleichsmessungen im Labor.
- Verglichen werden spaeter **CSV-Exporte ausserhalb von ROS**.
- Auto-ROI, lokale ROI-Suche und direkte manuelle ROI sind gleichwertige
  Messpfade und muessen deshalb dieselbe Export- und Diagnose-Struktur liefern.

Nicht der Anspruch dieser Stufe:

- absolute metrologische Rueckfuehrbarkeit
- ein neuer ROS-Serienrunner fuer Vergleichskampagnen
- Debayering-basierte MTF

## Offizieller Messmodus

`/promoc/camera/measure_mtf` ist der kanonische MTF-Service und nutzt denselben
wissenschaftlichen Raw-Pfad wie die Kompatibilitaets-Aliase
`/promoc/camera/measure_mtf_center` und `/promoc/camera/measure_mtf_roi`:

- der Kamerastream startet passend zum Kameraprofil als Raw-Mono oder Raw-Bayer
- Autofokus/Fly-over erzeugen daraus intern nur ein 8-bit-Preview
- die Start-Belichtung kommt aus dem beim Launch geladenen Kamera-Profil
- Monochromprofil: `PixelFormat=Mono*` und `analysis_channel=mono`
- Farbprofil: `PixelFormat=Bayer*` und `analysis_channel=green`
- `1x1`-Binning
- echte Gruen-Sensel aus `RGGB`
- Auto-Exposure, Auto-Gain, Auto-Whitebalance aus
- Gamma und Farbtransformation aus
- Capture-Readback muss passen, sonst ist der Run fachlich ungueltig

Der Analyzer verwendet bei der Monochromkamera alle Sensorpixel. Bei einer
Farbkamera arbeitet er direkt auf den beiden echten Gruen-Senselgruppen. Es gibt
kein Debayering und kein 2D-Infill fuer den offiziellen Farbvergleichspfad. Der
Startparameter `mtf_analysis_channel:=mono|green|auto` kann das im Kameraprofil
hinterlegte Verhalten kontrolliert ueberschreiben; eine unpassende Kombination
aus Kanal und Raw-Format wird abgelehnt.

Der Standardpfad ist bewusst konservativer eingestellt:

- Savitzky-Golay-ESF-Glaettung ist standardmaessig aktiv
- die LSF wird standardmaessig um ihren Peak gefenstert
- die ISO-Derivatkorrektur ist aktiv, aber auf einen konservativen Faktor
  gedeckelt

Damit sollen starke Overshoots softwareseitig gebremst werden, ohne sie
diagnostisch zu verstecken.

`/promoc/camera/set_exposure` nutzt fuer Live-Belichtungswechsel denselben
ROS-Parameterpfad wie die restliche Kamera-Reconfigure-Logik. Wenn der
Wunschwert nicht sauber geschrieben oder rueckgelesen werden kann, ist die
beim Launch gesetzte Start-Belichtung die offizielle Fallback-Stufe.

Fallback-Reihenfolge bei Hardwareproblemen:

- zuerst `BayerRG8` als alternatives Raw-Startprofil pruefen
- `RGB8` nur als klar markierter Debug-/Notfallmodus verwenden

Vor der ersten Messung des Tages wird ein kurzer Raw-First-Preflight empfohlen:

- Topic `/promoc/assembly_camera/stream0/image_raw` liefert `bayer_rggb16`
- bei Vollsensor ist `step = 11072`
- `rqt_image_view` zeigt ein nutzbares Livebild
- Autofokus funktioniert mit demselben Raw-Start
- je eine kurze Auto-ROI- und manuelle ROI-Messung erzeugt vollstaendige Run-Ordner

## Vergleichs-SOP

Der Vergleich wird immer ueber **Einzelmessungen mit festem Protokoll**
durchgefuehrt. Zwischen zwei Bedingungen darf genau **eine Variable**
geaendert werden.

Offizielle Arbeitszone fuer Slanted-Edge-Vergleiche:

- **empfohlener Winkelbereich:** `3 deg bis 10 deg`
- **technischer Node-Hard-Gate:** derzeit `2 deg bis 10 deg`

Wichtig fuer die Auswertung:

- die CSV-Exporte bewerten nur `3 deg bis 10 deg` als **offiziell akzeptiert**
- ein realer Fall kann deshalb technisch noch vom Node verarbeitet werden, aber
  fuer die offizielle SOP trotzdem als nicht akzeptiert gelten

Konstant halten:

- Target und Kantenlage
- Arbeitsdistanz
- Kameraorientierung
- Beleuchtung
- Fokusstrategie
- Expositionsstrategie
- Objektiv, sofern es nicht selbst die Vergleichsvariable ist

Default fuer Vergleichsstudien:

- **5 Wiederholungen pro Bedingung**

## Datenfluss

Der offizielle MTF-Pfad ist absichtlich kurz:

```text
launch
  -> camera node
  -> measure_mtf service handler
  -> shared mtf analyzer
  -> debug export
  -> run folder (CSV + plots + ROI overlays)
```

Wichtige Rollen:

- `promoc_bringup`: startet den Messstand
- `camera_nodes/services/mtf.py`: orchestriert den kanonischen Service, Aliase, ROI,
  Export und Response ueber einen gemeinsamen Kern
- `camera_nodes/algorithms/mtf/`: Single Source of Truth fuer Winkel, ESF, LSF,
  MTF und Raw-Green-Auswertung

## ROI-Pfade

### Auto-ROI

- erkennt Quadrat- oder Bar-Targets
- sucht im gesamten aktuellen Messbild nach vollstaendig sichtbaren Targets
- nutzt konfigurierbare Mindestgroessen, um kleine Artefakte auszuschliessen
- erzeugt mehrere `EdgeROI`-Kandidaten
- wertet jede Kante ueber dieselbe Analyzer-Pipeline aus
- exportiert pro Kante eigene Artefakte

### Manuelle ROI

- Nutzer waehlt nur die aeussere ROI
- der Analyzer bestimmt daraus intern einen kleineren Analyse-Streifen
- Diagnose-Overlay zeigt:
  - aeussere ROI
  - inneren Analyse-Streifen
  - gefittete Kante
  - Support-Points und Winkelmethoden

Das ist wichtig, weil eine zu grosse oder schraeg gewaehlte manuelle ROI die
Winkeldetektion sonst stark verziehen kann.

### ROI-Suche Nach Vollstaendigem Quadrat

- Nutzer waehlt nur eine aeussere Such-ROI oder der Client uebergibt sie als
  Pixelkoordinaten
- innerhalb dieser Such-ROI wird ein vollstaendiges Quadrat bzw. eine
  vollstaendige Wuerfelflaeche gesucht
- daraus werden lokal dieselben vier `EdgeROI`-Kandidaten abgeleitet wie beim
  globalen Auto-ROI
- die lokalen Kanten werden anschliessend wieder in globale Bildkoordinaten
  zurueckprojiziert und durch dieselbe Analyzer- und Exportpipeline geschickt

Der empfohlene Bedienpfad fuer neue Messablaeufe ist ein Service:

1. `/promoc/camera/measure_mtf` mit `measurement_mode='auto'`
2. bei Bedarf `measurement_mode='roi_search'` und optionalem ROI
3. nur als letzter Fallback `measurement_mode='direct_manual'`

Fuer schnelle Serienmessungen kann derselbe Service mit
`measurement_mode='capture_only'` verwendet werden. Dieser Pfad schaltet und
validiert die wissenschaftliche Raw-Capture-Konfiguration, nutzt standardmaessig
ein Suchfenster fuer die lokale Quadrat-Suche, erkennt die Kanten einmal,
speichert standardmaessig ein Fullframe-Raw plus pro Kante einen Raw-ROI-Stack
und verschiebt die MTF-Berechnung in einen spaeteren Batch-Lauf. Das Suchfenster
kann per `roi_x/y/width/height` uebergeben oder interaktiv im OpenCV-Bild
gezogen werden; derselbe Ablauf gilt fuer Mitte, Rand und Ecke:

Wenn die Kantenposition bereits bekannt ist, kann
`measurement_mode='capture_only_direct'` verwendet werden. Dann ist
`roi_x/y/width/height` direkt der Kanten-Crop; es wird keine Quadrat- oder
Kantensuche ausgefuehrt.

```bash
ros2 run camera_nodes mtf_batch_analyze \
  --input <run-or-folder> \
  --recursive --overwrite \
  --target-edge top --min-valid-edges 1
```

Die Batch-Auswertung akzeptiert Teilresultate. Es muessen nicht alle vier
Kanten gueltig sein; mit `--min-valid-edges 1` reicht eine gueltige Zielkante.
Pro Kante werden die MTF-Werte ueber alle gueltigen Samples des Raw-Stacks
gemittelt und die verworfenen Samples in `summary.csv` mitgezaehlt. Die
technische Analyzer-Grenze erlaubt Kanten bis `11°`; die offizielle
SOP-Akzeptanz bleibt davon getrennt und markiert weiterhin nur `3°...10°` als
gueltiges SOP-Fenster.

Wenn ein Bereich mehrfach automatisiert gemessen werden soll, kann der
Hilfsservice `/promoc/camera/get_roi_coordinates` einmalig einen Suchrahmen
interaktiv abfragen und die Pixelkoordinaten zur Wiederverwendung zurueckgeben.

`target_edge='any'/'top'/'right'/'bottom'/'left'/'select'` bleibt auch fuer
diesen ROI-Suchpfad gueltig.

## Exportvertrag

Jeder Run landet in genau einem Messordner und enthaelt mindestens:

- `summary.csv`
- `context.csv`
- `selected_edge.txt`
- pro Kante `*_esf.csv`, `*_lsf.csv`, `*_mtf.csv`, `*_plot.png`, `*_roi.png`

Capture-only-Runs enthalten vor der Offline-Auswertung stattdessen
`capture_manifest.json`, `capture_index.csv`, `summary.csv`, `context.csv`,
`edges_overview.png`, `first_fullframe_raw.npy` und pro Kante `*_raw_stack.npy`
plus `*_roi.png`. Die `*_raw_stack.npy` enthalten einen konfigurierbaren
Raw-Kontext um die Kanten-BBox; `capture_manifest.json` speichert dazu
`stack_bbox`, `stack_origin` und `edge_bbox_in_stack`. Nach dem Batch-Lauf
werden dieselben finalen CSV-/Plot-Artefakte wie im Online-Pfad geschrieben.

### context.csv

`context.csv` ist die **kanonische Ein-Zeilen-Beschreibung der Messbedingung**.
Sie ist fuer spaetere Vergleiche gedacht und enthaelt unter anderem:

- Operator
- Timestamp
- ROI-Modus, zum Beispiel `auto_square4`, `roi_square_search`, `manual` oder
  `capture_only`
- ROI-Erkennungsmodus, zum Beispiel `auto`, `search_square_in_roi` oder
  `direct_manual`
- Objektiv und Magnification aus der Messstand-Konfiguration
- effektive Pixelgroesse aus der Kamera-Konfiguration
- freie Notizen, zum Beispiel Lichtwerte, falls fuer die Messreihe relevant
- Fokusposition
- Capture-Readback und verfuegbare Keys
- Warnungen, Fehler und Notizen
- offizielle SOP-Wertung der ausgewaehlten Antwortkante
- gemessenen Endwinkel der ausgewaehlten Antwortkante

### summary.csv

`summary.csv` ist die **Kanten-Tabelle**. Pro Kante stehen dort unter anderem:

- Validitaet
- MTF50, MTF20, MTF10
- Kantenwinkel
- Kontrast
- G1/G2-Werte und Delta
- Analyse-Strip
- Support-Points
- Winkelmethode und Konsistenz
- offizielle SOP-Wertung fuer die Kante auf Basis des gemessenen Endwinkels

Wichtig:

- ROS-Services bleiben dadurch unveraendert
- technisch gueltige, aber ausserhalb der offiziellen Arbeitszone liegende Runs
  bleiben `success=true`
- die offizielle SOP-Akzeptanz steht nur in den CSV-Exporten und bleibt bewusst
  getrennt von der technischen Node-Validitaet
- Overshoot bleibt in `warning_msg`, `mtf_peak_raw`, `mtf_peak_used` und
  `mtf_clipped` sichtbar; `mtf_clip_max` ist kein offizieller Standardfix
