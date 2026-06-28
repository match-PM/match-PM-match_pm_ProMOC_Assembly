"""Small tagged logger wrapper used by the ROS nodes."""

from typing import Any


class LogTags:
    """Zentrale Log-Tags zur Kategorisierung aller Log-Ausgaben.

    Jeder Knotentyp hat eigene Tags:
    - PMC: Planar Motor Controller
    - LTS: Linear Axis (Thorlabs LTS300)
    - CAM: Kamera
    - SYS/LAUNCH: System und Launch
    - MOCK: Simulation/Mock-Treiber
    """

    # Planar Motor
    PMC = "[PMC]"
    PMC_MOTION = "[PMC:MOTION]"
    PMC_CTRL = "[PMC:CTRL]"
    PMC_CONN = "[PMC:CONN]"

    # Linear Axis
    LTS = "[LTS]"
    LTS_MOVE = "[LTS:MOVE]"
    LTS_HOME = "[LTS:HOME]"
    LTS_CONN = "[LTS:CONN]"

    # Camera
    CAM = "[CAM]"
    CAM_AF = "[CAM:AF]"
    CAM_MTF = "[CAM:MTF]"
    CAM_IMG = "[CAM:IMG]"

    # System / Launch
    SYS = "[SYS]"
    LAUNCH = "[LAUNCH]"

    # Mock / Simulation
    MOCK = "[MOCK]"


class TaggedLogger:
    """Wrapper um ROS-Logger mit Prefix-Unterstuetzung.

    Jede Log-Nachricht wird mit einem Tag-Prefix versehen, z.B.:
    "[PMC] Verbindung hergestellt" oder "[LTS:MOVE] Bewegung gestartet".
    """

    def __init__(self, logger: Any, tag: str):
        self._logger = logger
        self._tag = tag

    def _format(self, msg: str) -> str:
        """Haengt den Tag vor jede Nachricht."""
        return f"{self._tag} {msg}"

    def debug(self, msg: str, *args, **kwargs) -> None:
        """Log a debug message."""
        self._logger.debug(self._format(msg), *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        """Log an info message."""
        self._logger.info(self._format(msg), *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        """Log a warning message."""
        self._logger.warning(self._format(msg), *args, **kwargs)

    def warn(self, msg: str, *args, **kwargs) -> None:
        """Log a warning message (alias for warning)."""
        self.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        """Log an error message."""
        self._logger.error(self._format(msg), *args, **kwargs)

    def fatal(self, msg: str, *args, **kwargs) -> None:
        """Log a fatal message."""
        self._logger.fatal(self._format(msg), *args, **kwargs)
