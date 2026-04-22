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




error Notes

[camera_node-3] 1776859407.551151258: [promoc.camera_node] [INFO]	MTF measurement service called.
[camera_node-3] 1776859407.551658712: [promoc.camera_node] [INFO]	MTF capture: enabling scientific raw Bayer on the current stream.
[camera_node-3] 1776859407.552212746: [promoc.camera_node] [INFO]	MTF raw capture: current stream geometry 5536x3692 already matches requested geometry; skipping geometry switch.
[camera_node-3] 1776859409.153444138: [promoc.camera_node] [INFO]	MTF raw capture switch start: target=?x?, offset=(?,?), bin=?x?, pixfmt=BayerRG12 exp=30000.0us/30.000ms gain=1.0
[camera_node-3] 1776859409.154034582: [promoc.camera_node] [INFO]	Camera format switch: skipping unavailable optional keys ['color_transform_enable', 'gamma_enable']
[camera_driver_uv-1] 1776859409.282529672: [promoc.promoc_camera] [WARN]	(camera_frame_stream0) Frame error: ARV_BUFFER_STATUS_SIZE_MISMATCH
[camera_driver_uv-1] 1776859409.410356780: [promoc.promoc_camera] [WARN]	(camera_frame_stream0) Frame error: ARV_BUFFER_STATUS_SIZE_MISMATCH
[camera_driver_uv-1] 1776859409.533407371: [promoc.promoc_camera] [WARN]	(camera_frame_stream0) Frame error: ARV_BUFFER_STATUS_SIZE_MISMATCH
[camera_driver_uv-1] 1776859409.656181975: [promoc.promoc_camera] [WARN]	(camera_frame_stream0) Frame error: ARV_BUFFER_STATUS_SIZE_MISMATCH
[camera_driver_uv-1] 1776859409.779699221: [promoc.promoc_camera] [WARN]	(camera_frame_stream0) Frame error: ARV_BUFFER_STATUS_SIZE_MISMATCH
[camera_driver_uv-1] 1776859409.901019651: [promoc.promoc_camera] [WARN]	(camera_frame_stream0) Frame error: ARV_BUFFER_STATUS_SIZE_MISMATCH
[camera_driver_uv-1] 1776859410.022363950: [promoc.promoc_camera] [WARN]	(camera_frame_stream0) Frame error: ARV_BUFFER_STATUS_SIZE_MISMATCH
[camera_driver_uv-1] 1776859410.142687651: [promoc.promoc_camera] [WARN]	(camera_frame_stream0) Frame error: ARV_BUFFER_STATUS_SIZE_MISMATCH
[camera_driver_uv-1] 1776859410.265939610: [promoc.promoc_camera] [WARN]	(camera_frame_stream0) Frame error: ARV_BUFFER_STATUS_SIZE_MISMATCH
[camera_node-3] 1776859410.288875566: [promoc.camera_node] [INFO]	MTF raw capture switch applied: actual=5536x3692, offset=(?,?), bin=1x1, pixfmt=BayerRG12 exp=30000.0us/30.000ms gain=1.0 service=/promoc/promoc_camera/set_parameters
[camera_node-3] 1776859410.289373241: [promoc.camera_node] [INFO]	MTF raw capture readback OK: requested scientific state active.
[camera_node-3] 1776859410.289808366: [promoc.camera_node] [INFO]	MTF raw capture image: 5536x3692
[camera_driver_uv-1] 1776859410.386225691: [promoc.promoc_camera] [WARN]	(camera_frame_stream0) Frame error: ARV_BUFFER_STATUS_SIZE_MISMATCH
[camera_driver_uv-1] 1776859410.507400143: [promoc.promoc_camera] [WARN]	(camera_frame_stream0) Frame error: ARV_BUFFER_STATUS_SIZE_MISMATCH
[camera_driver_uv-1] 1776859410.632194394: [promoc.promoc_camera] [WARN]	(camera_frame_stream0) Frame error: ARV_BUFFER_STATUS_SIZE_MISMATCH
[camera_node-3] 1776859410.700642218: [promoc.camera_node] [INFO]	MTF measurement context: pixel_um=2.4000, pixel_source=request, objective=1x, mag=1.00x, coaxV=18.150, coaxI=0.180, auto_roi=yes
[camera_node-3] 1776859410.701508069: [promoc.camera_node] [ERROR]	MTF capture validation failed: [ImageProcessingError] Scientific MTF requires raw Bayer input, got encoding 'rgb8'. Next step: check the camera stream encoding and retry the measurement.. summary=/home/pmlab/Dokumente/Messungen/C.Sternberg/mtf_messungen/mtf_auto_20260422_140330/summary.csv, context=/home/pmlab/Dokumente/Messungen/C.Sternberg/mtf_messungen/mtf_auto_20260422_140330/context.csv
[camera_node-3] 1776859410.701868685: [promoc.camera_node] [INFO]	MTF format restore start: target=5536x3692, offset=(?,?), bin=1x1, pixfmt=RGB8 exp=30000.4us/30.000ms gain=1.0
[camera_driver_uv-1] 1776859410.769278030: [promoc.promoc_camera] [WARN]	(camera_frame_stream0) Frame error: ARV_BUFFER_STATUS_SIZE_MISMATCH
[camera_driver_uv-1] 1776859410.904186230: [promoc.promoc_camera] [ERROR]	/home/pmlab/ros2_ws/src/camera_aravis2/camera_aravis2/src/camera_aravis_node_base.cpp:334: arv-device-error-quark (Code 5): USB3Vision write_memory error (error). In setting value for feature 'BinningHorizontal'.
[camera_node-3] 1776859410.953938800: [promoc.camera_node] [WARN]	Failed to set BinningHorizontal=1: 
[camera_driver_uv-1] 1776859410.955175317: [promoc.promoc_camera] [ERROR]	/home/pmlab/ros2_ws/src/camera_aravis2/camera_aravis2/src/camera_aravis_node_base.cpp:334: arv-device-error-quark (Code 5): USB3Vision write_memory error (error). In setting value for feature 'BinningVertical'.
[camera_node-3] 1776859411.131166543: [promoc.camera_node] [WARN]	Failed to set BinningVertical=1: 
[camera_node-3] 1776859413.449740634: [promoc.camera_node] [INFO]	MTF format restore applied: actual=5536x3692, offset=(?,?), bin=1x1, pixfmt=RGB8 exp=30000.4us/30.000ms gain=1.0 service=/promoc/promoc_camera/set_parameters
[camera_node-3] 1776859413.451170498: [promoc.camera_node] [ERROR]	[CAM] Service error: [ImageProcessingError] Scientific MTF requires raw Bayer input, got encoding 'rgb8'. Next step: check the camera stream encoding and retry the measurement.
