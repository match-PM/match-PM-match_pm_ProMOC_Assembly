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
