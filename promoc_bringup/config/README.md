# Messstand-Konfiguration

Dieser Ordner enthaelt nur noch die aktiv gepflegten Konfigurationsdateien fuer
den `messstand`-Branch.

## Aktiv genutzt

- `user_config.yaml`
  Lokale Nutzerdatei auf dem Labor-PC. Sie wird von
  `optical_measurement_system.launch.py` direkt geladen.
- `user_config.example.yaml`
  Kanonische Vorlage fuer `user_config.yaml`.
- `linear_axes_params.yaml`
  Startkonfiguration der festen Thorlabs-X-Achse `lts300_x_axis`.
- `cameras/*.yaml`
  Ein Profil pro physischer Kamera. Die Auswahl erfolgt ueber
  `camera.profile` in `user_config.yaml`; Details stehen in
  [`cameras/README.md`](cameras/README.md).
- `imaging_profiles/*.yaml`
  Kalibrierte Kombinationen aus Kamera, Objektiv und Abbildungsmaßstab für die
  Verkippungsmessung. `object_um_per_pixel` wird nicht aus `CameraInfo`
  abgeleitet.

## Bewusst nicht mehr gepflegt

- alte `ids_camera_params.yaml`-Kompatibilitaetsdateien
- mehrere konkurrierende User-Config-Vorlagen

Der offizielle Bedienpfad lautet deshalb:

1. `cp promoc_bringup/config/user_config.example.yaml promoc_bringup/config/user_config.yaml`
2. Unter `camera.profile` die angeschlossene Kamera auswaehlen.
3. `ros2 launch promoc_bringup optical_measurement_system.launch.py`
