#!/usr/bin/env python3
"""
MTF (Modulation Transfer Function) Analyse Node.

Berechnet die MTF aus Kantenbild (Slanted Edge Method) nach ISO 12233.

Autor: [Dein Name]
Datum: Dezember 2025
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32, Float32MultiArray, String
from std_srvs.srv import Trigger
from cv_bridge import CvBridge
import cv2
import numpy as np
from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class MTFResult:
    """Ergebnis einer MTF-Messung."""
    mtf50: float           # Frequenz bei 50% Kontrast (lp/mm)
    mtf20: float           # Frequenz bei 20% Kontrast (lp/mm)
    mtf10: float           # Frequenz bei 10% Kontrast (lp/mm)
    frequencies: np.ndarray  # Frequenz-Array
    mtf_values: np.ndarray   # MTF-Werte
    esf: np.ndarray         # Edge Spread Function
    lsf: np.ndarray         # Line Spread Function
    edge_angle: float       # Erkannter Kantenwinkel (Grad)
    valid: bool             # Messung gültig?
    error_msg: str = ""


class MTFNode(Node):
    """
    ROS2 Node für MTF-Analyse.
    
    Berechnet die Modulationsübertragungsfunktion aus einem Kantenbild
    nach der Slanted Edge Methode (ISO 12233).
    """

    def __init__(self):
        super().__init__('mtf_node')
        
        # ================================================================
        # Parameter
        # ================================================================
        
        self.declare_parameter('image_topic', '/camera/image_raw')
        self.declare_parameter('pixel_size_um', 3.45)  # µm pro Pixel
        self.declare_parameter('roi_width', 200)
        self.declare_parameter('roi_height', 400)
        self.declare_parameter('oversample_factor', 4)
        self.declare_parameter('auto_detect_edge', True)
        self.declare_parameter('min_edge_angle', 2.0)   # Grad
        self.declare_parameter('max_edge_angle', 10.0)  # Grad
        
        # Parameter laden
        self.image_topic = self.get_parameter('image_topic').value
        self.pixel_size_um = self.get_parameter('pixel_size_um').value
        self.roi_width = self.get_parameter('roi_width').value
        self.roi_height = self.get_parameter('roi_height').value
        self.oversample_factor = self.get_parameter('oversample_factor').value
        self.auto_detect_edge = self.get_parameter('auto_detect_edge').value
        self.min_edge_angle = self.get_parameter('min_edge_angle').value
        self.max_edge_angle = self.get_parameter('max_edge_angle').value
        
        # ================================================================
        # Interne Variablen
        # ================================================================
        
        self.cv_bridge = CvBridge()
        self.current_image: Optional[np.ndarray] = None
        self.last_result: Optional[MTFResult] = None
        self.measurement_active = False
        
        # ================================================================
        # ROS2 Publisher
        # ================================================================
        
        self.pub_mtf50 = self.create_publisher(Float32, '/mtf/mtf50', 10)
        self.pub_mtf_curve = self.create_publisher(Float32MultiArray, '/mtf/curve', 10)
        self.pub_status = self.create_publisher(String, '/mtf/status', 10)
        
        # ================================================================
        # ROS2 Subscriber
        # ================================================================
        
        self.sub_cam = self.create_subscription(
            Image, self.image_topic, self._image_callback, 10)
        
        # ================================================================
        # ROS2 Services
        # ================================================================
        
        self.srv_measure = self.create_service(
            Trigger, '/mtf/measure', self._srv_measure_callback)
        self.srv_get_result = self.create_service(
            Trigger, '/mtf/get_result', self._srv_get_result_callback)
        
        # ================================================================
        # Logging
        # ================================================================
        
        self.get_logger().info("=" * 60)
        self.get_logger().info("MTF Analyse Node gestartet")
        self.get_logger().info("=" * 60)
        self.get_logger().info(f"  Pixel-Größe: {self.pixel_size_um} µm")
        self.get_logger().info(f"  ROI: {self.roi_width}x{self.roi_height} px")
        self.get_logger().info(f"  Oversampling: {self.oversample_factor}x")
        self.get_logger().info("=" * 60)
        self.get_logger().info("Warte auf Messung: ros2 service call /mtf/measure std_srvs/srv/Trigger")

    # ================================================================
    # Service Callbacks
    # ================================================================

    def _srv_measure_callback(self, request, response):
        """Service: MTF-Messung durchführen."""
        if self.current_image is None:
            response.success = False
            response.message = "Kein Bild verfügbar"
            return response
        
        self.get_logger().info("Starte MTF-Messung...")
        self.measurement_active = True
        
        try:
            result = self._compute_mtf(self.current_image)
            self.last_result = result
            
            if result.valid:
                # MTF50 publishen
                msg = Float32()
                msg.data = float(result.mtf50)
                self.pub_mtf50.publish(msg)
                
                response.success = True
                response.message = (
                    f"MTF50: {result.mtf50:.2f} lp/mm | "
                    f"MTF20: {result.mtf20:.2f} lp/mm | "
                    f"Kantenwinkel: {result.edge_angle:.1f}°"
                )
                
                self.get_logger().info(f"MTF-Messung erfolgreich: {response.message}")
                self._publish_status(f"OK - MTF50={result.mtf50:.2f} lp/mm")
            else:
                response.success = False
                response.message = f"MTF-Messung fehlgeschlagen: {result.error_msg}"
                self.get_logger().warn(response.message)
                self._publish_status(f"ERROR - {result.error_msg}")
                
        except Exception as e:
            response.success = False
            response.message = f"Fehler: {str(e)}"
            self.get_logger().error(response.message)
            self._publish_status(f"ERROR - {str(e)}")
        
        self.measurement_active = False
        return response

    def _srv_get_result_callback(self, request, response):
        """Service: Letztes Ergebnis abfragen."""
        if self.last_result is None:
            response.success = False
            response.message = "Keine Messung durchgeführt"
        elif self.last_result.valid:
            response.success = True
            response.message = (
                f"MTF50: {self.last_result.mtf50:.2f} lp/mm | "
                f"MTF20: {self.last_result.mtf20:.2f} lp/mm | "
                f"MTF10: {self.last_result.mtf10:.2f} lp/mm"
            )
        else:
            response.success = False
            response.message = f"Letzte Messung ungültig: {self.last_result.error_msg}"
        return response

    # ================================================================
    # Image Callback
    # ================================================================

    def _image_callback(self, msg: Image):
        """Bild speichern für Messung."""
        try:
            if msg.encoding in ['mono8', 'mono16']:
                self.current_image = self.cv_bridge.imgmsg_to_cv2(msg, "mono8")
            else:
                frame = self.cv_bridge.imgmsg_to_cv2(msg, "bgr8")
                self.current_image = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        except Exception as e:
            self.get_logger().error(f"Bildkonvertierung fehlgeschlagen: {e}")

    def _publish_status(self, status: str):
        """Status publishen."""
        msg = String()
        msg.data = status
        self.pub_status.publish(msg)

    # ================================================================
    # MTF Berechnung (Slanted Edge Method)
    # ================================================================

    def _compute_mtf(self, image: np.ndarray) -> MTFResult:
        """
        Berechne MTF nach Slanted Edge Method (ISO 12233).
        
        Schritte:
        1. ROI extrahieren mit Kante
        2. Kantenwinkel bestimmen
        3. Edge Spread Function (ESF) berechnen
        4. Line Spread Function (LSF) = Ableitung der ESF
        5. MTF = |FFT(LSF)|
        """
        
        # ROI aus Bildmitte extrahieren
        h, w = image.shape[:2]
        x1 = max(0, w // 2 - self.roi_width // 2)
        x2 = min(w, w // 2 + self.roi_width // 2)
        y1 = max(0, h // 2 - self.roi_height // 2)
        y2 = min(h, h // 2 + self.roi_height // 2)
        
        roi = image[y1:y2, x1:x2].astype(np.float64)
        
        # Kantenwinkel bestimmen
        edge_angle = self._detect_edge_angle(roi)
        
        if edge_angle is None:
            return MTFResult(
                mtf50=0, mtf20=0, mtf10=0,
                frequencies=np.array([]), mtf_values=np.array([]),
                esf=np.array([]), lsf=np.array([]),
                edge_angle=0, valid=False,
                error_msg="Keine Kante erkannt"
            )
        
        if abs(edge_angle) < self.min_edge_angle:
            return MTFResult(
                mtf50=0, mtf20=0, mtf10=0,
                frequencies=np.array([]), mtf_values=np.array([]),
                esf=np.array([]), lsf=np.array([]),
                edge_angle=edge_angle, valid=False,
                error_msg=f"Kantenwinkel zu klein: {edge_angle:.1f}° (min: {self.min_edge_angle}°)"
            )
        
        if abs(edge_angle) > self.max_edge_angle:
            return MTFResult(
                mtf50=0, mtf20=0, mtf10=0,
                frequencies=np.array([]), mtf_values=np.array([]),
                esf=np.array([]), lsf=np.array([]),
                edge_angle=edge_angle, valid=False,
                error_msg=f"Kantenwinkel zu groß: {edge_angle:.1f}° (max: {self.max_edge_angle}°)"
            )
        
        # ESF berechnen (überabgetastet)
        esf = self._compute_esf(roi, edge_angle)
        
        if len(esf) < 10:
            return MTFResult(
                mtf50=0, mtf20=0, mtf10=0,
                frequencies=np.array([]), mtf_values=np.array([]),
                esf=esf, lsf=np.array([]),
                edge_angle=edge_angle, valid=False,
                error_msg="ESF zu kurz"
            )
        
        # LSF = Ableitung der ESF
        lsf = np.diff(esf)
        
        # Hamming-Fenster anwenden (reduziert Leckage)
        window = np.hamming(len(lsf))
        lsf_windowed = lsf * window
        
        # MTF = |FFT(LSF)|
        fft_lsf = np.fft.fft(lsf_windowed)
        mtf = np.abs(fft_lsf[:len(fft_lsf)//2])
        
        # Normieren auf MTF(0) = 1
        if mtf[0] > 0:
            mtf = mtf / mtf[0]
        else:
            return MTFResult(
                mtf50=0, mtf20=0, mtf10=0,
                frequencies=np.array([]), mtf_values=mtf,
                esf=esf, lsf=lsf,
                edge_angle=edge_angle, valid=False,
                error_msg="MTF(0) = 0"
            )
        
        # Frequenzachse berechnen (lp/mm)
        # Oversampling berücksichtigen
        effective_pixel_size = self.pixel_size_um / self.oversample_factor  # µm
        sample_spacing = effective_pixel_size / 1000.0  # mm
        frequencies = np.fft.fftfreq(len(lsf_windowed), d=sample_spacing)[:len(mtf)]
        
        # MTF50, MTF20, MTF10 interpolieren
        mtf50 = self._find_mtf_frequency(frequencies, mtf, 0.5)
        mtf20 = self._find_mtf_frequency(frequencies, mtf, 0.2)
        mtf10 = self._find_mtf_frequency(frequencies, mtf, 0.1)
        
        return MTFResult(
            mtf50=mtf50,
            mtf20=mtf20,
            mtf10=mtf10,
            frequencies=frequencies,
            mtf_values=mtf,
            esf=esf,
            lsf=lsf,
            edge_angle=edge_angle,
            valid=True
        )

    def _detect_edge_angle(self, roi: np.ndarray) -> Optional[float]:
        """
        Erkenne Kantenwinkel mittels Hough-Transformation.
        """
        # Canny Edge Detection
        edges = cv2.Canny(roi.astype(np.uint8), 50, 150)
        
        # Hough Lines
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=50)
        
        if lines is None or len(lines) == 0:
            return None
        
        # Mittleren Winkel berechnen
        angles = []
        for line in lines:
            rho, theta = line[0]
            # Winkel in Grad (relativ zu vertikal)
            angle_deg = np.degrees(theta) - 90
            angles.append(angle_deg)
        
        # Median nehmen (robuster gegen Ausreißer)
        return float(np.median(angles))

    def _compute_esf(self, roi: np.ndarray, edge_angle: float) -> np.ndarray:
        """
        Berechne Edge Spread Function durch Projektion entlang der Kante.
        
        Überabtastung durch Ausnutzung des schrägen Kantenwinkels.
        """
        h, w = roi.shape
        
        # Projektion senkrecht zur Kante
        angle_rad = np.radians(edge_angle)
        
        # Für jede Zeile: Position der Kante bestimmen und Pixelwerte sammeln
        esf_points = []
        
        for row in range(h):
            # Offset durch Kantenneigung
            offset = row * np.tan(angle_rad)
            
            for col in range(w):
                # Position relativ zur Kante (überabgetastet)
                pos = (col - w/2 - offset) * self.oversample_factor
                esf_points.append((pos, roi[row, col]))
        
        # Sortieren nach Position
        esf_points.sort(key=lambda x: x[0])
        
        # Binning für gleichmäßige Abtastung
        positions = np.array([p[0] for p in esf_points])
        values = np.array([p[1] for p in esf_points])
        
        # Bins erstellen
        bin_edges = np.arange(positions.min(), positions.max(), 1)
        bin_indices = np.digitize(positions, bin_edges)
        
        # Mittelwert pro Bin
        esf = []
        for i in range(1, len(bin_edges)):
            mask = bin_indices == i
            if np.sum(mask) > 0:
                esf.append(np.mean(values[mask]))
        
        return np.array(esf)

    def _find_mtf_frequency(self, frequencies: np.ndarray, mtf: np.ndarray, 
                            threshold: float) -> float:
        """
        Finde Frequenz bei gegebenem MTF-Wert durch Interpolation.
        """
        # Nur positive Frequenzen
        mask = frequencies >= 0
        freq_pos = frequencies[mask]
        mtf_pos = mtf[mask]
        
        # Finde Übergang
        for i in range(len(mtf_pos) - 1):
            if mtf_pos[i] >= threshold > mtf_pos[i+1]:
                # Lineare Interpolation
                f1, f2 = freq_pos[i], freq_pos[i+1]
                m1, m2 = mtf_pos[i], mtf_pos[i+1]
                
                if m1 != m2:
                    freq = f1 + (threshold - m1) * (f2 - f1) / (m2 - m1)
                    return float(freq)
        
        # Threshold nicht erreicht
        return float(freq_pos[-1]) if len(freq_pos) > 0 else 0.0


def main(args=None):
    rclpy.init(args=args)
    node = MTFNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down...")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
