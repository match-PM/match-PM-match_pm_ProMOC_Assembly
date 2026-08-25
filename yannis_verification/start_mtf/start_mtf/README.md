

cd ros2_ws
source ~/.bashrc
# Kamera einmal in promoc_bringup/config/user_config.yaml auswaehlen:
# camera:
#   profile: ids_u3_3800cp_m_gl_r22
# Profil, Pixelgroesse und mono/green werden danach automatisch geladen.
ros2 launch promoc_bringup optical_measurement_system.launch.py

# Farbkamera: passendes Raw-Bayer-Profil waehlen und nur Gruen-Sensel nutzen
# ros2 launch promoc_bringup optical_measurement_system.launch.py \
#   camera_type:=ids_u3_3890cp_c_hq_r22
rqt
ros2 run rqt_image_view rqt_image_view 
ros2 run start_mtf run_mtf_client 



Kamerawechsel:
In `promoc_bringup/config/user_config.yaml` nur `camera.profile` auf eines der
Profile aus `promoc_bringup/config/cameras/README.md` setzen, danach neu starten.
Keine GUID-, Aufloesungs- oder Pixelgroessenwerte mehr von Hand umkommentieren.


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
