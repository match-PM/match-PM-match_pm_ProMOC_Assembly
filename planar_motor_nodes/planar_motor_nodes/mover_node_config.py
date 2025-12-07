"""
Node-Konfiguration für den Mover Service Node.

Diese Datei enthält die NodeConfig-Dataclass, die alle Konfigurationsparameter
des Mover-Nodes in einer übersichtlichen Struktur zusammenfasst.

Vorteile einer Dataclass:
=========================
1. Alle Parameter an einem Ort
2. Typ-Hints für bessere IDE-Unterstützung
3. Automatische __repr__ für Debug-Ausgaben
4. Einfaches Weitergeben als einzelnes Objekt

Standard-Parameter werden in mover_node.py via ROS-Parameter definiert
und können per Launch-File oder Kommandozeile überschrieben werden.
"""

import dataclasses


@dataclasses.dataclass
class NodeConfig:
    """
    Konfiguration für den MoverServiceNode.

    Alle Werte werden aus ROS-Parametern geladen und hier zusammengefasst.

    Attribute:
        use_mock (bool): True = Mock-Modus (ohne Hardware)
        xbot_id (int): Standard-XBot-ID (0)
        publish_rate (float): Position-Publish-Rate in Hz (10.0)
        pmc_ip (str): IP-Adresse des PMC-Controllers

        xy_tolerance (float): Toleranz für XY-Positionierung in Metern
        six_d_tolerance (float): Toleranz für 6DOF-Bewegungen in Metern

        x_min, x_max (float): X-Achsen-Grenzen in Metern
        y_min, y_max (float): Y-Achsen-Grenzen in Metern
        z_min, z_max (float): Z-Achsen-Grenzen in Metern

    Grenzen-Diagramm:
    -----------------

        y_max ─────────────────────
              │                   │
              │   Erlaubter      │
              │   Bereich         │
              │                   │
        y_min ─────────────────────
             x_min             x_max

    Beispiel:
        >>> config = NodeConfig(
        ...     use_mock=False,
        ...     xbot_id=0,
        ...     publish_rate=10.0,
        ...     pmc_ip="192.168.10.100",
        ...     xy_tolerance=0.001,
        ...     six_d_tolerance=0.001,
        ...     x_min=0.055, x_max=0.420,
        ...     y_min=0.055, y_max=0.180,
        ...     z_min=0.000, z_max=0.004
        ... )
        >>> print(config)
        NodeConfig(use_mock=False, xbot_id=0, ...)
    """
    # ── Allgemeine Einstellungen ──
    use_mock: bool          # Mock-Modus aktivieren
    xbot_id: int            # Standard-XBot-ID
    publish_rate: float     # Position-Updates pro Sekunde
    pmc_ip: str             # PMC-Controller IP-Adresse

    # ── Toleranzen (in Metern) ──
    xy_tolerance: float     # XY-Positioniergenauigkeit
    six_d_tolerance: float  # 6DOF-Positioniergenauigkeit

    # ── Bewegungsgrenzen (in Metern) ──
    x_min: float            # Minimale X-Position
    x_max: float            # Maximale X-Position
    y_min: float            # Minimale Y-Position
    y_max: float            # Maximale Y-Position
    z_min: float            # Minimale Z-Position (Levitation)
    z_max: float            # Maximale Z-Position (Levitation)
