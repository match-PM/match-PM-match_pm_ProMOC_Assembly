"""
Node-Konfiguration für den LTS300 Linearachsen-Node.

Diese Datei enthält die Lts300Config-Dataclass, die alle Konfigurationsparameter
des Linearachsen-Nodes in einer übersichtlichen Struktur zusammenfasst.

Parameter-Kategorien:
=====================

1. Verbindung:
   - use_sim_time: True für Simulation
   - serial_port: USB-Port (z.B. /dev/ttyUSB0)
   - serial_number: Geräte-ID für Identifikation
   - namespace: ROS2-Namespace

2. Sicherheit:
   - collision_threshold: Kollisionsschwelle in mm
   - max_position / min_position: Soft-Limits
   - max_single_move: Maximale Einzelbewegung

3. Timing:
   - homing_timeout: Maximale Zeit für Homing

4. Umrechnung:
   - velocity_conversion_factor: Geräteeinheiten → mm/s

Kollisionserkennung:
====================
Wenn die andere Achse (X oder Z) über collision_threshold ist,
werden Bewegungen blockiert um Kollisionen zu vermeiden.

    Z-Achse                            
       │                              
       │  Wenn Z > threshold:         
       │  X-Bewegung blockiert!       
       │                              
       └────────────── X-Achse
"""

import dataclasses


@dataclasses.dataclass
class Lts300Config:
    """
    Konfiguration für den LTS300 Linearachsen-Node.

    Alle Werte werden aus ROS-Parametern geladen.

    Attribute:
        use_sim_time (bool): True = Simulationsmodus
        serial_port (str): USB-Port (z.B. /dev/ttyUSB0)
        serial_number (str): Geräte-Seriennummer
        collision_threshold (float): Ab welcher Position der anderen Achse
            keine Bewegung mehr erlaubt ist (mm)
        namespace (str): ROS2-Namespace für Topics
        max_position (float): Oberes Soft-Limit (mm)
        min_position (float): Unteres Soft-Limit (mm)
        max_single_move (float): Maximale Einzelbewegung (mm)
        homing_timeout (float): Maximale Homing-Dauer (s)
        velocity_conversion_factor (float): Geräteeinheiten → mm/s

    Beispiel:
        >>> config = Lts300Config(
        ...     use_sim_time=False,
        ...     serial_port="/dev/ttyUSB0",
        ...     serial_number="12345678",
        ...     collision_threshold=50.0,
        ...     ...
        ... )
    """
    # ── Verbindung ──
    use_sim_time: bool          # Simulationsmodus aktivieren
    serial_port: str            # USB-Port für Hardware
    serial_number: str          # Geräte-Seriennummer
    namespace: str              # ROS2-Namespace

    # ── Sicherheit ──
    collision_threshold: float  # Kollisionsschwelle (mm)
    max_position: float         # Oberes Soft-Limit (mm)
    min_position: float         # Unteres Soft-Limit (mm)
    max_single_move: float      # Max. Einzelbewegung (mm)

    # ── Timing ──
    homing_timeout: float       # Max. Homing-Dauer (s)

    # ── Umrechnung ──
    # Basierend auf Messungen: 500 Geräteeinheiten ≈ 9.0 mm/s
    # 100 Geräteeinheiten ≈ 1.85 mm/s → Faktor ≈ 0.018
    velocity_conversion_factor: float = 0.018
