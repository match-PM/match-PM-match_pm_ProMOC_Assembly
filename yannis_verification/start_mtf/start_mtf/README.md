

cd ros2_ws
source ~/.bashrc
ros2 launch promoc_bringup optical_measurement_system.launch.py
rqt
ros2 run rqt_image_view rqt_image_view 
ros2 run start_mtf run_mtf_client 



Kamera wechsel:
suche nach # Wechsel bei Kamera wechsel
guid: 'IDS Imaging Development Systems GmbH-1409f49a1e40-4103740992'
image_width: 4000 # Cam2
image_height: 3000 # Cam2
pixelsize: 2.4  # µm
sensor_resolution_h
sensor_width_mm
nyquist_frequency
save and build


MTF Messung:
(roi ermitteln)
Autofoucs roi
in mtf_automated_client
Messbereich anpassen
colcon build --packages-select start_mtf
ros2 run start_mtf run_mtf_client 
Dateien verschieben!

Anschließend: (kann auch mehrere Ordner)
ros2 run camera_nodes mtf_batch_analyze --input ~/"Dokumente/Messungen/Yannis Wesser/Messungen" --recursive --delete-npy



Für Visualisierung:
cd src/match-PM-match_pm_ProMOC_Assembly/yannis_verification/start_mtf/start_mtf/

python3 mtf_auswertung.py

Für Kombination der 5 MTF Messungen
python3 mtf_combined.py

Kamera
python3 mtf_combined_cam.py

Objektive + Umlnekkomponenten
python3 mtf_combined_o.py

Exposuretime
ros2 run start_mtf exposure_control

Verzeichnung:
Speicherpfad Anpassen!
colcon build --packages-select start_mtf
ros2 run start_mtf verzeichnung 

Verschiebung:


Noch schneller, wenn die Kanten-ROI schon bekannt ist und keine Quadrat-Suche
mehr laufen soll:

```bash
ros2 service call /promoc/camera/measure_mtf \
  promoc_assembly_interfaces/srv/MeasureMTF \
  "{measurement_mode: 'capture_only_direct', target_edge: 'any', roi_x: 120, roi_y: 240, roi_width: 220, roi_height: 120}"
```

Die spaetere Auswertung eines Capture-Ordners laeuft ohne Kamera:

```bash
ros2 run camera_nodes mtf_batch_analyze \
  --input ~/Dokumente/Messungen/MaxMustermann/mtf_messungen \
  --recursive --overwrite \
  --target-edge top --min-valid-edges 1
```

`--target-edge` ist optional (`top`, `right`, `bottom`, `left`) und waehlt die
gewollte Kante, wenn sie gueltige Samples hat. `--min-valid-edges 1` erlaubt
Teilresultate; die MTF-Werte werden pro Kante ueber alle gueltigen Samples im
Raw-Stack gemittelt. Die technische Analyzer-Winkelgrenze liegt bei `11°`,
waehrend die offizielle SOP-Bewertung weiter `3°...10°` verwendet. Zusaetzlich
entsteht eine `batch_summary.csv`. Nach der Offline-Auswertung werden die
`*_roi.png` als vergroesserte Review-Bilder aus dem Raw-Stack neu geschrieben;
der sichtbare Rahmen zeigt den tatsaechlich analysierten Streifen.