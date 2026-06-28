"""Gemeinsame Kernbibliothek fuer alle ProMOC Assembly ROS-Pakete.

Enthaelt:
- error_codes: Numerische Fehlercodes (0-9999)
- error_handling: Decorator fuer automatische Fehlerbehandlung in ROS-Services
- promoc_exceptions: Exception-Hierarchie (ProMocError -> ConnectionError, MotionError, ...)
- status: DeviceState und AxisState Enums
- logging: TaggedLogger mit Prefix-Unterstuetzung ([PMC], [LTS], ...)
- motion: Hilfsfunktion zur Timeout-Berechnung fuer Bewegungen
- conversions: Einheitenumrechnungen (mm/m, rad/deg, ...)
- system_controller: Systemweites Monitoring und Stop-Koordination
"""
