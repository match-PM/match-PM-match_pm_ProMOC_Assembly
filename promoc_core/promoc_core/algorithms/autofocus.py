"""
Hybrid Autofocus Algorithm mit Hysterese-Kompensation.

Dieses Modul implementiert einen Hybrid-Autofokus-Algorithmus mit:
1. Coarse Search: Linearer Scan mit großen Schritten
2. Fine Search: Verfeinerung um das Maximum
3. Hysterese-Kompensation: Unidirektionale Bewegung

WICHTIG - Hysterese-Problem:
============================
Linear-Achsen haben mechanische Hysterese (Spiel, Reibung).
Wenn man hin und her fährt, erhält man unterschiedliche Positionen
für die gleiche Sollposition.

    Vorwärts:  0 → 10mm  →  Fokus bei 5.0mm
    Rückwärts: 10 → 0mm  →  Fokus bei 4.8mm  ← Hysterese!

Lösung - Unidirektionale Bewegung:
==================================
    ┌─────────────────────────────────────────────────────────────┐
    │  ScanDirection.FORWARD                                       │
    │                                                             │
    │  Start bei Z_MIN, fahre nur nach oben                       │
    │  0mm ──────────────────────────────────────────────▶ 10mm   │
    │       Coarse Scan (große Schritte)                          │
    │       Fine Scan (kleine Schritte, gleiche Richtung)         │
    │                                                             │
    │  Für Fine Search: Zurück zum Start, dann vorwärts           │
    │  5mm ◀────────── 0mm ──────────────────────▶ 5mm           │
    │      (schnell)        (langsam, Messungen)                 │
    └─────────────────────────────────────────────────────────────┘
    
    ┌─────────────────────────────────────────────────────────────┐
    │  ScanDirection.BACKWARD                                      │
    │                                                             │
    │  Start bei Z_MAX, fahre nur nach unten                      │
    │  10mm ◀────────────────────────────────────────────── 0mm   │
    │        Coarse Scan (große Schritte)                         │
    │        Fine Scan (kleine Schritte, gleiche Richtung)        │
    └─────────────────────────────────────────────────────────────┘
    
    ┌─────────────────────────────────────────────────────────────┐
    │  ScanDirection.BIDIRECTIONAL (Hysterese-Messung)            │
    │                                                             │
    │  Führt beide Scans durch und vergleicht:                    │
    │  1. Forward:  0mm → 10mm  →  Fokus_fwd                     │
    │  2. Backward: 10mm → 0mm  →  Fokus_bwd                     │
    │  3. Hysterese = |Fokus_fwd - Fokus_bwd|                    │
    │                                                             │
    │  Wenn Hysterese < Toleranz: Kann ignoriert werden          │
    │  Sonst: Muss kompensiert werden                            │
    └─────────────────────────────────────────────────────────────┘

Usage:
======
    from promoc_core.algorithms.autofocus import HybridAutofocus, AutofocusConfig
    
    # Unidirektional (empfohlen):
    config = AutofocusConfig(
        z_min_mm=0.0,
        z_max_mm=10.0,
        scan_direction=ScanDirection.FORWARD
    )
    
    # Hysterese messen:
    config = AutofocusConfig(
        scan_direction=ScanDirection.BIDIRECTIONAL
    )
    result = autofocus.process_image(...)
    if result.finished:
        print(f"Hysterese: {result.hysteresis_mm:.3f}mm")

Classes:
    ScanDirection: Scan-Richtung (FORWARD, BACKWARD, BIDIRECTIONAL)
    AutofocusConfig: Konfigurationsparameter
    AutofocusResult: Ergebnis der Bildverarbeitung
    HybridAutofocus: Hauptalgorithmus
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Tuple, Callable
import math
import numpy as np

from .focus_metrics import laplacian_variance, tenengrad


class ScanDirection(Enum):
    """
    Scan-Richtung für den Autofokus.

    FORWARD: Von z_min nach z_max (eliminiert Hysterese)
    BACKWARD: Von z_max nach z_min (eliminiert Hysterese)
    BIDIRECTIONAL: Beide Richtungen (misst Hysterese)
    """
    FORWARD = auto()      # 0 → max
    BACKWARD = auto()     # max → 0
    BIDIRECTIONAL = auto()  # Beide Richtungen (Hysterese-Messung)


class FocusPhase(Enum):
    """
    Aktuelle Phase des Autofokus-Algorithmus.

    Phasen-Ablauf (unidirektional):
    ===============================
        IDLE → COARSE_SEARCH → FINE_REPOSITION → FINE_SEARCH → FINISHED

    Phasen-Ablauf (bidirektional):
    ==============================
        IDLE → COARSE_FORWARD → COARSE_BACKWARD → COMPARE → FINISHED
    """
    IDLE = auto()

    # Unidirektionale Phasen
    COARSE_SEARCH = auto()      # Grobe Suche in Scan-Richtung
    FINE_REPOSITION = auto()    # Zurückfahren zum Start des Fine-Bereichs
    FINE_SEARCH = auto()        # Feine Suche (gleiche Richtung wie Coarse)
    FINE_SEARCH_INIT = auto()   # Legacy: Golden Section Init

    # Bidirektionale Phasen (Hysterese-Messung)
    COARSE_FORWARD = auto()     # Vorwärts-Scan
    COARSE_BACKWARD = auto()    # Rückwärts-Scan
    COMPARE_RESULTS = auto()    # Ergebnisse vergleichen

    FINISHED = auto()


@dataclass
class AutofocusConfig:
    """
    Konfiguration für den Hybrid-Autofokus-Algorithmus.

    Attribute:
        z_min_mm: Minimale Z-Position in mm
        z_max_mm: Maximale Z-Position in mm
        coarse_step_mm: Schrittweite für grobe Suche
        fine_step_mm: Schrittweite für feine Suche
        fine_range_mm: Bereich um Maximum für Fine Search (±fine_range)
        fine_metric: Fokus-Metrik ('variance' oder 'tenengrad')
        coarse_metric: Fokus-Metrik für Coarse Search
        min_focus_score: Minimaler Score für gültigen Fokus
        scan_direction: Scan-Richtung (FORWARD, BACKWARD, BIDIRECTIONAL)
        hysteresis_threshold_mm: Ab welcher Hysterese wird gewarnt

    Hysterese-Kompensation:
    =======================
    - FORWARD/BACKWARD: Keine Hysterese (unidirektional)
    - BIDIRECTIONAL: Misst Hysterese und gibt sie im Ergebnis zurück
    """
    z_min_mm: float = 0.0
    z_max_mm: float = 10.0
    coarse_step_mm: float = 0.5
    fine_step_mm: float = 0.05          # NEU: Feine Schrittweite
    fine_range_mm: float = 1.5          # NEU: ±1.5mm um Coarse-Maximum
    fine_tolerance_mm: float = 0.01     # Legacy: Golden Section Toleranz
    fine_metric: str = 'tenengrad'
    coarse_metric: str = 'variance'
    min_focus_score: float = 100.0
    scan_direction: ScanDirection = ScanDirection.FORWARD  # NEU
    hysteresis_threshold_mm: float = 0.1  # NEU: Warnung ab 0.1mm Hysterese

    def validate(self) -> None:
        """Validiert die Konfigurationsparameter."""
        if self.z_min_mm >= self.z_max_mm:
            raise ValueError(
                f"z_min ({self.z_min_mm}) muss < z_max ({self.z_max_mm}) sein")
        if self.coarse_step_mm <= 0:
            raise ValueError(
                f"coarse_step muss positiv sein, ist {self.coarse_step_mm}")
        if self.fine_step_mm <= 0:
            raise ValueError(
                f"fine_step muss positiv sein, ist {self.fine_step_mm}")
        if self.fine_range_mm <= 0:
            raise ValueError(
                f"fine_range muss positiv sein, ist {self.fine_range_mm}")
        if self.fine_step_mm >= self.coarse_step_mm:
            raise ValueError(
                f"fine_step ({self.fine_step_mm}) sollte < coarse_step ({self.coarse_step_mm}) sein")


@dataclass
class AutofocusResult:
    """
    Ergebnis der Bildverarbeitung im Autofokus-Prozess.

    Attribute:
        finished: True wenn Autofokus abgeschlossen
        best_z_mm: Beste Z-Position (gültig wenn finished=True)
        next_z_mm: Nächste Z-Position (gültig wenn finished=False)
        phase: Aktuelle Phase des Algorithmus
        current_score: Fokus-Score des aktuellen Bildes
        best_score: Bester Fokus-Score bisher
        progress: Geschätzter Fortschritt 0.0 bis 1.0
        message: Lesbare Statusmeldung

        # Hysterese-Informationen (nur bei BIDIRECTIONAL):
        hysteresis_mm: Gemessene Hysterese in mm (None wenn nicht gemessen)
        forward_focus_mm: Fokusposition bei Vorwärts-Scan
        backward_focus_mm: Fokusposition bei Rückwärts-Scan
        hysteresis_significant: True wenn Hysterese > Threshold

        # Bewegungs-Hinweise:
        requires_repositioning: True wenn Achse repositioniert werden muss
        reposition_z_mm: Zielposition für Repositionierung
    """
    finished: bool = False
    best_z_mm: Optional[float] = None
    next_z_mm: Optional[float] = None
    phase: FocusPhase = FocusPhase.IDLE
    current_score: float = 0.0
    best_score: float = 0.0
    progress: float = 0.0
    message: str = ""

    # Hysterese-Messung (BIDIRECTIONAL)
    hysteresis_mm: Optional[float] = None
    forward_focus_mm: Optional[float] = None
    backward_focus_mm: Optional[float] = None
    hysteresis_significant: bool = False

    # Repositionierung (für unidirektionale Fine Search)
    requires_repositioning: bool = False
    reposition_z_mm: Optional[float] = None


@dataclass
class _FocusMeasurement:
    """Interne Klasse: Einzelne Fokus-Messung."""
    z_mm: float
    score: float


class HybridAutofocus:
    """
    Hybrid-Autofokus mit Hysterese-Kompensation.

    Der Algorithmus arbeitet in mehreren Phasen:

    Unidirektional (FORWARD/BACKWARD):
    ==================================
    1. Coarse Search: Linearer Scan in Scan-Richtung
    2. Fine Reposition: Zurück zum Start des Fine-Bereichs
    3. Fine Search: Feine Suche in gleicher Richtung

    Bidirektional (Hysterese-Messung):
    ==================================
    1. Coarse Forward: Scan von min nach max
    2. Coarse Backward: Scan von max nach min
    3. Compare: Ergebnisse vergleichen, Hysterese berechnen

    Warum unidirektional?
    =====================
    Linear-Achsen haben mechanische Hysterese. Wenn man immer
    in die gleiche Richtung fährt, wird diese eliminiert.

    Ablauf (FORWARD):
    =================
        ┌─────────────────────────────────────────────────────────┐
        │  Coarse Search: 0mm → 10mm                              │
        │  ════════════════════════════════▶                      │
        │           ↑ Maximum bei 5mm gefunden                    │
        │                                                         │
        │  Fine Reposition: 5mm → 3.5mm (kein Messen!)           │
        │  ◀══════════════                                        │
        │                                                         │
        │  Fine Search: 3.5mm → 6.5mm                            │
        │  ════════════════════════════════▶                      │
        │           ↑ Präzises Maximum bei 4.95mm                │
        └─────────────────────────────────────────────────────────┘

    Usage:
        # Unidirektional (empfohlen):
        config = AutofocusConfig(
            scan_direction=ScanDirection.FORWARD
        )
        af = HybridAutofocus(config)

        # Hysterese messen:
        config = AutofocusConfig(
            scan_direction=ScanDirection.BIDIRECTIONAL
        )
        af = HybridAutofocus(config)
        config = AutofocusConfig(z_min_mm=0, z_max_mm=10)
        af = HybridAutofocus(config)

        # Start search
        first_z = af.start()
        move_to_z(first_z)

        # Main loop
        while True:
            image = capture_image()
            result = af.process_image(current_z, image)

            if result.finished:
                print(f"Focus found at Z={result.best_z_mm:.3f}mm")
                break

            move_to_z(result.next_z_mm)
    """

    def __init__(self, config: AutofocusConfig):
        """
        Initialisiert den Autofokus-Algorithmus.

        Args:
            config: Autofokus-Konfigurationsparameter
        """
        config.validate()
        self.config = config
        self._reset_state()

    def _reset_state(self) -> None:
        """Setzt den internen Zustand für neue Suche zurück."""
        self._phase = FocusPhase.IDLE
        self._measurements: List[_FocusMeasurement] = []

        # Scan-Richtung
        self._scan_forward = (self.config.scan_direction !=
                              ScanDirection.BACKWARD)

        # Coarse Search State
        self._coarse_positions: List[float] = []
        self._coarse_index: int = 0

        # Fine Search State (unidirektional)
        self._fine_positions: List[float] = []
        self._fine_index: int = 0
        self._fine_start_z: float = 0.0  # Startposition für Fine Search
        self._fine_end_z: float = 0.0    # Endposition für Fine Search

        # Bidirektional: Ergebnisse beider Richtungen
        self._forward_measurements: List[_FocusMeasurement] = []
        self._backward_measurements: List[_FocusMeasurement] = []
        self._forward_best_z: float = 0.0
        self._backward_best_z: float = 0.0

        # Legacy: Golden Section State (für Abwärtskompatibilität)
        self._gs_a: float = 0.0
        self._gs_b: float = 0.0
        self._gs_c: float = 0.0
        self._gs_d: float = 0.0
        self._gs_fc: Optional[float] = None
        self._gs_fd: Optional[float] = None
        self._gs_waiting_for: Optional[str] = None

        # Best result tracking
        self._best_z: float = 0.0
        self._best_score: float = 0.0

    def start(self) -> float:
        """
        Startet eine neue Autofokus-Suche.

        Generiert Positionen basierend auf Scan-Richtung:
        - FORWARD:  z_min → z_max
        - BACKWARD: z_max → z_min
        - BIDIRECTIONAL: Startet mit Forward

        Returns:
            Erste Z-Position zu der gefahren werden soll
        """
        self._reset_state()

        # Positionen basierend auf Richtung generieren
        if self.config.scan_direction == ScanDirection.BIDIRECTIONAL:
            # Bidirektional: Starte mit Forward
            self._coarse_positions = self._generate_positions(forward=True)
            self._phase = FocusPhase.COARSE_FORWARD
        else:
            # Unidirektional
            forward = (self.config.scan_direction == ScanDirection.FORWARD)
            self._coarse_positions = self._generate_positions(forward=forward)
            self._phase = FocusPhase.COARSE_SEARCH

        self._coarse_index = 0
        return self._coarse_positions[0]

    def _generate_positions(self, forward: bool) -> List[float]:
        """
        Generiert Positionen für den Scan.

        Args:
            forward: True für min→max, False für max→min

        Returns:
            Liste von Z-Positionen
        """
        z_range = self.config.z_max_mm - self.config.z_min_mm
        num_steps = int(z_range / self.config.coarse_step_mm) + 1

        positions = [
            self.config.z_min_mm + i * self.config.coarse_step_mm
            for i in range(num_steps)
        ]

        # Letzte Position nicht über Maximum
        if positions[-1] > self.config.z_max_mm:
            positions[-1] = self.config.z_max_mm

        # Bei Rückwärts-Scan: Liste umkehren
        if not forward:
            positions = positions[::-1]

        return positions

    def process_image(self, current_z_mm: float, image: np.ndarray) -> AutofocusResult:
        """
        Verarbeitet ein Bild und bestimmt die nächste Aktion.

        Diese Methode wird für jedes aufgenommene Bild aufgerufen.
        Sie berechnet den Fokus-Score und gibt die nächste Position zurück.

        Args:
            current_z_mm: Aktuelle Z-Position in mm
            image: Aufgenommenes Bild an aktueller Position

        Returns:
            AutofocusResult mit nächster Aktion oder Endergebnis
        """
        if self._phase == FocusPhase.IDLE:
            return AutofocusResult(
                finished=False,
                next_z_mm=self.start(),
                phase=FocusPhase.COARSE_SEARCH,
                message="Starte Autofokus"
            )

        # Unidirektionale Phasen
        if self._phase == FocusPhase.COARSE_SEARCH:
            return self._process_coarse_unidirectional(current_z_mm, image)

        if self._phase == FocusPhase.FINE_REPOSITION:
            return self._process_fine_reposition(current_z_mm)

        if self._phase == FocusPhase.FINE_SEARCH:
            return self._process_fine_unidirectional(current_z_mm, image)

        # Bidirektionale Phasen
        if self._phase == FocusPhase.COARSE_FORWARD:
            return self._process_coarse_forward(current_z_mm, image)

        if self._phase == FocusPhase.COARSE_BACKWARD:
            return self._process_coarse_backward(current_z_mm, image)

        if self._phase == FocusPhase.COMPARE_RESULTS:
            return self._compare_bidirectional_results()

        # Legacy: Golden Section (für Abwärtskompatibilität)
        if self._phase == FocusPhase.FINE_SEARCH_INIT:
            return self._init_fine_search(current_z_mm, image)

        # Bereits fertig
        return AutofocusResult(
            finished=True,
            best_z_mm=self._best_z,
            phase=FocusPhase.FINISHED,
            best_score=self._best_score,
            progress=1.0,
            message="Autofokus abgeschlossen"
        )

    def _compute_metric(self, image: np.ndarray, metric_type: str) -> float:
        """Berechnet Fokus-Metrik für ein Bild."""
        if metric_type == 'variance':
            return laplacian_variance(image)
        elif metric_type == 'tenengrad':
            return tenengrad(image)
        else:
            raise ValueError(f"Unbekannte Metrik: {metric_type}")

    # ══════════════════════════════════════════════════════════════════════════
    # UNIDIREKTIONALE SUCHE (FORWARD/BACKWARD)
    # ══════════════════════════════════════════════════════════════════════════

    def _process_coarse_unidirectional(self, current_z_mm: float, image: np.ndarray) -> AutofocusResult:
        """
        Verarbeitet Bild während unidirektionaler Coarse-Suche.

        Fährt nur in eine Richtung (keine Hysterese).
        """
        # Fokus-Metrik berechnen
        score = self._compute_metric(image, self.config.coarse_metric)

        # Messung speichern
        self._measurements.append(
            _FocusMeasurement(z_mm=current_z_mm, score=score))

        # Bestes Ergebnis tracken
        if score > self._best_score:
            self._best_score = score
            self._best_z = current_z_mm

        # Fortschritt berechnen
        progress = (self._coarse_index + 1) / len(self._coarse_positions) * 0.5

        # Zur nächsten Position
        self._coarse_index += 1

        if self._coarse_index < len(self._coarse_positions):
            next_z = self._coarse_positions[self._coarse_index]
            return AutofocusResult(
                finished=False,
                next_z_mm=next_z,
                phase=FocusPhase.COARSE_SEARCH,
                current_score=score,
                best_score=self._best_score,
                progress=progress,
                message=f"Grobe Suche: {self._coarse_index}/{len(self._coarse_positions)}"
            )

        # Coarse Search fertig → Fine Search vorbereiten
        return self._prepare_fine_search_unidirectional()

    def _prepare_fine_search_unidirectional(self) -> AutofocusResult:
        """
        Bereitet unidirektionale Fine Search vor.

        Berechnet Fine-Bereich um Coarse-Maximum und generiert
        Positionen in der richtigen Scan-Richtung.
        """
        if not self._measurements:
            return AutofocusResult(
                finished=True,
                best_z_mm=self.config.z_min_mm,
                phase=FocusPhase.FINISHED,
                message="Keine Messungen gesammelt"
            )

        # Fine Search Bereich berechnen
        best_z = self._best_z
        forward = (self.config.scan_direction == ScanDirection.FORWARD)

        # Bereich: ±fine_range_mm um Maximum
        fine_start = max(self.config.z_min_mm, best_z -
                         self.config.fine_range_mm)
        fine_end = min(self.config.z_max_mm, best_z +
                       self.config.fine_range_mm)

        # Fine-Positionen generieren
        num_fine_steps = int((fine_end - fine_start) /
                             self.config.fine_step_mm) + 1
        self._fine_positions = [
            fine_start + i * self.config.fine_step_mm
            for i in range(num_fine_steps)
        ]

        # Bei Rückwärts-Scan: umkehren
        if not forward:
            self._fine_positions = self._fine_positions[::-1]

        self._fine_index = 0

        # Startposition für Fine Search
        reposition_target = self._fine_positions[0]

        # Müssen wir zuerst repositionieren?
        # Bei FORWARD: Wenn wir über dem Fine-Start sind
        # Bei BACKWARD: Wenn wir unter dem Fine-Start sind
        current_z = self._coarse_positions[-1]  # Letzte Coarse-Position

        if forward:
            need_reposition = current_z > reposition_target
        else:
            need_reposition = current_z < reposition_target

        if need_reposition:
            # Erst repositionieren (ohne Messung!)
            self._phase = FocusPhase.FINE_REPOSITION
            self._fine_start_z = reposition_target

            return AutofocusResult(
                finished=False,
                next_z_mm=reposition_target,
                phase=FocusPhase.FINE_REPOSITION,
                best_score=self._best_score,
                progress=0.5,
                message=f"Repositioniere zu {reposition_target:.2f}mm für Fine Search",
                requires_repositioning=True,
                reposition_z_mm=reposition_target
            )
        else:
            # Direkt mit Fine Search starten
            self._phase = FocusPhase.FINE_SEARCH
            return AutofocusResult(
                finished=False,
                next_z_mm=self._fine_positions[0],
                phase=FocusPhase.FINE_SEARCH,
                best_score=self._best_score,
                progress=0.5,
                message="Starte feine Suche"
            )

    def _process_fine_reposition(self, current_z_mm: float) -> AutofocusResult:
        """
        Verarbeitet Repositionierung vor Fine Search.

        WICHTIG: Hier wird NICHT gemessen! Nur Bewegung.
        """
        # Repositionierung abgeschlossen → Fine Search starten
        self._phase = FocusPhase.FINE_SEARCH
        self._fine_index = 0

        return AutofocusResult(
            finished=False,
            next_z_mm=self._fine_positions[0],
            phase=FocusPhase.FINE_SEARCH,
            best_score=self._best_score,
            progress=0.55,
            message="Repositionierung abgeschlossen, starte feine Suche"
        )

    def _process_fine_unidirectional(self, current_z_mm: float, image: np.ndarray) -> AutofocusResult:
        """
        Verarbeitet Bild während unidirektionaler Fine-Suche.

        Fährt nur in eine Richtung durch den Fine-Bereich.
        """
        # Fokus-Metrik berechnen
        score = self._compute_metric(image, self.config.fine_metric)

        # Messung speichern
        self._measurements.append(
            _FocusMeasurement(z_mm=current_z_mm, score=score))

        # Bestes Ergebnis tracken
        if score > self._best_score:
            self._best_score = score
            self._best_z = current_z_mm

        # Fortschritt: 50% (Coarse) + 50% (Fine)
        progress = 0.5 + (self._fine_index + 1) / \
            len(self._fine_positions) * 0.5

        # Zur nächsten Position
        self._fine_index += 1

        if self._fine_index < len(self._fine_positions):
            next_z = self._fine_positions[self._fine_index]
            return AutofocusResult(
                finished=False,
                next_z_mm=next_z,
                phase=FocusPhase.FINE_SEARCH,
                current_score=score,
                best_score=self._best_score,
                progress=progress,
                message=f"Feine Suche: {self._fine_index}/{len(self._fine_positions)}"
            )

        # Fine Search fertig
        self._phase = FocusPhase.FINISHED
        return AutofocusResult(
            finished=True,
            best_z_mm=self._best_z,
            phase=FocusPhase.FINISHED,
            best_score=self._best_score,
            progress=1.0,
            message=f"Fokus gefunden bei Z={self._best_z:.4f}mm"
        )

    # ══════════════════════════════════════════════════════════════════════════
    # BIDIREKTIONALE SUCHE (HYSTERESE-MESSUNG)
    # ══════════════════════════════════════════════════════════════════════════

    def _process_coarse_forward(self, current_z_mm: float, image: np.ndarray) -> AutofocusResult:
        """
        Verarbeitet Bild während Vorwärts-Scan (Bidirektional).
        """
        score = self._compute_metric(image, self.config.coarse_metric)

        self._forward_measurements.append(
            _FocusMeasurement(z_mm=current_z_mm, score=score))

        # Bestes Forward-Ergebnis tracken
        if not self._forward_measurements or score > max(m.score for m in self._forward_measurements[:-1] or [_FocusMeasurement(0, 0)]):
            self._forward_best_z = current_z_mm

        progress = (self._coarse_index + 1) / \
            len(self._coarse_positions) * 0.25

        self._coarse_index += 1

        if self._coarse_index < len(self._coarse_positions):
            next_z = self._coarse_positions[self._coarse_index]
            return AutofocusResult(
                finished=False,
                next_z_mm=next_z,
                phase=FocusPhase.COARSE_FORWARD,
                current_score=score,
                progress=progress,
                message=f"Vorwärts-Scan: {self._coarse_index}/{len(self._coarse_positions)}"
            )

        # Forward fertig → Backward starten
        # Bestes Forward-Ergebnis finden
        if self._forward_measurements:
            best_fwd = max(self._forward_measurements, key=lambda m: m.score)
            self._forward_best_z = best_fwd.z_mm

        # Positionen für Rückwärts-Scan generieren
        self._coarse_positions = self._generate_positions(forward=False)
        self._coarse_index = 0
        self._phase = FocusPhase.COARSE_BACKWARD

        return AutofocusResult(
            finished=False,
            next_z_mm=self._coarse_positions[0],
            phase=FocusPhase.COARSE_BACKWARD,
            progress=0.25,
            message="Vorwärts-Scan abgeschlossen, starte Rückwärts-Scan",
            forward_focus_mm=self._forward_best_z
        )

    def _process_coarse_backward(self, current_z_mm: float, image: np.ndarray) -> AutofocusResult:
        """
        Verarbeitet Bild während Rückwärts-Scan (Bidirektional).
        """
        score = self._compute_metric(image, self.config.coarse_metric)

        self._backward_measurements.append(
            _FocusMeasurement(z_mm=current_z_mm, score=score))

        progress = 0.25 + (self._coarse_index + 1) / \
            len(self._coarse_positions) * 0.25

        self._coarse_index += 1

        if self._coarse_index < len(self._coarse_positions):
            next_z = self._coarse_positions[self._coarse_index]
            return AutofocusResult(
                finished=False,
                next_z_mm=next_z,
                phase=FocusPhase.COARSE_BACKWARD,
                current_score=score,
                progress=progress,
                message=f"Rückwärts-Scan: {self._coarse_index}/{len(self._coarse_positions)}"
            )

        # Backward fertig → Ergebnisse vergleichen
        if self._backward_measurements:
            best_bwd = max(self._backward_measurements, key=lambda m: m.score)
            self._backward_best_z = best_bwd.z_mm

        self._phase = FocusPhase.COMPARE_RESULTS
        return self._compare_bidirectional_results()

    def _compare_bidirectional_results(self) -> AutofocusResult:
        """
        Vergleicht Forward- und Backward-Ergebnisse, berechnet Hysterese.
        """
        hysteresis = abs(self._forward_best_z - self._backward_best_z)
        is_significant = hysteresis > self.config.hysteresis_threshold_mm

        # Bestes Ergebnis: Durchschnitt oder besserer Score
        fwd_score = max(
            m.score for m in self._forward_measurements) if self._forward_measurements else 0
        bwd_score = max(
            m.score for m in self._backward_measurements) if self._backward_measurements else 0

        if fwd_score >= bwd_score:
            self._best_z = self._forward_best_z
            self._best_score = fwd_score
        else:
            self._best_z = self._backward_best_z
            self._best_score = bwd_score

        self._phase = FocusPhase.FINISHED

        if is_significant:
            message = (
                f"⚠️ Hysterese signifikant: {hysteresis:.3f}mm > {self.config.hysteresis_threshold_mm}mm\n"
                f"   Forward: {self._forward_best_z:.3f}mm, Backward: {self._backward_best_z:.3f}mm"
            )
        else:
            message = (
                f"✓ Hysterese vernachlässigbar: {hysteresis:.3f}mm\n"
                f"   Forward: {self._forward_best_z:.3f}mm, Backward: {self._backward_best_z:.3f}mm"
            )

        return AutofocusResult(
            finished=True,
            best_z_mm=self._best_z,
            phase=FocusPhase.FINISHED,
            best_score=self._best_score,
            progress=1.0,
            message=message,
            hysteresis_mm=hysteresis,
            forward_focus_mm=self._forward_best_z,
            backward_focus_mm=self._backward_best_z,
            hysteresis_significant=is_significant
        )

    # ══════════════════════════════════════════════════════════════════════════
    # CONTROL METHODS
    # ══════════════════════════════════════════════════════════════════════════

    def abort(self) -> AutofocusResult:
        """
        Abort the current autofocus search.

        Returns:
            Result with best position found so far
        """
        self._phase = FocusPhase.FINISHED

        return AutofocusResult(
            finished=True,
            best_z_mm=self._best_z if self._best_score > 0 else None,
            phase=FocusPhase.FINISHED,
            best_score=self._best_score,
            progress=1.0,
            message="Autofocus aborted"
        )

    def get_measurements(self) -> List[Tuple[float, float]]:
        """
        Get all measurements taken during search.

        Returns:
            List of (z_mm, score) tuples
        """
        return [(m.z_mm, m.score) for m in self._measurements]

    @property
    def phase(self) -> FocusPhase:
        """Current phase of the autofocus algorithm."""
        return self._phase

    @property
    def is_running(self) -> bool:
        """True if autofocus is currently running."""
        return self._phase not in (FocusPhase.IDLE, FocusPhase.FINISHED)
