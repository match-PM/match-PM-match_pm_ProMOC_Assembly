"""
Bildverarbeitungs-Algorithmen für Kamera-Node.

Dieses Modul enthält die CameraImageProcessing-Klasse mit allen
Algorithmen für MTF-Berechnung und Bildanalyse.

MTF-Berechnung (Modulation Transfer Function):
=============================================
Die MTF beschreibt, wie gut ein optisches System Kontrast
bei verschiedenen Frequenzen überträgt.

Berechnungs-Pipeline:
--------------------
    Eingabe: ROI mit Slanted Edge
         │
         ▼
    ┌─────────────────────────────────────────────────────────────┐
    │  1. ESF berechnen (Edge Spread Function)                    │
    │     ├── Kante im Bild finden                               │
    │     ├── Pixel auf Linie senkrecht zur Kante projizieren    │
    │     └── Intensitätsprofil = ESF                            │
    │                                                             │
    │  2. LSF berechnen (Line Spread Function)                    │
    │     └── LSF = Ableitung der ESF                            │
    │                                                             │
    │  3. MTF berechnen                                           │
    │     └── MTF = |FFT(LSF)| normalisiert                      │
    └─────────────────────────────────────────────────────────────┘

Slanted Edge Method (ISO 12233):
================================
Die Kante muss leicht schräg sein (ca. 5°), damit Sub-Pixel-
Informationen aus mehreren Zeilen extrahiert werden können.

    ┌───────────────────┐
    │▓▓▓▓▓▓░░░░░░░░░░░░│  ← Schräge Kante
    │▓▓▓▓▓▓▓░░░░░░░░░░░│
    │▓▓▓▓▓▓▓▓░░░░░░░░░░│
    │▓▓▓▓▓▓▓▓▓░░░░░░░░░│
    └───────────────────┘

Verwendung:
===========
    processor = CameraImageProcessing(logger)
    
    # MTF aus ROI berechnen:
    results = processor.calculate_mtf_from_roi(roi_image)
    
    # Ergebnis exportieren:
    processor.export_to_csv(results, "mtf_results.csv")
"""

import cv2
import numpy as np
import csv


class CameraImageProcessing:
    """
    Bildverarbeitungs-Algorithmen für MTF-Berechnung.

    Diese Klasse implementiert die Slanted Edge Method nach ISO 12233
    für die MTF-Berechnung und weitere Bildanalyse-Funktionen.

    Attribute:
        logger: ROS2-Logger für Ausgaben

    Hauptfunktionen:
        calculate_mtf_from_roi(): Berechnet MTF aus ROI mit Slanted Edge
        export_to_csv(): Exportiert MTF-Ergebnisse als CSV
    """

    def __init__(self, logger):
        """
        Initialisiert die Bildverarbeitungs-Klasse.

        Args:
            logger: ROS2-Logger für Log-Ausgaben
        """
        self.logger = logger

    # ══════════════════════════════════════════════════════════════════════════
    # MTF-BERECHNUNG
    # ══════════════════════════════════════════════════════════════════════════

    def calculate_mtf_from_roi(self, roi_image, oversample_factor=4):
        """
        Berechnet die MTF aus einem ROI mit Slanted Edge.

        Ablauf (Schritt für Schritt):
        =============================
        1. ESF (Edge Spread Function) berechnen
        2. LSF (Line Spread Function) aus ESF ableiten
        3. MTF als FFT der LSF berechnen

        Args:
            roi_image: Bildausschnitt mit schräger Kante
            oversample_factor: Faktor für Sub-Pixel-Analyse (Standard: 4)

        Returns:
            dict: {'frequency': array, 'mtf': array} oder None bei Fehler
        """
        esf = self._calculate_esf(roi_image, oversample_factor)
        if esf is None:
            self.logger.error("ESF calculation failed.")
            return None

        freq, mtf = self._calculate_lsf_and_mtf(esf, oversample_factor)

        return {'frequency': freq, 'mtf': mtf}

    def _calculate_esf(self, roi_image, oversample_factor):
        """
        Berechnet die Edge Spread Function (ESF) aus einem Slanted Edge ROI.

        Ablauf:
        -------
        1. In Graustufen konvertieren
        2. Kante mit Canny-Detektor finden
        3. Linie durch Kantenpunkte fitten
        4. Alle Pixel senkrecht zur Linie projizieren
        5. Intensitäten in Bins sammeln → ESF
        """
        if roi_image is None or roi_image.size == 0:
            return None

        # ── Schritt 1: In Graustufen konvertieren ──
        gray_roi = cv2.cvtColor(
            roi_image, cv2.COLOR_BGR2GRAY).astype(np.float64)

        # ── Schritt 2: Kante finden ──
        edges = cv2.Canny(np.uint8(gray_roi), 50, 150)
        points = np.argwhere(edges > 0)
        if len(points) < 10:
            return None  # Zu wenige Kantenpunkte

        # ── Schritt 3: Linie durch Kante fitten ──
        # OpenCV fitLine erwartet (x,y) Format
        points_xy = points[:, ::-1]
        [vx, vy, x0, y0] = cv2.fitLine(points_xy, cv2.DIST_L2, 0, 0.01, 0.01)
        angle = np.arctan2(vy, vx)

        # ── Schritt 4: Pixel auf senkrechte Linie projizieren ──
        min_dist, max_dist = -np.inf, np.inf
        distances = (points_xy[:, 0] - x0) * vy - (points_xy[:, 1] - y0) * vx
        min_dist, max_dist = np.min(distances), np.max(distances)

        num_bins = int(np.ceil(max_dist - min_dist) * oversample_factor)
        if num_bins <= 0:
            return None

        bin_sums = np.zeros(num_bins)
        bin_counts = np.zeros(num_bins)

        # Alle Pixel im ROI verarbeiten
        h, w = gray_roi.shape
        y_coords, x_coords = np.mgrid[:h, :w]
        all_points = np.vstack((x_coords.ravel(), y_coords.ravel())).T

        # Senkrechte Distanz für alle Punkte berechnen
        all_distances = (all_points[:, 0] - x0) * \
            vy - (all_points[:, 1] - y0) * vx
        all_intensities = gray_roi.ravel()

        # Bin-Index für jeden Punkt
        bin_indices = np.floor((all_distances - min_dist)
                               * oversample_factor).astype(int)

        # Punkte außerhalb des Bereichs filtern
        valid_mask = (bin_indices >= 0) & (bin_indices < num_bins)
        valid_indices = bin_indices[valid_mask]
        valid_intensities = all_intensities[valid_mask]

        # ── Schritt 5: Werte in Bins sammeln ──
        np.add.at(bin_sums, valid_indices, valid_intensities)
        np.add.at(bin_counts, valid_indices, 1)

        # Durchschnitt bilden → ESF
        valid_bins = bin_counts > 0
        esf = np.full(num_bins, np.nan)
        esf[valid_bins] = bin_sums[valid_bins] / bin_counts[valid_bins]

        # Leere Bins interpolieren
        if np.isnan(esf).any():
            x = np.arange(num_bins)
            not_nan = ~np.isnan(esf)
            esf = np.interp(x, x[not_nan], esf[not_nan])

        return esf

    def _calculate_lsf_and_mtf(self, esf, oversample_factor):
        """
        Berechnet LSF und MTF aus der ESF.

        Mathematischer Zusammenhang:
        ============================
            LSF = d/dx ESF       (Ableitung)
            MTF = |FFT(LSF)|     (Fourier-Transform)

        Args:
            esf: Edge Spread Function (1D Array)
            oversample_factor: Überabtastungsfaktor

        Returns:
            tuple: (freq, mtf) - Frequenz- und MTF-Arrays
        """
        # ── Schritt 1: LSF berechnen (Ableitung der ESF) ──
        lsf = np.diff(esf)
        # Normalisieren auf Summe = 1
        lsf = lsf / np.sum(lsf)

        # ── Schritt 2: Hamming-Fenster anwenden ──
        # Reduziert spektrales Lecken (Artefakte an Rändern)
        window = np.hamming(len(lsf))
        windowed_lsf = lsf * window

        # ── Schritt 3: MTF berechnen (FFT der LSF) ──
        fft_result = np.fft.fft(windowed_lsf)
        mtf = np.abs(fft_result)  # Betrag = MTF

        # ── Schritt 4: MTF auf DC-Wert normalisieren ──
        # MTF(0) = 1.0 per Definition
        mtf = mtf / mtf[0]

        # ── Schritt 5: Frequenzachse berechnen ──
        # Einheit: Zyklen/Pixel
        freq = np.fft.fftfreq(len(mtf), d=1.0/oversample_factor)

        # Nur positive Frequenzen bis Nyquist-Limit (0.5 cycles/pixel)
        positive_freq_mask = (freq >= 0) & (freq <= 0.5)
        freq = freq[positive_freq_mask]
        mtf = mtf[positive_freq_mask]

        return freq, mtf

    # ══════════════════════════════════════════════════════════════════════════
    # EXPORT
    # ══════════════════════════════════════════════════════════════════════════

    def export_to_csv(self, data_dict, filename):
        """
        Exportiert MTF-Daten in eine CSV-Datei.

        Args:
            data_dict: Dictionary mit Arrays (z.B. {'frequency': f, 'mtf': m})
            filename: Ausgabe-Dateiname

        Beispiel CSV-Ausgabe:
            frequency,mtf
            0.0,1.0
            0.1,0.95
            0.2,0.87
            ...
        """
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            # Header schreiben
            header = list(data_dict.keys())
            writer.writerow(header)
            # Datenzeilen schreiben
            rows = zip(*data_dict.values())
            writer.writerows(rows)
        self.logger.info(f"Daten erfolgreich exportiert nach {filename}")
