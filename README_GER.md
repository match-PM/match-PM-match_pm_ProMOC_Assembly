# README_GER

Diese Datei ist auf dem `messstand`-Branch nur noch eine kurze Weiterleitung.
Die gepflegte Dokumentation steht in [README.md](README.md).

## Messstand starten

Bei änderungen oder erstem start des Messtandes bitte die folgenden Schritte durchführen:

```bash
cd ros2_ws
colcon build --symlink-install 
source install/setup.bash
```

In jedem neuen Terminal zuerst:

```bash
source ~/.bashrc
```

Standardablauf:

```bash
# Terminal 1

ros2 launch promoc_bringup optical_measurement_system.launch.py

# Terminal 2
rqt

# Terminal 3
rqt_image_view
```

## Wichtige Hinweise

- Die kanonische Benutzerkonfiguration ist `promoc_bringup/config/user_config.v2.example.yaml`.
- Die relevante Kamera-API des Messstands ist auf `autofocus`, `measure_mtf` und `set_exposure` reduziert.
- MTF-Ergebnisse liegen pro Messung in einem Run-Ordner mit `summary.csv`, `context.csv` und pro Kante benannten Exportdateien.
- Das wissenschaftliche Messprotokoll fuer Vergleichsmessungen steht in `MTF_PROTOCOL.md`.

Fuer alle weiteren Details bitte direkt `README.md` verwenden.


