# Automatisierte MTF-Messreihen – Stand 2026-09-04

Implementiert im Branch `messstand`; Softwaretests und synthetische Durchläufe vorhanden.
**Noch nicht am realen Messstand freigegeben.** Keine Hardwarebewegungen wurden bei der Entwicklung ausgelöst.

## Messentscheidung

- Lokale Bestschärfe pro Versuchsbedingung (`local_best`), keine gemeinsame Fokusebene.
- Grünes Koaxiallicht, 20,0 V Referenz; tatsächliche Anzeige vom Bediener bestätigen.
- Auto-Exposure gleicht P95 der ausgewählten Kanten-ROI auf 0,75 des nativen Sensorbereichs an;
  Toleranz standardmäßig 0,02, höchstens 0,1 % der Pixel über 98 %.
- Verschiedene Komponenten dürfen unterschiedliche Belichtungszeiten benötigen. Keine Histogrammangleichung.
- Gain bleibt fest. Nach Vorbereitung bleiben Exposure, ROI und Fokus für 50×10 unverändert.
- Die Daten beschreiben System-MTF bei lokalem Bestfokus, keine isolierte Objektiv-MTF oder kalibrierte Transmission.

## Softwareaufteilung

`measurement_plan.py` validiert die flache YAML-v1. Der Runner löst Defaults und Overrides auf,
wählt vor dem Action-Start interaktiv **eine schräge Kante mit heller und dunkler Plateaufläche** und
sendet eine typisierte `MeasurementCondition` an `/promoc/camera/start_measurement`.
Die Action liest keine YAML-Dateipfade. `plan_source` ist nur ein archivierter Text-Snapshot.

Der hardwareunabhängige `MeasurementEngine` läuft innerhalb des Kameraknotens. Damit kann die Action
vorhandene Raw-/Exposure-/MTF-Bausteine ohne Selbstaufrufe über ROS benutzen. Die neue deterministische
lokale Fokusstrategie scannt das konfigurierte Fenster aufsteigend und verfeinert einmal zwischen den
Nachbarn des Maximums, soweit die Positionstoleranz eine feinere Abtastung erlaubt. Tenengrad wird bei
Mono direkt, bei Bayer auf den zwei echten grünen Teilgittern berechnet. Kein Debayering im Messpfad.
Die bisherigen manuellen Autofokus-Services bleiben verfügbar.

Das ist das beste **abgetastete lokale** Ergebnis, keine Garantie eines mathematisch exakten Maximums.
Fenster, Abtastung und Toleranz müssen zum realen Schärfefenster passen. Randmaxima, flache Kurven und
schlechte Wiederkehr zum Maximum werden abgelehnt. Die vollständige Kurve und Rasterweite werden gespeichert.

## Reihenfolge

1. Manuell aufbauen, Achse referenzieren, sichere Fahrstrecke bestätigen und grob fokussieren.
2. Bedingung auswählen und Kamera/Objektiv/Target/Licht kontrollieren.
3. Kanten-ROI auswählen (oder explizite Pixelwerte in der YAML).
4. Action: Kamerasperre und Achsreservierung, frische Readbacks/Frames und Grenzwerte prüfen.
5. Auto-Exposure, lokaler Fokus mit festem Exposure, abschließender Exposure-Check.
6. Bei Bedarf einmal nachregeln; ab 10 % Exposure-Änderung einmal lokal nachfokussieren und erneut prüfen.
7. Einstellungen, Fokuskurve, Raw-Referenz und ROI-Vorschaubild speichern.
8. Je Wiederholung: Park → Fokus → frische Position/Stillstand → Einschwingen/Frame-Verwerfen → Raw-Stack.
9. Kamera-Readbacks vor/nach dem Stack und Achsposition prüfen. Daten mit Prüfsummen vollständig speichern.
10. Fortschritt aktualisieren. Zwischen den Wiederholungen weder AF noch AE ausführen.

Auch die erste Wiederholung fährt weg und zurück. V1 verlangt eine Parkposition **unterhalb des gesamten
Fokusfensters**, sodass finale Anfahrten immer aus derselben Richtung erfolgen. Keine automatische
Erweiterung in den 300-mm-Achsbereich und keine automatische Referenzfahrt.

## Startbefehle

```bash
cd /home/sterni/Development/ros2/humble_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select promoc_assembly_interfaces promoc_core linear_axis_nodes camera_nodes promoc_bringup --symlink-install
source install/setup.bash
```

Die Interfaces `GetPosition` und `MoveAbsolute` wurden erweitert. Alle laufenden betroffenen ROS-Prozesse
nach dem Build neu starten und in neuen Terminals die neue Workspace-Umgebung laden.

Ohne Kamera/Achse: Simulation und Planauflistung:

```bash
ros2 run camera_nodes measurement_runner --plan src/promoc_bringup/config/measurement_plans/pilot_simulation.yaml --condition pilot-2x2 --simulate
ros2 run camera_nodes measurement_runner --plan src/promoc_bringup/config/measurement_plans/screening_green_v5.yaml --list
```

Die Simulation schreibt ausschließlich nach `/tmp/mtf_measurement_simulation/pilot-simulation/`.
Simulationsdaten sind kein Hardwaretest. Das Simulationsprofil wird vom Hardware-Preflight nicht akzeptiert.

Für Hardware zuerst eine Arbeitskopie der Kampagnenvorlage anlegen und bearbeiten, beispielsweise
`src/promoc_bringup/config/measurement_plans/screening_lab.yaml`. Die Vorlage überschreibt keine Laborwerte:

```bash
cp --no-clobber src/promoc_bringup/config/measurement_plans/screening_green_v5.yaml src/promoc_bringup/config/measurement_plans/screening_lab.yaml
nano src/promoc_bringup/config/measurement_plans/screening_lab.yaml
ros2 run camera_nodes measurement_runner --plan src/promoc_bringup/config/measurement_plans/screening_lab.yaml --condition m001-screening-color-myutron-1x --validate
```

Nach Start des passenden Kameraprofils, manueller Grobfokussierung und bestätigtem Aufbau zunächst 2×2:

```bash
ros2 run camera_nodes measurement_runner --plan src/promoc_bringup/config/measurement_plans/screening_lab.yaml --condition m001-screening-color-myutron-1x --set measurement_count=2 --set frames_per_measurement=2 --confirm-setup
```

Erst nach Pilotfreigabe ohne die beiden Anzahl-Overrides die 50×10-Reihe starten.
Der Runner zeigt Fortschritt. `Ctrl+C` fordert Abbruch an und wartet auf kontrollierte Beendigung.
Terminal-Schließen ist **keine** garantierte Abbruchanforderung; der Server kann weiterlaufen.

## YAML v1: bewusst flache Felder

```yaml
schema_version: 1
campaign_id: meine-kampagne
source: Versuchsplan V5, letzter Tabellenreiter
defaults:
  operator_name: Name
  setup_id: tagesdatum-physischer-aufbau-01
  # weitere typisierte Felder aus den mitgelieferten Vorlagen
conditions:
  - condition_id: m001-screening-color-myutron-1x
    experiment_id: V003
    plan_row_number: 3  # Spalte Nr., NICHT die physische Excel-Zeilennummer
```

Die V5-Bedienkennungen sind unabhängig von den lückenhaften Excel-Zeilennummern aufgebaut:

- `m001` bis `m146` geben die lückenlose Reihenfolge der Messkampagne an.
- Der nachfolgende Slug beschreibt Screening beziehungsweise Strahlführung, Target, Komponente und Wiederholung.
- `experiment_id` und `plan_row_number` bleiben unverändert als Rückverweis auf den ursprünglichen Excel-Plan erhalten.

Beispiele: `m006-screening-mono-myutron-1x`, `m012-straight-center-none-r0` und `m146-turn90-bottom-left-prism-r2`.

Keine verschachtelten AE-/AF-Blöcke aus früheren Konzeptnotizen verwenden. Zulässige Felder und
konkrete Defaults stehen in `camera_nodes/camera_nodes/measurement_plan.py` / `MeasurementCondition.msg`.
Unbekannte Schlüssel, doppelte Schlüssel/IDs, nicht endliche Zahlen, unsichere Grenzen und fehlende
Pflichtwerte werden abgelehnt. Explizite `0`-ROI-Breite und -Höhe wählen im Runner interaktive Auswahl.

Vor Ort zwingend ausfüllen/prüfen:

- `operator_name`, `setup_id`: physischer Neuaufbau ist nicht gleich Neustart der Software.
- `illumination_voltage_v`: tatsächliche Anzeige bei Referenz 20,0 V; V1 akzeptiert 19,5–20,5 V.
- `axis_min_mm`, `axis_max_mm`, `park_position_mm`: sichere absolute Grenzen/Fahrstrecke.
- `position_tolerance_mm`, `settle_time_s`, `fine_focus_half_range_mm`, `focus_samples`.
- `exposure_min_us`, `exposure_max_us`, `frame_timeout_s`, `expected_gain`.
- `output_root`: absoluter beschreibbarer Messordner mit ausreichend Speicher.
- `camera_profile`, `camera_serial`, `objective_id`, `objective_family`, `magnification_x`.

Die Vorlagen setzen absichtlich keine angenommenen sicheren Achspositionen. `REPLACE`-Werte sind Startblocker.
Die Kamera-GUID wird mit der konfigurierten Seriennummer verglichen; physische Seriennummer zusätzlich
am Gerät bestätigen. Derzeit ist dies **kein unabhängiges Hardware-Seriennummern-Readback**.
Homing wird vom Bediener bestätigt; die Software erkennt Änderungen der Referenz-Epoche beim Homing.

## Vollständiger V5-Plan

- `screening_green_v5.yaml`: 10 grüne Kamera-/Objektivbedingungen.
- `components_green_v5.yaml`: V041 + 60 gerade + 75 umgelenkte Bedingungen = 136.
- Insgesamt 146 × 50 × 10 = 73.000 geplante Frames, ohne Referenzbilder, Fokus-/AE-Frames und Fehlversuche.
- `source_green_v5.csv`: lesender Connector-Export der letzten Tabelle der Originaldatei.
- Die späteren `?`-Lichtfelder dieser Tabelle werden gemäß Nutzerentscheidung als grün interpretiert.
- Komponentenplan benötigt eine bewusst eingetragene Gewinnerkombination aus dem Screening.
  Ursprünglich eingetragene Mono-Kamera steht zur Nachvollziehbarkeit in den Notes; keine automatische Wahl.
- `4gx` bleibt `budget-4gx`, getrennt von `myutron-4x` trotz nominal 4,0×.
- Die Bediennummer steckt lückenlos als `m001` bis `m146` in `condition_id`; doppelte Excel-Kennungen wie V054–V057 bleiben über den beschreibenden Slug und die Quellenfelder eindeutig.

## Ergebnisse und Logging

```text
<output_root>/<campaign_id>/runs/<condition_id>__<UTC>__<UUID>/
  resolved_condition.yaml       # aufgelöste Sollvorgabe + Hash + IDs
  plan_snapshot.yaml            # unveränderte Quellkonfiguration
  preflight.json                # Geräte-/Software-/Parameterstand, Quellen der Angaben
  preparation.json              # tatsächliche Exposure/Fokus/ROI-Kontext/Analyseparameter
  focus_curve.csv
  reference_raw.npy
  reference_preview.png         # nur Kontrolle, keine MTF-Eingabe
  events.jsonl                  # strukturierte Phasen/Fehler, UTC; leere Zeilen ignorieren
  progress.json                 # wiederherstellbare Übersicht
  capture_index.csv
  measurements/m001/attempt_01/
    edge_raw_stack.npy          # Raw-ROI plus Kontext, unverändert
    frames.csv                  # eindeutige Zeitstempel und Helligkeitsdiagnostik je Frame
    capture_manifest.json      # Readbacks, Positionen, ROI, Prüfsummen, Qualitätsflags
  analysis/<analysis_id>/
    frame_results.csv
    measurement_results.csv
    series_summary.csv
    analysis_manifest.json
    curves/m001.npz             # MTF-/ESF-/LSF-Kurven der Einzelbilder
```

Eine vollständige Messung wird erst nach NPY/Frame-Tabelle/Manifest-Prüfung atomar aus `.pending`
umbenannt. Dateiinhalt und Verzeichniseinträge werden synchronisiert. Unvollständige Versuche bleiben
als `.pending` mit Fehlerangabe und – soweit speicherbar – Teilframes erhalten. Keine Lösch-/Überschreiblogik.
Bei Resume werden Framezahl, Zeitstempel und SHA256 geprüft; der Fortschrittszähler allein wird nicht vertraut.

Pro Frame wird ein steigender ROS-Quellzeitstempel und die Empfangszeit festgehalten. Hardware-Frame-IDs
und der genaue Belichtungsbeginn sind vom Treiber nicht geliefert und werden nicht erfunden. Die
Frame-Frische basiert auf Queue-Tiefe 1, Wartezeit und verworfenen Frames nach einer neuen Zeitbarriere.
Dieses Verhalten muss unter realer Auslastung geprüft werden; ein Hardware-Triggerpfad ist nicht implementiert.

Kamerawerte stammen aus ROS-Treiber-Parameter-Readbacks, nicht aus einer zusätzlichen unabhängigen
GenICam-Abfrage. Pflicht-Readbacks müssen verfügbar sein, andernfalls blockiert der Preflight.
Direkte Eingriffe am separaten Aravis-Treiber außerhalb der Messstand-Schnittstellen sind während eines Runs
verboten; sie lassen sich nicht vollständig durch die lokale Kamerasperre verhindern. Vor-/Nach-Readbacks
erkennen persistente Änderungen, nicht garantiert kurzzeitige Änderungen zwischen zwei Abfragen.

## Fehler und Wiederaufnahme

- Frame-Timeout: begrenzter zusätzlicher Aufnahmeversuch an derselben Position, mit eigener Attempt-ID.
- Niedrige MTF: wird nicht durch automatische Wiederholung verbessert/selektiert; Offline-Ergebnis bleibt erhalten.
- Intensitätsdrift: vollständigen Stack mit Flag behalten, Reihe stoppen; keine AE mitten in der Reihe.
- Kameraformat/Gain/Belichtungsänderung, fehlende Position, Grenzverletzung, Speicherfehler: abbrechen.
- Stop/Not-Halt bleiben auch bei Reservierung möglich; Cleanup hebt einen Not-Halt nicht auf.
- Achsreservierung hat einen 30-s-Watchdog mit 5-s-Heartbeat. Bei Verlust wird Stop angefordert;
  dies ist **kein sicherheitsgerichteter Hardware-Not-Halt** und ersetzt keine mechanische Absicherung.

Resume nur mit exakter Run-ID, identischer aufgelöster Konfiguration, bestätigtem unverändertem Aufbau,
gleicher Kamera-Node-Sitzung und Achsreferenz. Keine neue AE/AF bei Resume. Bei Hardware-/Node-Neustart,
erneutem Homing, Drift oder unvollständiger Vorbereitung wird ein neuer Run benötigt. Alte Daten bleiben erhalten.

```bash
ros2 run camera_nodes measurement_runner --plan /absoluter/pfad/screening_lab.yaml --condition m001-screening-color-myutron-1x --resume RUN_ID --confirm-setup
```

Bei einem 2×2-Pilot-Resume müssen dieselben Anzahl-Overrides erneut angegeben werden.
Die bisherige Pixel-ROI wird automatisch aus dem Run übernommen, wenn die Plan-ROI interaktiv war.

## Offline-Auswertung

```bash
ros2 run camera_nodes measurement_analyze --run /absoluter/pfad/zum/run
ros2 run camera_nodes measurement_analyze --campaign /absoluter/pfad/zur/kampagne
```

Neue Runs verwenden diese Befehle, nicht den alten `mtf_batch_analyze` (dieser bleibt für Legacy-Manifeste).
Jede Analyse bekommt einen neuen Ordner. Kampagnenanalyse schreibt `campaign_summary.csv` plus `errors.json`;
Fehler einzelner Runs werden ausgewiesen und führen zu einem Nichtnull-Exitcode.

MTF50/20/10 werden pro Frame ausgewertet und als **Bildraum-lp/mm** bezeichnet. Pro Achswiederholung wird
der Median der technisch gültigen Einzelwerte ausgegeben, zusätzlich deren Streuung. Die Serienübersicht
enthält Mittelwert und Streuung dieser Wiederholungsmediane. Ungültige Frames werden mit Fehlergrund gezählt,
nicht als Null-MTF interpretiert. Warnungen/SOP-Kantenwinkel (3–10°) sind gesondert markiert. Eine fachliche
Freigabe ist nicht gleich einem erfolgreichen Capture. Die drei Neuaufbauten bleiben separate Datensätze;
keine automatische Zusammenfassung zu 500 unabhängigen Wiederholungen.

## Freigabetests vor Ort

- [ ] Alle Pflicht-Readbacks verfügbar; Mono und Bayer jeweils prüfen.
- [ ] 2×2-Pilot mit realem Aufbau und anschließender Analyse erfolgreich.
- [ ] Auswahl einer einzelnen passenden Kante, Referenzbild/ROI und Bayer-Ursprung prüfen.
- [ ] Fokusfenster trifft einen klaren Peak; feinste Rasterweite zur erforderlichen Schärfe passend.
- [ ] Positionstoleranz und tatsächliche Wiederholgenauigkeit zur Fokuskurve passend.
- [ ] Einschwingzeit sowie gepufferte Frames unter realistischer Kameralast prüfen.
- [ ] AE-Ziel mit/ohne Strahlteiler erreichbar; Licht stabil; kein Gain-Fallback.
- [ ] Abbruch während Fahrt/Capture sowie parallele Bedienversuche kontrolliert testen.
- [ ] Resume ohne Neueinstellung und Abweisung nach verändertem Aufbau/Homing überprüfen.
- [ ] Speicherverbrauch/Laufzeit einer Reihe messen, danach 50×10-Probereihe.
- [ ] Backup der Kampagne auf zweites Medium einrichten und Prüfsummen kontrollieren.

Softwaretests:

```bash
cd /home/sterni/Development/ros2/humble_ws/src
python3 -c 'import cv2, pytest; raise SystemExit(pytest.main(["camera_nodes/test", "linear_axis_nodes/test", "promoc_bringup/test", "-q"]))'
cd /home/sterni/Development/ros2/humble_ws
source install/setup.bash
python3 src/camera_nodes/test/measurement_ros_smoke.py
```

Der ROS-Smoke-Test prüft Nachrichtentransport-Serialisierung und Action-Callbacks mit synthetischem IO,
aber weder DDS-Discovery noch echte Hardware. Keine Hardware-Freigabe aus Softwaretestergebnissen ableiten.
