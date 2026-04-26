# MTF Protocol

Dieses Dokument beschreibt den offiziellen wissenschaftlichen Arbeitsablauf
fuer den Messstand-Branch. Ziel ist ein lehrfreundlicher, aber belastbarer
**vergleichender Slanted-Edge-MTF-Teststand**.

## Zielbild

- Das Repo liefert **relative wissenschaftliche Validitaet** fuer
  Vergleichsmessungen im Labor.
- Verglichen werden spaeter **CSV-Exporte ausserhalb von ROS**.
- `auto_roi`, lokale ROI-Suche und direkte manuelle ROI sind gleichwertige
  Messpfade und muessen deshalb dieselbe Export- und Diagnose-Struktur liefern.

Nicht der Anspruch dieser Stufe:

- absolute metrologische Rueckfuehrbarkeit
- ein neuer ROS-Serienrunner fuer Vergleichskampagnen
- Debayering-basierte MTF

## Offizieller Messmodus

`/promoc/camera/measure_mtf_center` und `/promoc/camera/measure_mtf_roi`
nutzen denselben wissenschaftlichen Raw-Pfad:

- der Kamerastream startet bereits offiziell als `BayerRG12`
- Autofokus/Fly-over erzeugen daraus intern nur ein 8-bit-Preview
- die Start-Belichtung kommt aus dem beim Launch geladenen Kamera-Profil
- `PixelFormat=BayerRG12`
- `1x1`-Binning
- echte Gruen-Sensel aus `RGGB`
- Auto-Exposure, Auto-Gain, Auto-Whitebalance aus
- Gamma und Farbtransformation aus
- Capture-Readback muss passen, sonst ist der Run fachlich ungueltig

Der Analyzer arbeitet direkt auf den Gruen-Samples. Es gibt kein Debayering und
kein 2D-Infill fuer den offiziellen Vergleichspfad.

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

- der Standalone-Validator bewertet nur `3 deg bis 10 deg` als **offiziell akzeptiert**
- ein synthetischer oder realer Fall kann deshalb technisch noch vom Node
  verarbeitet werden, aber fuer die offizielle SOP trotzdem als nicht akzeptiert
  gelten

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

### Beam-Splitter-Vergleich

Fuer einen sauberen `use_beamsplitter`-Vergleich bleiben konstant:

- Objektiv
- Arbeitsdistanz
- Target
- Kamerawinkel
- Beleuchtung
- Fokuspfad

Es wechselt nur:

- `use_beamsplitter = false`
- `use_beamsplitter = true`

## Datenfluss

Der offizielle MTF-Pfad ist absichtlich kurz:

```text
launch
  -> camera node
  -> measure_mtf_center / measure_mtf_roi service handler
  -> shared mtf analyzer
  -> debug export
  -> run folder (CSV + plots + ROI overlays)
```

Wichtige Rollen:

- `promoc_bringup`: startet den Messstand
- `camera_nodes/services/mtf.py`: orchestriert beide Service-Einstiege, ROI,
  Export und Response ueber einen gemeinsamen Kern
- `camera_nodes/algorithms/mtf/`: Single Source of Truth fuer Winkel, ESF, LSF,
  MTF und Raw-Green-Auswertung
- `mtf_synthetic_validation.py`: ruft denselben Repo-Kern fuer synthetische
  Validierung auf

## ROI-Pfade

### Auto-ROI

- erkennt Quadrat- oder Bar-Targets
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

- Nutzer waehlt nur eine aeussere Such-ROI
- innerhalb dieser Such-ROI wird ein vollstaendiges Quadrat bzw. eine
  vollstaendige Wuerfelflaeche gesucht
- daraus werden lokal dieselben vier `EdgeROI`-Kandidaten abgeleitet wie beim
  globalen Auto-ROI
- die lokalen Kanten werden anschliessend wieder in globale Bildkoordinaten
  zurueckprojiziert und durch dieselbe Analyzer- und Exportpipeline geschickt

Der empfohlene Bedienpfad ist:

1. `/promoc/camera/measure_mtf_center`
2. bei Bedarf `/promoc/camera/measure_mtf_roi` mit `roi_detection_mode='search_square_in_roi'`
3. nur als letzter Fallback `/promoc/camera/measure_mtf_roi` mit `roi_detection_mode='direct_manual'`

`target_edge='any'/'top'/'right'/'bottom'/'left'/'select'` bleibt auch fuer
diesen ROI-Suchpfad gueltig.

## Exportvertrag

Jeder Run landet in genau einem Messordner und enthaelt mindestens:

- `summary.csv`
- `context.csv`
- `selected_edge.txt`
- pro Kante `*_esf.csv`, `*_lsf.csv`, `*_mtf.csv`, `*_plot.png`, `*_roi.png`

### context.csv

`context.csv` ist die **kanonische Ein-Zeilen-Beschreibung der Messbedingung**.
Sie ist fuer spaetere Vergleiche gedacht und enthaelt unter anderem:

- Operator
- Timestamp
- ROI-Modus
- ROI-Erkennungsmodus im Sinne von `auto`, `roi_square_search` oder `manual`
- Objektiv und Magnification
- `use_beamsplitter`
- coaxiale Lichtwerte
- effektive Pixelgroesse und deren Quelle
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

## Validator

Der Standalone-Validator bleibt ein duennes Frontend um denselben Repo-Kern:

```bash
python mtf_synthetic_validation.py --profile quick
python mtf_synthetic_validation.py --profile scientific --no-png
```

Er dient fuer:

- algorithmische Regression
- ROI-/Paritaets-Checks
- Winkelstabilitaet auf synthetischen Targets
- Boundary-Pruefung gegen die offizielle Arbeitszone `3 deg bis 10 deg`

Der Validator trennt dabei bewusst zwischen:

- **technischer Node-Validitaet**
- **offizieller SOP-Akzeptanz**

Beispiel:

- ein synthetischer `2.5 deg`-Fall kann technisch noch `valid=True` sein
- im Validator wird er trotzdem als **offiziell nicht akzeptiert** gewertet

Er ersetzt keine echte Laborvalidierung mit realen Targets und Wiederholungen.
