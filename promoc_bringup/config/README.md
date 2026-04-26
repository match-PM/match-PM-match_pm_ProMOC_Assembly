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
- `cameras/ids_u3_3800cp_hq.yaml`
  Aktives Kamera-Profil fuer die IDS U3-3800CP-HQ.

## Bewusst nicht mehr gepflegt

- weitere Kamera-Beispielprofile
- alte `ids_camera_params.yaml`-Kompatibilitaetsdateien
- mehrere konkurrierende User-Config-Vorlagen

Der offizielle Bedienpfad lautet deshalb:

1. `cp promoc_bringup/config/user_config.example.yaml promoc_bringup/config/user_config.yaml`
2. `ros2 launch promoc_bringup optical_measurement_system.launch.py`
