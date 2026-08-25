# Kamera-Profile

Das aktive Profil wird in `../user_config.yaml` ausgewaehlt:

```yaml
camera:
  profile: ids_u3_3800cp_m_gl_r22
```

Beim normalen Start ist kein zusaetzliches Launch-Argument erforderlich:

```bash
ros2 launch promoc_bringup optical_measurement_system.launch.py
```

Verfuegbare Profile:

| Profil | Kamera | MTF-Kanal | Status |
|---|---|---|---|
| `ids_u3_3800cp_m_gl_r22` | U3-3800CP-M-GL Rev.2.2 | `mono` | aktiv, GUID vorhanden |
| `ids_u3_3800cp_c_hq_r22` | U3-3800CP-C-HQ Rev.2.2 | `green` | GUID aus Alt-Konfiguration |
| `ids_u3_3890cp_c_hq_r22` | U3-3890CP-C-HQ Rev.2.2 | `green` | GUID aus Alt-Konfiguration |
| `ids_ui_3280cp_c_hq_r2` | UI-3280CP-C-HQ Rev.2 | `green` | Referenz; uEye-Treiber fehlt |

`ids_u3_3800cp_hq` bleibt nur als veralteter Launch-Alias fuer das aktuelle
Monochromprofil erhalten.

Die allgemeine Beschreibung der Messstand-Konfiguration liegt im Root-README
und in [`../README.md`](../README.md).

Fuer jede physische Kamera gibt es damit eine eigene GUID, Sensorgeometrie,
Pixelgroesse, Raw-Pixelformat und MTF-Kanalauswahl. Insbesondere muessen diese
Werte zusammenpassen:

```yaml
# Monochromkamera
camera_params:
  pixel_format: Mono12
  mtf_capture_pixel_format: Mono12
mtf_params:
  analysis_channel: mono

# Farbkamera
camera_params:
  pixel_format: BayerRG12
  mtf_capture_pixel_format: BayerRG12
  mtf_capture_bayer_pattern: RGGB
mtf_params:
  analysis_channel: green
```

Der Launch-Override `mtf_analysis_channel:=mono|green|auto` ist fuer Tests und
Kontrollen gedacht. Das Kameraprofil bleibt die kanonische Einstellung.

Ein Profil kann fuer einen einzelnen Start weiterhin ueberschrieben werden:

```bash
ros2 launch promoc_bringup optical_measurement_system.launch.py \
  camera_type:=ids_u3_3890cp_c_hq_r22
```

Die UI-3280 ist eine Kamera der IDS-Software-Suite-Reihe. Der aktuell eingesetzte
`camera_aravis2`-Treiber unterstuetzt GenICam GigE Vision und USB3 Vision, nicht
den proprietaeren uEye-Pfad. Die Auswahl des UI-Profils endet deshalb bewusst
mit einer klaren Fehlermeldung, bis ein uEye-ROS-2-Treiber integriert wurde.

Hinweis zu den Bezeichnungen: Fuer die monochrome U3-3800 nennt IDS die
offizielle Variante `M-GL`; eine `M-HQ`-Variante ist dort nicht gelistet. Die
3890 wurde entsprechend der vorhandenen USB3-Vision-Konfiguration als `U3-3890`
aufgenommen.
