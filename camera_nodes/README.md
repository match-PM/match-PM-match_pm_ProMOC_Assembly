# camera_nodes

Die gepflegte Dokumentation fuer den Messstand liegt im Root-README:
[`../README.md`](../README.md).

Fuer dieses Paket sind dort vor allem die Abschnitte zu Architektur,
Konfiguration sowie `/promoc/camera/*` relevant.

## Target-Verkippung

`target_tilt_estimator` stellt pro Kameranamespace die Action
`EstimateTargetTilt` bereit. Im Standard-Launch lautet der Action-Name
`/promoc/promoc_camera/estimate_target_tilt`. Ein Scan wie im mathematischen
Prototypen wird so gestartet:

```bash
ros2 action send_goal --feedback \
  /promoc/promoc_camera/estimate_target_tilt \
  promoc_assembly_interfaces/action/EstimateTargetTilt \
  "{center_z_mm: 284.985, half_range_mm: 0.1, step_mm: 0.01, frames_per_position: 5, fit_field_curvature: true, return_to_center: true}"
```

Für einen einfachen Aufruf über `rqt_service_caller` stellt derselbe Node
außerdem `/promoc/promoc_camera/estimate_target_tilt_service` mit dem Typ
`promoc_assembly_interfaces/srv/EstimateTargetTilt` bereit. Dieser Service
sendet intern ein Goal an die Action; er dupliziert weder Scan- noch
Hardwarelogik. Die Action bleibt für Feedback und Cancellation erhalten.

Die Standardauswahl `roi_selection_mode: auto_texture` erzeugt ein dichtes
überlappendes Kandidatenraster und wählt musterunabhängig strukturierte,
räumlich verteilte ROIs. `manual_bbox` und der kompatible Modus `fixed_grid`
stehen als Alternativen zur Verfügung. Sämtliche Parameter und Diagnosefelder
sind in [`../ACTIONS.md`](../ACTIONS.md) beschrieben.

Die Runtime-Konfiguration folgt `Node-Defaults < target_tilt.imaging_profile <
user_config.yaml`. `roi_valid` zählt weiterhin alle gültigen Fokusfits;
`selected_roi_count` und `surface_inlier_count` beschreiben die nachfolgenden
Auswahlstufen. Bei aktivierter Rückfahrt wird die Achse immer vor dem optionalen
Evaluations-/Plotexport auf die Scanmitte zurückgeführt.

Änderungen an den Action-/Service-Resultfeldern ändern den ROSIDL-Typ. Nach
einem Update müssen daher `promoc_assembly_interfaces`, `camera_nodes`,
`promoc_bringup` sowie externe Clients neu gebaut und neu gesourct werden.

Der Messwert `z` bezeichnet dabei die Fokuskoordinate entlang der optischen
Achse. Die vorhandene Hardware-Schnittstelle dieses Repositories heißt aus
Kompatibilitätsgründen `lts300_x_axis`; der Action-Node verwendet ausschließlich
deren bestehende Services und lässt sich über `axis_service_prefix` umstellen.

Bildkoordinaten sind `+x` nach rechts und `+y` nach unten. Ein positiver
`tilt_x_deg` beziehungsweise `tilt_y_deg` bedeutet, dass die optimale
Fokusposition in dieser Bildrichtung zunimmt. Das Vorzeichen einer mechanischen
Kippachse hängt zusätzlich von der Montage ab und wird nicht automatisch
angesteuert.

`tilt_*_detectable=false` bedeutet nur, dass der Winkel unter der konservativen
95-%-Nachweisgrenze liegt; es ist kein Nachweis für Orthogonalität. Die separaten
Flags `within_tolerance_*` und `resolution_limited_*` erhalten diese
Unterscheidung.
