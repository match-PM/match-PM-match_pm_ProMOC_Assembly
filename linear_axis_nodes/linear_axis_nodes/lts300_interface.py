"""
LTS300 Interface - Hardware-Abstraktion für Thorlabs Linearachse.

Dieses Modul kapselt alle Interaktionen mit der Thorlabs LTS300 Hardware
und bietet eine einheitliche Schnittstelle, unabhängig davon ob die echte
Hardware oder ein Simulator verwendet wird.

Funktionsweise (Driver-Auswahl):
================================
Das Interface wählt automatisch den passenden Driver:

    ┌─────────────────────────────────────────────────────────────┐
    │  use_sim_time = True?                                       │
    │     └── JA: SimulatedLinearAxisDriver                      │
    │         └── Für Tests und Entwicklung ohne Hardware         │
    │                                                             │
    │     └── NEIN: ThorlabsLTS300Driver                         │
    │         └── Für echte Hardware-Steuerung                    │
    └─────────────────────────────────────────────────────────────┘

Komponenten nach dem Laden:
===========================
- driver: Der ausgewählte Treiber (Simulation oder Hardware)
- is_connected: Verbindungsstatus

Verwendung:
===========
    # Mit echte Hardware:
    interface = Lts300Interface(logger, config)
    interface.connect()
    
    # Position abfragen:
    pos = interface.driver.get_position()
    
    # Bewegung ausführen:
    interface.driver.move_absolute(150.0)  # in mm
"""

from .drivers.simulated_linear_axis_driver import SimulatedLinearAxisDriver


class Lts300Interface:
    """
    Zentrale Schnittstelle für Thorlabs LTS300 Linearachsen-Kommunikation.

    Diese Klasse abstrahiert die Hardware-Ebene und ermöglicht:
    - Nahtloses Umschalten zwischen echter Hardware und Simulation
    - Einheitliche API für alle Bewegungsbefehle
    - Klare Fehlerbehandlung bei Verbindungsproblemen

    Attribute:
        driver: Der aktive Treiber (Simulation oder Hardware)
        is_connected (bool): True wenn verbunden

    Beispiel:
        >>> interface = Lts300Interface(logger, config)
        >>> if interface.connect():
        ...     pos = interface.driver.get_position()
        ...     interface.driver.move_absolute(100.0)
    """

    def __init__(self, logger, config):
        """
        Initialisiert das Interface und wählt den passenden Driver.

        Ablauf:
        -------
        1. Logger und Config speichern
        2. Basierend auf use_sim_time den Driver wählen:
           - True: SimulatedLinearAxisDriver
           - False: ThorlabsLTS300Driver (Import erst wenn nötig)

        Args:
            logger: ROS2-Logger für Log-Ausgaben
            config: Lts300Config mit allen Parametern
        """
        self.logger = logger
        self.config = config
        self.driver = None
        self.is_connected = False

        # Driver-Auswahl basierend auf Simulation/Hardware-Modus
        if self.config.use_sim_time:
            self.driver = SimulatedLinearAxisDriver()
            self.logger.info("Using basic simulation driver for LTS300")
        else:
            # Hardware-Driver nur importieren wenn wirklich benötigt
            from .drivers.thorlabs_lts300_driver import ThorlabsLTS300Driver
            self.driver = ThorlabsLTS300Driver(logger)
            self.logger.info("Using Thorlabs LTS300 hardware driver")

    def connect(self) -> bool:
        """
        Stellt Verbindung zum Gerät her.

        Ablauf:
        -------
        1. Verbindungsversuch je nach Modus:
           - Simulation: Einfacher Connect-Aufruf
           - Hardware: Verbindung über seriellen Port
        2. Bei Hardware: Seriennummer-Überprüfung
        3. Verbindungsstatus speichern

        Returns:
            True bei erfolgreicher Verbindung, False sonst
        """
        try:
            self.logger.info(
                f"Connecting to device with S/N {self.config.serial_number} on port {self.config.serial_port}...")

            if self.config.use_sim_time:
                # Simulation mode
                connected = self.driver.connect()
                if connected:
                    self.logger.info("Connected in simulation mode")
            else:
                # Hardware mode - pass port as parameter
                connected = self.driver.connect(port=self.config.serial_port)
                if connected:
                    # Verify serial number matches configuration
                    device_serial = self.driver.get_serial_number()
                    if device_serial != self.config.serial_number:
                        self.logger.warn(
                            f"Expected S/N {self.config.serial_number}, but device reports {device_serial}")
                    self.logger.info(
                        f"Connected to Thorlabs LTS300 (S/N: {device_serial})")

            self.is_connected = connected
            return connected

        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """
        Trennt die Verbindung zum Gerät sauber.

        Sollte beim Herunterfahren des Nodes aufgerufen werden.
        """
        if self.driver and self.is_connected:
            self.driver.disconnect()
            self.is_connected = False
            self.logger.info("Device disconnected")
