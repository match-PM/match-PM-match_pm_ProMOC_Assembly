"""Shared device and axis status values for ProMOC assembly nodes."""

from enum import IntEnum


class DeviceState(IntEnum):
    """Geraetezustand fuer alle ProMOC-Knoten.

    Zustandsuebergaenge:
    DISCONNECTED -> CONNECTING -> CONNECTED -> (NOT_READY | READY)
    READY <-> BUSY (waehrend Bewegung)
    Jeder Zustand -> ERROR | STOPPED
    STOPPED -> READY (nach Reset)
    """
    DISCONNECTED = 0  # Keine Verbindung
    CONNECTING = 1    # Verbindungsaufbau laeuft
    CONNECTED = 2     # Verbunden, noch nicht bereit
    NOT_READY = 3     # Verbunden, aber nicht einsatzbereit (z.B. ungehomed)
    READY = 4         # Bereit fuer Kommandos
    BUSY = 5          # Fuehrt Operation aus (Bewegung, Homing)
    STOPPED = 6       # Gestoppt (durch Stop-Kommando oder Sicherheitssystem)
    ERROR = 7         # Fehlerzustand


class AxisState(IntEnum):
    """Achsenzustand fuer Linearachsen (Thorlabs LTS300)."""
    UNKNOWN = 0   # Zustand unbekannt
    UNHOMED = 1   # Nicht gehomt (keine absolute Position bekannt)
    HOMING = 2    # Homing laeuft
    HOMED = 3     # Gehomt (absolute Positionen verfuegbar)
