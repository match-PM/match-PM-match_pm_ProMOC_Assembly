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
  - `rqt_image_view`
- Standardablauf:
  - bei Bedarf `set_exposure`
  - dann `autofocus` mit `focus_mode=0`
  - dann `measure_mtf` zuerst mit `auto_roi=true`
  - nur falls noetig `measure_mtf` mit manueller ROI
  - fuer die Auswertung zuerst `summary.csv` oeffnen

## Weitere Details

- Die kanonische Benutzerkonfiguration ist `promoc_bringup/config/user_config.v2.example.yaml`.
- Wissenschaftliches Protokoll: `MTF_PROTOCOL.md`
- Vollstaendige Bedienanleitung: `README.md`


