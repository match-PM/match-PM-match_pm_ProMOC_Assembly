# ROS-2-Actions am ProMOC-Messstand

Dieses Dokument beschreibt die Benutzung der kamerabasierten
Target-Verkippungsmessung `EstimateTargetTilt`. Action und Service fahren einen Fokus-
Scan, nimmt an jeder Achsposition mehrere Bilder auf und bestimmt aus den
optimalen Fokuspositionen räumlich verteilter ROIs die Targetebene.

Die Action misst ausschließlich. Sie verstellt keine mechanische Kippachse.

## Übersicht

| Eigenschaft | Wert im Standard-Launch |
| --- | --- |
| Action-Name | `/promoc/promoc_camera/estimate_target_tilt` |
| Action-Typ | `promoc_assembly_interfaces/action/EstimateTargetTilt` |
| Action-Node | `/promoc/promoc_camera/target_tilt_estimator` |
| Bild-Topic | `/promoc/promoc_camera/stream0/image_raw` |
| Fokusachse | `/promoc/linear_axis/lts300_x_axis` |
| Konfiguration | Node-Defaults < gewähltes Imaging-Profil < `user_config.yaml` |

Für `rqt_service_caller` steht zusätzlich der synchrone Service
`/promoc/promoc_camera/estimate_target_tilt_service` vom Typ
`promoc_assembly_interfaces/srv/EstimateTargetTilt` bereit. Er leitet intern
ein Goal an dieselbe Action weiter; Kamera- und Achslogik existieren nur einmal.

## Einfacher Aufruf über rqt

1. `rqt` starten.
2. **Plugins → Services → Service Caller** öffnen.
3. `/promoc/promoc_camera/estimate_target_tilt_service` auswählen.
4. Scanparameter eintragen und **Call** drücken.

Beispielwerte sind `center_z_mm: 294.19`, `half_range_mm: 0.15`,
`step_mm: 0.01`, `frames_per_position: 5`, `fit_field_curvature: false` und
`return_to_center: true`.

Der Service antwortet erst nach dem vollständigen Scan. Über ihn gibt es kein
laufendes Feedback und keinen Cancel-Button. Für Fortschrittsfeedback und
Abbruch bleibt die Action die geeignete Schnittstelle.

Die Achse heißt in der vorhandenen Hardware-API `lts300_x_axis`. Innerhalb der
Tilt-Action heißt ihre optische Fokuskoordinate trotzdem `z`. Der
`axis_service_prefix` ist konfigurierbar, falls später eine anders benannte
Fokusachse verwendet wird.

## Bauen und starten

Nach Änderungen an Action-Definition, Python-Code oder Konfiguration:

```bash
cd /home/pmlab/ros2_ws

colcon build --packages-select \
  promoc_assembly_interfaces camera_nodes promoc_bringup

source install/setup.bash
```

Den vollständigen Messstand starten:

```bash
ros2 launch promoc_bringup optical_measurement_system.launch.py
```

Der normale Launch startet den Tilt-Estimator automatisch als separaten Node.
Die Action ist nicht Teil des Prozesses `camera_node`; beide Nodes werden aber
vom selben Launch gestartet.

In einem zweiten Terminal muss ebenfalls der Workspace geladen werden:

```bash
cd /home/pmlab/ros2_ws
source install/setup.bash

ros2 action list -t
ros2 action info /promoc/promoc_camera/estimate_target_tilt
```

Erwartete Ausgabe von `ros2 action list -t`:

```text
/promoc/promoc_camera/estimate_target_tilt [promoc_assembly_interfaces/action/EstimateTargetTilt]
```

Weitere Laufzeitkontrollen:

```bash
ros2 node info /promoc/promoc_camera/target_tilt_estimator

ros2 param get \
  /promoc/promoc_camera/target_tilt_estimator \
  object_um_per_pixel

ros2 topic echo \
  /promoc/promoc_camera/stream0/image_raw \
  sensor_msgs/msg/Image \
  --once --field encoding
```

## Action ausführen

Empfohlener erster Testscan:

```bash
ros2 action send_goal --feedback \
  /promoc/promoc_camera/estimate_target_tilt \
  promoc_assembly_interfaces/action/EstimateTargetTilt \
  "{center_z_mm: 284.985, half_range_mm: 0.1, step_mm: 0.01, frames_per_position: 5, fit_field_curvature: false, return_to_center: true}"
```

Dieser Aufruf misst von `284.885 mm` bis `285.085 mm` in Schritten von
`0.010 mm`. Das sind 21 Achspositionen und bei fünf Bildern pro Position
insgesamt 105 ausgewertete Bilder.

Für den ersten Hardwaretest sollte `fit_field_curvature` auf `false` bleiben.
Erst nach einem stabilen linearen Ebenenfit sollte der quadratische Fit
zugeschaltet werden.

## Goal-Parameter

| Feld | Einheit | Wirkung |
| --- | --- | --- |
| `center_z_mm` | mm | Mittelpunkt des Fokus-Scans. Der Wert muss innerhalb des zulässigen Achsbereichs liegen. |
| `half_range_mm` | mm | Halbe Scanbreite. Start ist `center_z_mm - half_range_mm`, Ende ist `center_z_mm + half_range_mm`. Ein größerer Wert hilft bei Fokusmaxima außerhalb des Scans, kostet aber zusätzliche Fahrzeit. |
| `step_mm` | mm | Abstand benachbarter Scanpositionen. Kleinere Schritte liefern mehr Stützstellen für den Peak-Fit, erhöhen aber Messdauer und Datenmenge. |
| `frames_per_position` | Bilder | Anzahl unterschiedlicher Kamerabilder pro Position. Pro ROI wird der Median der Fokuswerte gebildet. Mehr Bilder unterdrücken Rauschen und Ausreißer, verlängern aber die Messung. |
| `fit_field_curvature` | bool | `false`: robuste Ebene `z=c+a*x+b*y`. `true`: zusätzlich `x²`, `x*y` und `y²`, um Bildfeldwölbung zu modellieren. Die Winkel stammen weiterhin aus den linearen Koeffizienten am Bildzentrum. |
| `return_to_center` | bool | Fährt nach Erfolg sowie nach einem kontrollierten Abbruch zur Scanmitte zurück. Bei Cancellation wird zuerst ein Achsstopp angefordert. |

Gültigkeitsgrenzen des Action-Servers:

- `half_range_mm > 0`
- `step_mm > 0`
- mindestens drei und höchstens 1000 Scanpositionen
- `1 <= frames_per_position <= 100`
- es kann immer nur ein Goal gleichzeitig laufen

Falls der Scanbereich kein ganzzahliges Vielfaches von `step_mm` ist, wird die
positive Endposition zusätzlich als letzter Messpunkt angefügt.

## Feedback während des Scans

Mit `--feedback` werden folgende Felder ausgegeben:

| Feld | Bedeutung |
| --- | --- |
| `phase` | Aktueller Ablaufzustand: `moving`, `settling`, `acquiring`, `fitting` oder `returning`. |
| `z_index` | Index der aktuellen Scanposition. |
| `z_count` | Gesamtzahl der Scanpositionen. |
| `current_z_mm` | Aktuell angeforderte Fokusposition. |
| `frames_acquired` | Zahl der an dieser Position bereits akzeptierten Bilder. |
| `preliminary_valid_rois` | Vorläufige Zahl der ROIs mit ausreichend Kontrast und Gradientenenergie. Der vollständige Peak-Fit erfolgt erst nach dem Scan. |

Es werden nur unterschiedliche Bilder akzeptiert, deren ROS-Zeitstempel nach
dem bestätigten Ende der Achsbewegung und nach der Einpendelzeit liegt.

## Ergebnisfelder

| Feld | Einheit | Bedeutung |
| --- | --- | --- |
| `status` | Code | Ergebnisstatus aus der Statustabelle unten. |
| `status_message` | Text | Lesbare Zusammenfassung oder Diagnosezählung. |
| `tilt_x_deg` | Grad | Neigung der Fokusfläche entlang der Bild-X-Richtung. |
| `tilt_y_deg` | Grad | Neigung der Fokusfläche entlang der Bild-Y-Richtung. |
| `uncertainty_x_deg` | Grad | Konservative Standardunsicherheit für X. Sie ist das Maximum aus Online-Fitunsicherheit und empirischer Wiederholbarkeit. |
| `uncertainty_y_deg` | Grad | Konservative Standardunsicherheit für Y. |
| `detection_limit_x_deg` | Grad | 95-%-Nachweisgrenze `1.96 * uncertainty_x_deg`. |
| `detection_limit_y_deg` | Grad | 95-%-Nachweisgrenze `1.96 * uncertainty_y_deg`. |
| `center_focus_z_mm` | mm | Gefittete optimale Fokusposition im Bildzentrum. |
| `surface_rms_um` | µm | RMS der Residuen zwischen gültigen ROI-Fokuspositionen und gefitteter Fläche. Kleinere Werte bedeuten eine konsistentere Fläche. |
| `roi_total` | Anzahl | Gesamtzahl der Kandidaten-ROIs; im adaptiven Modus deutlich mehr als 49. |
| `roi_valid`, `focus_valid_roi_count` | Anzahl | Alle Kandidaten mit gültigem Fokusfit. `roi_valid` behält damit seine historische Bedeutung. |
| `x_span_fraction` | Anteil | X-Spannweite der finalen Surface-Inlier relativ zum erkannten Target. |
| `y_span_fraction` | Anteil | Entsprechende Y-Spannweite der finalen Surface-Inlier. |
| `tilt_x_detectable` | bool | `true`, wenn `abs(tilt_x_deg)` mindestens der 95-%-Nachweisgrenze entspricht. |
| `tilt_y_detectable` | bool | Entsprechende Aussage für Y. |
| `within_tolerance_x` | bool | `true`, wenn der Betrag des X-Winkels innerhalb von `tolerance_x_deg` liegt. |
| `within_tolerance_y` | bool | Entsprechende Aussage für Y. |
| `resolution_limited_x` | bool | `true`, wenn der X-Winkel nicht sicher von null unterscheidbar ist. |
| `resolution_limited_y` | bool | Entsprechende Aussage für Y. |
| `decision_x`, `decision_y` | Text | Intervallbasierte Entscheidung: `PASS`, `FAIL`, `INCONCLUSIVE` oder bei ungültigem Ergebnis `INVALID`. |
| `surface_mae_um` | µm | Mittlerer Absolutbetrag der Flächenresiduen. |
| `surface_median_abs_um` | µm | Medianer Absolutbetrag; weniger ausreißerempfindlich als RMS. |
| `surface_max_abs_um` | µm | Größter Absolutbetrag eines gültigen ROI-Residuums. |
| `roi_surface_inliers`, `surface_inlier_count` | Anzahl | Ausgewählte ROIs, die nach dem robusten Flächenfit Inlier bleiben. |
| `roi_rejected_focus` | Anzahl | Ausschließlich Kandidaten mit `fit.valid == false`. |
| `roi_rejected_spatial` | Anzahl | Gültige Fokusfits, die wegen Support, Überlappung oder räumlicher Auswahl nicht verwendet wurden. |
| `roi_rejected_surface` | Anzahl | Ausgewählte ROIs, die als Surface-Outlier markiert wurden. |
| `roi_robust_outliers` | Anzahl | Gültige Fokus-ROIs, die der robuste Flächenfit stark heruntergewichtet hat. |
| `mean_peak_uncertainty_um` | µm | Mittelwert der endlich bestimmbaren ROI-Peakunsicherheiten. |
| `median_peak_uncertainty_um` | µm | Median derselben Unsicherheiten. |
| `evaluation_directory` | Pfad | Erzeugtes Laufverzeichnis im Evaluationsmodus, sonst leer. |
| `target_bbox_normalized` | Anteil | Erkannte beziehungsweise manuelle Targetbox `[xmin,ymin,xmax,ymax]`. |
| `target_coverage_fraction` | Anteil | Anteil strukturell zum Support gehörender Kandidaten. |
| `baseline_x_mm`, `baseline_y_mm` | mm | Tatsächliche physische Messbasis der finalen Surface-Inlier. |
| `candidate_roi_count` | Anzahl | Zahl aller dicht erzeugten Kandidaten. |
| `structurally_valid_candidate_count` | Anzahl | Kandidaten mit ausreichender lokaler Struktur vor Peak- und Raumauswahl. |
| `selected_roi_count` | Anzahl | Räumlich verteilte Kandidaten, die in den Flächenfit eingehen. |
| `surface_inlier_count` | Anzahl | Final beobachtbare Inlier nach robustem Flächenfit. |
| `design_condition_number` | – | Konditionszahl der skalierten Designmatrix der finalen Inlier. |

`detectable` und `within_tolerance` beantworten verschiedene Fragen:

- `detectable`: Ist der Winkel bei der aktuellen Messauflösung statistisch von
  null unterscheidbar?
- `within_tolerance`: Liegt der geschätzte Winkel innerhalb der konfigurierten
  technischen Toleranz?

`resolution_limited=true` ist kein Nachweis dafür, dass das Target orthogonal
steht. Es bedeutet nur, dass die Messung den Winkel nicht sicher auflösen kann.

## Ergebnisstatus

| Code | Name | Bedeutung und typische Reaktion |
| ---: | --- | --- |
| 0 | `OK` | Fit erfolgreich. Winkel, Unsicherheiten und Flags können ausgewertet werden. |
| 1 | `INSUFFICIENT_TEXTURE` | Zu viele ROIs sind schwarz, gesättigt oder kontrastarm. Beleuchtung, Targetposition, Belichtung und Livebild prüfen. |
| 2 | `INSUFFICIENT_COVERAGE` | Es gibt möglicherweise genügend gültige ROIs, aber ihre räumliche Verteilung erlaubt keine zuverlässige X-/Y-Ebene. Target über das Bild verteilen oder ROI-Geometrie prüfen. |
| 3 | `FOCUS_OUTSIDE_SCAN` | Zu viele Fokusmaxima liegen am Rand des Scans. `center_z_mm` korrigieren oder `half_range_mm` vergrößern. |
| 4 | `FIT_UNSTABLE` | Fokuskurven oder Flächenfit sind instabil beziehungsweise mehrdeutig. Schrittweite, Einpendelzeit, Bildzahl, Vibrationen und Targetstruktur prüfen. |
| 5 | `CANCELLED` | Goal wurde vom Client abgebrochen. Die Achse wird gestoppt und optional zur Mitte zurückgefahren. |
| 6 | `HARDWARE_TIMEOUT` | Achsservice fehlt, antwortet nicht oder die Zielposition wurde nicht rechtzeitig bestätigt. Achsnode und Service-Namespace prüfen. |
| 7 | `IMAGE_TIMEOUT` | Nicht genügend frische, eindeutig zeitgestempelte Bilder. Kameratopic, Framerate, Encoding und Zeitstempel prüfen. |

Ein fachlicher Fehlerstatus wie `INSUFFICIENT_TEXTURE` kann als regulär
beendetes Action-Goal zurückkommen. Maßgeblich ist deshalb immer das Feld
`result.status`, nicht nur der Transportzustand der Action.

## Koordinatensystem und Vorzeichen

Es gilt das ROS-Kamera-Koordinatensystem:

- Bild-X ist positiv nach rechts.
- Bild-Y ist positiv nach unten.
- Ein positiver `tilt_x_deg` bedeutet, dass die optimale Fokusposition nach
  rechts zunimmt.
- Ein positiver `tilt_y_deg` bedeutet, dass die optimale Fokusposition nach
  unten zunimmt.

Das Vorzeichen einer späteren mechanischen Korrektur hängt von der Montage der
Kamera und der Kippachsen ab. Die Action leitet daraus bewusst noch keinen
automatischen Stellbefehl ab.

## Laufzeitkonfiguration

Der normale Launch lädt die lokale Datei
`promoc_bringup/config/user_config.yaml`. `user_config.example.yaml` ist nur
eine Vorlage. Nach Änderungen an `user_config.yaml` muss `promoc_bringup` neu
gebaut werden, wenn kein Symlink-Install verwendet wird.

Aktuelles 3×-Beispiel:

```yaml
target_tilt:
  imaging_profile: ids_u3_3800cp_c_hq_myutron_ftv30_150_3x
  magnification: 3.0
  object_um_per_pixel: 0.8
  roi_rows: 7
  roi_cols: 7
  roi_width_fraction: 0.10
  roi_height_fraction: 0.10
  roi_margin_fraction: 0.08
  use_integral_image: true
  focus_metric: tenengrad
  peak_fit_method: quadratic
  surface_weighted: false
  surface_robust: true
  evaluation_enabled: false
  evaluation_focus_metrics: []
  bootstrap_iterations: 0
  settle_time_s: 0.15
  axis_timeout_s: 30.0
  image_timeout_s: 2.0
  axis_position_tolerance_mm: 0.01
  repeatability_x_deg: 0.002
  repeatability_y_deg: 0.002
  tolerance_x_deg: 0.05
  tolerance_y_deg: 0.05
```

`target_tilt.imaging_profile` lädt die gleichnamige Datei aus
`config/imaging_profiles`. Die eindeutige Hierarchie ist: interne Node-Defaults,
danach das Imaging-Profil und zuletzt einzelne Werte aus `user_config.yaml`.
Damit können lokale Kalibrierwerte gezielt Profilwerte überschreiben.

### Abbildungsmaßstab

| Parameter | Wirkung |
| --- | --- |
| `magnification` | Dokumentiert die verwendete Vergrößerung und dient als Fallback zur Berechnung des Objektmaßstabs, falls `object_um_per_pixel` fehlt. |
| `object_um_per_pixel` | Objektseitige Größe eines Bildpixels. Dieser Wert skaliert Pixelabstände in Millimeter und beeinflusst die berechneten Winkel direkt. Er muss für Kamera, Objektiv, Vergrößerung, Binning und ROI-Modus gemeinsam kalibriert werden. Er wird nicht aus `CameraInfo` abgeleitet. |

Ein zu großer Wert für `object_um_per_pixel` macht den berechneten Winkel zu
klein; ein zu kleiner Wert macht ihn zu groß.

### ROI-Geometrie

#### Adaptive Target- und ROI-Auswahl

| Parameter | Standard | Wirkung |
| --- | ---: | --- |
| `roi_selection_mode` | `auto_texture` | `auto_texture` erkennt den strukturierten Target-Support; `manual_bbox` begrenzt Kandidaten auf eine Benutzerbox; `fixed_grid` reproduziert das alte Raster. |
| `manual_target_bbox` | `[0,0,1,1]` | Normalisierte Box `[xmin,ymin,xmax,ymax]`; nur bei `manual_bbox`. Ungültige oder invertierte Boxen werden abgelehnt. |
| `candidate_roi_width_fraction` | 0.08 | Breite einer adaptiven Kandidaten-ROI relativ zum Bild. |
| `candidate_roi_height_fraction` | 0.08 | Höhe einer adaptiven Kandidaten-ROI relativ zum Bild. |
| `candidate_step_x_fraction` | 0.06 | Horizontaler Kandidatenschritt. Kleiner als die ROI-Breite bedeutet Überlappung. |
| `candidate_step_y_fraction` | 0.06 | Vertikaler Kandidatenschritt. |
| `minimum_structured_pixel_fraction` | 0.01 | Dichte Strukturroute: Mindestanteil signifikanter Gradientenpixel. Dünne Kanten können alternativ die Sparse-Edge-Route bestehen. |
| `structure_mad_multiplier` | 3.0 | Robuste Schwelle `Median + Faktor·MAD` für signifikante Gradienten. |
| `structure_energy_quantile` | 0.90 | Obere lokale Gradientenquantile als Ergänzung zur mittleren Energie. |
| `analysis_max_dimension_px` | 2048 | Maximale Kantenlänge des verkleinerten Analysebilds für Kontrast-, Schwarz-, Sättigungs- und Strukturdiagnostik. Das Fokusmaß selbst bleibt vollaufgelöst. |
| `sparse_contrast_quantile` | 0.999 | Erfasst dünne helle oder dunkle Linien, die in P99–P01 verschwinden würden. |
| `sparse_energy_quantile` | 0.995 | Top-Gradientenstatistik für wenige starke Kantenpixel. |
| `minimum_gradient_snr` | 6.0 | Mindestabstand der starken Gradienten vom lokalen Median/MAD-Rauschboden. |
| `minimum_connected_edge_pixels` | 6 | Mindestgröße der stärksten zusammenhängenden Kantenkomponente. |
| `minimum_connected_edge_span_fraction` | 0.12 | Mindestspannweite dieser Komponente relativ zur ROI; unterdrückt isolierte Hotpixel. |
| `support_closing_radius` | 1 | Morphologisches Schließen auf dem Kandidatenraster; verbindet kleine Lücken in Ring- und Gitterstrukturen. |
| `minimum_target_coverage_fraction` | 0.05 | Mindestanteil struktureller Kandidaten am Kandidatenraster. |
| `minimum_selected_rois` | 10 | Mindestzahl räumlich ausgewählter Fokus-ROIs. |
| `maximum_selected_rois` | 30 | Obergrenze; verhindert, dass viele überlappende ROIs denselben Bereich mehrfach gewichten. |

`auto_texture` benutzt keine Hough-Kreis-, Checkerboard- oder Grid-Erkennung.
Aus strukturell gültigen Kandidaten wird eine morphologisch bereinigte
Connected-Component-Region gebildet. Isolierte Außeninseln werden verworfen;
innere Komponenten innerhalb der Hauptregion bleiben für konzentrische Ringe
erhalten. Die Auswahl reserviert zuerst äußere X-/Y-Punkte, Targetquadranten und
Pflichtbins. Verbleibende Plätze werden deterministisch nach räumlichem Abstand
und Qualität ergänzt; ein abschließendes globales Qualitäts-Capping entfernt
die geometrische Grundabdeckung nicht mehr.

| Parameter | Standard | Wirkung |
| --- | ---: | --- |
| `roi_rows` | 7 | Zahl der Kandidatenzeilen. |
| `roi_cols` | 7 | Zahl der Kandidatenspalten. |
| `roi_width_fraction` | 0.10 | Breite jeder ROI als Anteil der Bildbreite. Größere ROIs liefern mehr Textur, können aber lokale Effekte mitteln und sich überlappen. |
| `roi_height_fraction` | 0.10 | Höhe jeder ROI als Anteil der Bildhöhe. |
| `roi_margin_fraction` | 0.08 | Abstand der äußeren ROI-Zentren vom Bildrand. Größere Werte ziehen das Raster zur Mitte und verringern die räumliche Hebelwirkung. |
| `use_integral_image` | `true` | Kompatibilitätsparameter. Die aktuelle speichersparende Implementierung verwendet unabhängig davon direkte Float64-ROI-Summen aus jeweils einer Float32-Fokuskarte und keine Vollbild-Integralbilder. |

Alle ROI-Angaben sind normiert und passen sich automatisch an die aktuelle
Bildgröße an. Ändern sich Bildgröße oder Encoding innerhalb eines Scans, wird
der Scan kontrolliert abgebrochen.

### Aufnahme und Achse

| Parameter | Standard | Wirkung |
| --- | ---: | --- |
| `settle_time_s` | 0.15 s | Wartezeit nach bestätigtem Erreichen jeder Achsposition. Bei Vibrationen erhöhen; unnötig große Werte verlängern jede Scanposition. |
| `axis_timeout_s` | 30.0 s | Maximale Wartezeit auf Achsservices, Serviceantworten und Zielposition. |
| `image_timeout_s` | 2.0 s | Maximale Wartezeit pro benötigtem frischem Bild. Bei niedriger Framerate oder langer Belichtung erhöhen. |
| `axis_position_tolerance_mm` | 0.01 mm | Zulässige Abweichung zwischen angeforderter und gemeldeter Achsposition. Zu klein kann reale Bewegungen fälschlich als Timeout markieren. |
| `axis_service_prefix` | `/promoc/linear_axis/lts300_x_axis` | Prefix der bestehenden Achsservices `move_absolute`, `get_operation_status`, `get_position` und `stop`. |
| `image_topic` | `image_raw` | Relativer Name des Bildtopics im Namespace des Action-Nodes. Der Standard-Launch setzt ihn auf `stream0/image_raw`. |
| `camera_info_topic` | `camera_info` | Relativer Name des optionalen CameraInfo-Topics. Der Standard-Launch setzt ihn auf `stream0/camera_info`. CameraInfo ersetzt nicht den kalibrierten Objektmaßstab. |

Die Bild- und CameraInfo-Topics sind relativ zum Kameranamespace. Im
Standard-Launch werden dadurch automatisch
`/promoc/promoc_camera/stream0/image_raw` und
`/promoc/promoc_camera/stream0/camera_info` verwendet.

### ROI-Qualität und Fokuskurven

Diese Expertparameter können ebenfalls unter `target_tilt` gesetzt werden:

| Parameter | Standard | Prüfung und Auswirkung |
| --- | ---: | --- |
| `min_contrast` | 0.015 | Mindestkontrast. Dichte Textur verwendet P99–P01; die Sparse-Edge-Route zusätzlich die konfigurierbaren äußersten Quantile für Linien mit weniger als 1 % Flächenanteil. |
| `max_black_fraction` | 0.98 | Maximal erlaubter Anteil von Pixeln kleiner/gleich 0.005. Verringern verwirft dunkle ROIs früher. |
| `max_saturated_fraction` | 0.98 | Maximal erlaubter Anteil von Pixeln größer/gleich 0.995. Verringern verwirft gesättigte ROIs früher. |
| `min_gradient_energy` | 0.00001 | Minimale mittlere Sobel-/Tenengrad-Energie. Erhöhen fordert stärkere Kantenstruktur. |
| `max_frame_cv` | 0.35 | Maximaler robuster Variationskoeffizient der Fokuswerte zwischen Bildern derselben Position. Verringern reagiert strenger auf Bewegung und Flackern. |
| `min_peak_prominence` | 0.03 | Minimale relative Abhebung des Fokusmaximums vom Kurvenuntergrund. Erhöhen verwirft flache oder mehrdeutige Peaks strenger. |
| `min_peak_curvature` | 0.000001 | Minimale negative Krümmung des lokalen Maximums. Erhöhen fordert einen schärfer definierten Fokuspeak. |
| `min_fit_r2` | 0.40 | Minimales lokales Bestimmtheitsmaß des quadratischen Peak-Fits. Erhöhen akzeptiert nur stärker parabelförmige Kurven. |
| `peak_half_window` | 2 | Zahl der Scanpunkte links und rechts des diskreten Maximums für den lokalen Peak-Fit. Standardmäßig werden bis zu fünf Punkte verwendet. |
| `focus_metric` | `tenengrad` | Aktives Fokusmaß: `tenengrad`, `modified_laplacian` oder `variance_laplacian`. Tenengrad bleibt der kompatible Produktionsstandard. |
| `peak_fit_method` | `quadratic` | Lokales Peakmodell: `quadratic` oder `gaussian`. Beide liefern einen Sub-Step-Peak und eine kovarianzbasierte Z-Unsicherheit. |
| `max_peak_uncertainty_um` | 100 | Verwirft einen ROI-Peak, wenn seine berechnete Standardunsicherheit diesen Wert überschreitet. Bei exakt drei Fitpunkten ist keine Kovarianz schätzbar; der Peak bleibt dann ungewichtet nutzbar. |

Schwarze oder strukturlose ROIs werden nicht interpoliert. Sie bleiben ungültig
und gehen nicht in den Flächenfit ein.

### Flächenfit, Gewichtung und Residuen

| Parameter | Standard | Wirkung |
| --- | ---: | --- |
| `surface_weighted` | `false` | Erzwingt auch bei `fixed_grid` Qualitätsgewichte. Die adaptiven Modi verwenden ihre begrenzten Qualitätsgewichte immer. |
| `surface_robust` | `true` | Aktiviert den Huber-IRLS-Fit. Ausreißer werden nicht heimlich gelöscht, sondern erhalten ein kleineres robustes Gewicht. |
| `huber_k` | 1.345 | Übergang zwischen quadratischer und linearer Huber-Verlustfunktion. Kleinere Werte reagieren strenger auf Ausreißer. |
| `weight_sigma_floor_um` | 0.5 | Untere Begrenzung für `sigma_z`, damit unrealistisch kleine Unsicherheiten kein extremes Gewicht erzeugen. |
| `weight_sigma_ceiling_um` | 100 | Obere Begrenzung für die Gewichtung; nicht bestimmbare Unsicherheiten werden konservativ mit diesem Wert behandelt. |
| `robust_outlier_weight_threshold` | 0.25 | ROI gilt in der Diagnose als Flächenausreißer, wenn sein Huber-Gewicht darunter liegt. Er bleibt mit seinem tatsächlichen Gewicht im Fit. |

Zusätzlich zum bisherigen `surface_rms_um` berechnet der Kern MAE, medianen
Absolutfehler und maximalen Absolutfehler. Pro ROI werden gemessener Peak,
Flächenprognose, Residuum sowie Basis-, Huber- und Gesamtgewicht exportiert.
Im adaptiven Modus ist `base_weight` das median-normalisierte und begrenzte
Produkt aus Peakunsicherheit, Prominenz, R², Krümmung, Frame-Stabilität und
Strukturpixelanteil. Der zugrunde liegende ROI-`quality_score` wird in der CSV
zusammen mit allen Einzelkriterien ausgegeben. Einen zusätzlichen opaken
Gesamtscore für die vollständige Messung gibt es bewusst nicht.

### Räumliche Beobachtbarkeit

| Parameter | Standard | Wirkung |
| --- | ---: | --- |
| `min_valid_rois` | 10 | Mindestzahl vollständig gültiger ROI-Fokusfits. Bei einem 7×7-Raster stehen maximal 49 zur Verfügung. |
| `min_span_fraction` | 0.50 | Geforderte Spannweite der gültigen ROI-Zentren sowohl in X als auch in Y relativ zur Bildgröße. |
| `min_quadrants` | 4 | Mindestzahl belegter Bildquadranten. Mit dem Standardwert müssen alle vier Quadranten gültige ROIs enthalten. |
| `max_design_condition` | 100.0 | Maximal erlaubte Konditionszahl der skalierten linearen Designmatrix. Kleinere Werte prüfen die Ebenenbeobachtbarkeit strenger. |
| `minimum_baseline_x_mm` | 0.25 mm | Minimale reale X-Messbasis der finalen ROIs. |
| `minimum_baseline_y_mm` | 0.25 mm | Minimale reale Y-Messbasis. |
| `minimum_spatial_bins_x` | 3 | Mindestzahl belegter X-Bereiche relativ zum erkannten Target. |
| `minimum_spatial_bins_y` | 3 | Mindestzahl belegter Y-Bereiche. Horizontale oder vertikale Linien scheitern dadurch kontrolliert. |
| `maximum_standardized_residual` | 3.5 | Zusätzliche Residuenprüfung für `surface_inlier`; nach Ausreißern wird die Beobachtbarkeit erneut bewertet. |

Eine große Zahl gültiger ROIs allein reicht nicht. Im adaptiven Modus beziehen
sich Spannweiten und Quadranten auf den erkannten Target-Support, während die
physischen Messbasen weiterhin in Millimetern geprüft werden. Ein kleines
Target kann daher nicht dieselbe Winkelunsicherheit wie ein sensorfüllendes
Target vortäuschen. Nach Surface-Outliern wird die Beobachtbarkeit erneut
geprüft; Messbasis und Konditionszahl im Ergebnis stammen aus diesen finalen
Inliern. Die Mindestbasis ist keine Genauigkeitsgarantie – eine kleinere Basis
vergrößert weiterhin die aus der Fitkovarianz gemeldete Winkelunsicherheit.

### Wiederholbarkeit und Toleranz

| Parameter | Standard | Wirkung |
| --- | ---: | --- |
| `repeatability_x_deg` | 0.002° | Empirische Standardabweichung wiederholter X-Messungen. Die ausgegebene Unsicherheit kann nie kleiner werden als dieser Wert. |
| `repeatability_y_deg` | 0.002° | Entsprechender Wert für Y. |
| `tolerance_x_deg` | 0.05° | Technische Toleranz für `within_tolerance_x`. |
| `tolerance_y_deg` | 0.05° | Technische Toleranz für `within_tolerance_y`. |

Die erweiterten Felder `decision_x` und `decision_y` sind aussagekräftiger als
die kompatibel beibehaltenen `within_tolerance_*`-Flags:

- `PASS`: das vollständige 95-%-Intervall liegt innerhalb der Toleranz.
- `FAIL`: das vollständige 95-%-Intervall liegt außerhalb der Toleranz.
- `INCONCLUSIVE`: das Intervall schneidet eine Toleranzgrenze.
- `INVALID`: der Scan bzw. Fit war nicht gültig.

Die Wiederholbarkeiten sollten aus realen Wiederholmessungen mit unverändertem
Aufbau bestimmt und nicht nur theoretisch gewählt werden.

## Diagnose- und Evaluationsmodus

Der Normalbetrieb hält weiterhin weder vollständige Bilder noch einen
Bildstapel im Speicher. Der optionale Evaluationsmodus speichert nur skalare
ROI-Fokuswerte und erzeugt nach dem Scan reproduzierbare Artefakte:

```yaml
target_tilt:
  evaluation_enabled: true
  evaluation_export_all_focus_curves: false
  evaluation_output_directory: ~/Dokumente/Messungen/tilt_evaluation
  evaluation_focus_metrics: [modified_laplacian, variance_laplacian]
  bootstrap_iterations: 200
  bootstrap_seed: 1729
```

Der produktionsnahe Standard ist `evaluation_enabled: false`. Bei Aktivierung
erhält jeder Lauf ein Verzeichnis `run_<UTC-Zeit>` mit `summary.json`,
`roi_data.csv`, `focus_curves.csv`, Kandidatenübersicht, koordinatenbasierter
Peak-/Residuen-Darstellung und einer 3D-Flächendarstellung. Einzelplots werden
standardmäßig nur für ausgewählte ROIs und je einen relevanten Ablehnungsgrund
geschrieben. `evaluation_export_all_focus_curves: true` ist ein langsamer
Debugmodus für wirklich alle Kandidaten. Die alternativen
Fokusmaße werden aus denselben aufgenommenen Bildern berechnet; die Achse wird
nicht erneut bewegt. `bootstrap_iterations: 0` deaktiviert Bootstrap im
Normalbetrieb. Bei aktiviertem Bootstrap werden pro Z-Position nur die
skalaren Frame-Scores mit Zurücklegen resampelt.

Bei `return_to_center: true` erfolgt die bestätigte Rückfahrt in einem gemeinsamen
Cleanup-Pfad vor jedem Diagnose- oder Plotexport – auch nach Cancellation,
Bildfehlern und Hardwarefehlern. Der Export bleibt bewusst synchron und erzeugt
damit keine unkontrollierten Hintergrundthreads; die Action gilt frühestens nach
erfolgreicher Rückfahrt als abgeschlossen.

Mehrere exportierte Läufe lassen sich zusammenfassen mit:

```bash
ros2 run camera_nodes target_tilt_repeatability \
  ~/Dokumente/Messungen/tilt_evaluation \
  --output ~/Dokumente/Messungen/tilt_repeatability \
  --reference-output ~/Dokumente/Messungen/tilt_reference.json
```

Das erzeugt `runs_summary.csv` und `repeatability.json` mit Mittelwert,
Standardabweichung und Spannweite der Winkel, Fokuslage, RMS-Residuen und
gültigen ROI-Zahl. `roi_repeatability.csv` und zwei Heatmaps zeigen zusätzlich,
welche ROIs bei Peaklage oder Flächenresiduum systematisch instabil sind.
`--reference-output` ist optional und mittelt die Flächenkoeffizienten der
unkorrigierten Läufe. Es verweigert gemischte Bildgrößen, Maßstäbe oder Modelle.

### Referenzfläche

`reference_surface_path` kann auf eine JSON-Referenzfläche (`plane` oder
`quadratic`) zeigen. Ihre Z-Werte werden vor dem Ziel-Flächenfit an denselben
ROI-Koordinaten subtrahiert. Der Estimator verweigert die Korrektur, wenn
Bildgröße oder `object_um_per_pixel` nicht exakt zum Referenzprofil passen.
Damit eine Referenz nicht unbemerkt auf eine andere Kamera-/Objektivkombination
angewendet wird, sollte die Datei zusätzlich Kamera, Optik und Datum im
`metadata`-Objekt dokumentieren.

## Unterstützte Bildformate

Die Action verarbeitet folgende ROS-Encodings:

- `mono8`
- `mono16`
- `rgb8`
- `bgr8`
- `bayer_rggb8`, `bayer_bggr8`, `bayer_gbrg8`, `bayer_grbg8`
- entsprechende Bayer-16-Encodings

Farbbilder werden standardmäßig über den Grünkanal ausgewertet. Gepacktes
Bayer12 wird bewusst nicht im Estimator entpackt. Der Kameranode muss es vor der
Übergabe in ein unterstütztes ROS-Image-Encoding überführen.

## rqt

Das in ROS 2 Humble installierte `rqt_action` ist nur ein
Action-Type-Browser. Es kann Goal-, Feedback- und Result-Typen anzeigen, aber
kein Goal senden. `rqt_service_caller` sollte nicht zum manuellen Aufruf der
internen Action-Services wie `.../_action/send_goal` verwendet werden.

Stattdessen kann der eigens dafür bereitgestellte
`estimate_target_tilt_service` direkt mit `rqt_service_caller` verwendet
werden. `ros2 action send_goal` bleibt verfügbar, wenn Feedback oder
Cancellation benötigt werden.

## Typische Scanprofile

### Schneller Funktionstest

```bash
ros2 action send_goal --feedback \
  /promoc/promoc_camera/estimate_target_tilt \
  promoc_assembly_interfaces/action/EstimateTargetTilt \
  "{center_z_mm: 284.985, half_range_mm: 0.05, step_mm: 0.01, frames_per_position: 3, fit_field_curvature: false, return_to_center: true}"
```

### Robuster Standardscan

```bash
ros2 action send_goal --feedback \
  /promoc/promoc_camera/estimate_target_tilt \
  promoc_assembly_interfaces/action/EstimateTargetTilt \
  "{center_z_mm: 284.985, half_range_mm: 0.1, step_mm: 0.01, frames_per_position: 5, fit_field_curvature: false, return_to_center: true}"
```

### Untersuchung der Bildfeldwölbung

```bash
ros2 action send_goal --feedback \
  /promoc/promoc_camera/estimate_target_tilt \
  promoc_assembly_interfaces/action/EstimateTargetTilt \
  "{center_z_mm: 284.985, half_range_mm: 0.1, step_mm: 0.01, frames_per_position: 5, fit_field_curvature: true, return_to_center: true}"
```

Die Werte `284.985 mm` sind nur ein Beispiel. Vor jedem realen Scan muss geprüft
werden, ob Mittelpunkt und Bereich zur aktuellen Targetposition sowie zum
zulässigen Fahrbereich der Achse passen.

## Fehlersuche

### Action wird nicht gefunden

```bash
source /home/pmlab/ros2_ws/install/setup.bash
ros2 node list
ros2 action list -t
```

Falls der Node fehlt, `promoc_assembly_interfaces`, `camera_nodes` und
`promoc_bringup` neu bauen und den normalen Launch neu starten.

### Goal wird sofort abgelehnt

Mögliche Ursachen:

- ungültige oder nicht endliche Scanwerte
- weniger als drei oder mehr als 1000 Scanpositionen
- null Bilder oder mehr als 100 Bilder pro Position
- ein anderer Tilt-Scan läuft bereits

### `IMAGE_TIMEOUT`

Prüfen:

```bash
ros2 topic hz /promoc/promoc_camera/stream0/image_raw

ros2 topic echo \
  /promoc/promoc_camera/stream0/image_raw \
  sensor_msgs/msg/Image \
  --once --field encoding
```

Danach Kameraverbindung, ROS-Zeitstempel, Belichtungszeit und
`image_timeout_s` prüfen.

### `HARDWARE_TIMEOUT`

```bash
ros2 service list -t | grep /promoc/linear_axis/lts300_x_axis
```

Der Achsnode muss mindestens `move_absolute`, `get_operation_status`,
`get_position` und für Cancellation `stop` bereitstellen.

### `INSUFFICIENT_TEXTURE`

- Livebild auf Schwarzbild oder Sättigung prüfen.
- Belichtung und Beleuchtung korrigieren.
- Sicherstellen, dass das USAF-/Grid-Target über genügend ROIs sichtbar ist.
- Erst danach Expertgrenzen wie `min_contrast` verändern.

### `FOCUS_OUTSIDE_SCAN`

- `center_z_mm` näher an den tatsächlichen Fokus setzen.
- Alternativ `half_range_mm` vorsichtig vergrößern.
- Dabei den zulässigen Achsbereich beachten.

### `INSUFFICIENT_COVERAGE`

- Target so positionieren, dass Struktur in allen Bildquadranten liegt.
- Schwarze oder gesättigte Bildbereiche vermeiden.
- ROI-Raster und Ränder prüfen.
- Nicht einfach nur `min_valid_rois` reduzieren; die X-/Y-Beobachtbarkeit muss
  erhalten bleiben.

### `FIT_UNSTABLE`

- `frames_per_position` erhöhen.
- `settle_time_s` bei Vibrationen erhöhen.
- `step_mm` verkleinern, wenn der Fokuspeak nur von sehr wenigen Punkten
  erfasst wird.
- Scanbereich und Targetstruktur kontrollieren.
- Zunächst `fit_field_curvature: false` verwenden.
