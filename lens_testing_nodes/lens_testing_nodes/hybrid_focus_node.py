#!/usr/bin/env python3
"""
Hybrid Autofokus Node für Bachelorarbeit Messstand.

Kombiniert zwei Suchstrategien:
1. Grob-Suche: Linearer Scan mit Varianz-Metrik (schnell)
2. Fein-Suche: Golden Section Search mit Tenengrad-Metrik (präzise)

Autor: [Dein Name]
Datum: Dezember 2025
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32, String, Bool
from std_srvs.srv import Trigger
from cv_bridge import CvBridge
import cv2
import numpy as np
import time
from enum import Enum
import math
from typing import Optional, Tuple, List

# Import ProMOC Services (optional, für echte Hardware)
try:
    from promoc_assembly_interfaces.srv import MoveAbsolute, GetPosition
    PROMOC_AVAILABLE = True
except ImportError:
    PROMOC_AVAILABLE = False


class FocusState(Enum):
    """Zustandsautomat für den Hybrid-Autofokus-Prozess."""
    IDLE = 0
    COARSE_SCAN_MOVE = 1      # Grob: Fahren
    COARSE_SCAN_CAPTURE = 2   # Grob: Messen
    PREPARE_FINE_SEARCH = 3   # Übergang: Intervall setzen
    FINE_SEARCH_MOVE = 4      # Fein (Golden Section): Fahren
    FINE_SEARCH_CAPTURE = 5   # Fein (Golden Section): Messen
    GOTO_BEST_POS = 6         # Zum finalen Fokus fahren
    WAITING_FOR_MTF = 7       # Warten auf MTF-Messung
    DONE = 8
    ERROR = 99


class HybridFocusNode(Node):
    """
    ROS2 Node für Hybrid-Autofokus.
    
    Kombiniert einen schnellen linearen Grob-Scan mit einer präzisen
    Golden-Section-Feinsuche für optimale Fokussierung.
    """

    def __init__(self):
        super().__init__('hybrid_focus_node')
        
        # ================================================================
        # Parameter deklarieren
        # ================================================================
        
        # Grob-Suche Parameter
        self.declare_parameter('scan_start', 0.0)
        self.declare_parameter('scan_end', 50.0)
        self.declare_parameter('coarse_step', 1.0)  # mm
        
        # Fein-Suche Parameter
        self.declare_parameter('fine_tolerance', 0.005)  # mm (5µm)
        self.declare_parameter('fine_search_range', 1.0)  # mm um Grob-Maximum
        
        # Timing Parameter
        self.declare_parameter('settle_time', 0.5)  # Sekunden
        self.declare_parameter('startup_delay', 2.0)  # Sekunden
        
        # ROI Parameter
        self.declare_parameter('roi_size', 250)  # Pixel (halbe Kantenlänge)
        
        # Topic/Service Namen
        self.declare_parameter('image_topic', '/camera/image_raw')
        self.declare_parameter('stage_topic', '/lts300/move_to')
        self.declare_parameter('use_promoc_services', False)
        self.declare_parameter('axis_service_prefix', '/lts300_z_axis')
        
        # Auto-Start
        self.declare_parameter('auto_start', True)
        
        # ================================================================
        # Parameter laden
        # ================================================================
        
        self.scan_start = self.get_parameter('scan_start').value
        self.scan_end = self.get_parameter('scan_end').value
        self.coarse_step = self.get_parameter('coarse_step').value
        self.fine_tolerance = self.get_parameter('fine_tolerance').value
        self.fine_search_range = self.get_parameter('fine_search_range').value
        self.settle_time = self.get_parameter('settle_time').value
        self.startup_delay = self.get_parameter('startup_delay').value
        self.roi_size = self.get_parameter('roi_size').value
        self.image_topic = self.get_parameter('image_topic').value
        self.stage_topic = self.get_parameter('stage_topic').value
        self.use_promoc_services = self.get_parameter('use_promoc_services').value
        self.axis_service_prefix = self.get_parameter('axis_service_prefix').value
        self.auto_start = self.get_parameter('auto_start').value
        
        # ================================================================
        # Interne Variablen
        # ================================================================
        
        self.state = FocusState.IDLE
        self.cv_bridge = CvBridge()
        self.last_move_time = 0.0
        self.current_image: Optional[np.ndarray] = None
        
        # Grob-Suche Daten
        self.coarse_results: List[Tuple[float, float]] = []  # [(pos, score), ...]
        self.current_coarse_pos = 0.0
        
        # Fein-Suche Daten (Golden Section)
        self.gs_a = 0.0  # Untere Grenze
        self.gs_b = 0.0  # Obere Grenze
        self.gs_c = 0.0  # Probe-Punkt 1 (links)
        self.gs_d = 0.0  # Probe-Punkt 2 (rechts)
        self.score_c: Optional[float] = None
        self.score_d: Optional[float] = None
        self.target_gs_point: Optional[str] = None  # 'c' oder 'd'
        
        # Ergebnis
        self.best_focus_position: Optional[float] = None
        self.best_focus_score: Optional[float] = None
        
        # ================================================================
        # ROS2 Publisher
        # ================================================================
        
        self.pub_status = self.create_publisher(
            String, '/autofocus/status', 10)
        self.pub_best_position = self.create_publisher(
            Float32, '/autofocus/best_position', 10)
        self.pub_current_score = self.create_publisher(
            Float32, '/autofocus/current_score', 10)
        self.pub_focus_complete = self.create_publisher(
            Bool, '/autofocus/complete', 10)
        
        # Stage Control (einfacher Modus)
        if not self.use_promoc_services:
            self.pub_stage = self.create_publisher(
                Float32, self.stage_topic, 10)
        
        # ================================================================
        # ROS2 Subscriber
        # ================================================================
        
        self.sub_cam = self.create_subscription(
            Image, self.image_topic, self._image_callback, 10)
        
        # ================================================================
        # ROS2 Services (Server)
        # ================================================================
        
        self.srv_start = self.create_service(
            Trigger, '/autofocus/start', self._srv_start_callback)
        self.srv_stop = self.create_service(
            Trigger, '/autofocus/stop', self._srv_stop_callback)
        self.srv_get_result = self.create_service(
            Trigger, '/autofocus/get_result', self._srv_get_result_callback)
        
        # ================================================================
        # ROS2 Services (Clients für ProMOC)
        # ================================================================
        
        if self.use_promoc_services and PROMOC_AVAILABLE:
            self.cli_move_absolute = self.create_client(
                MoveAbsolute, f'{self.axis_service_prefix}/move_absolute')
            self.cli_get_position = self.create_client(
                GetPosition, f'{self.axis_service_prefix}/get_position')
        
        # ================================================================
        # Logging
        # ================================================================
        
        self.get_logger().info("=" * 60)
        self.get_logger().info("Hybrid Autofokus Node gestartet")
        self.get_logger().info("=" * 60)
        self.get_logger().info(f"  Scan-Bereich: {self.scan_start} - {self.scan_end} mm")
        self.get_logger().info(f"  Grob-Schrittweite: {self.coarse_step} mm")
        self.get_logger().info(f"  Fein-Toleranz: {self.fine_tolerance * 1000} µm")
        self.get_logger().info(f"  Image Topic: {self.image_topic}")
        self.get_logger().info(f"  Stage Control: {'ProMOC Services' if self.use_promoc_services else self.stage_topic}")
        self.get_logger().info("=" * 60)
        
        # Auto-Start Timer
        if self.auto_start:
            self.get_logger().info(f"Auto-Start in {self.startup_delay}s...")
            self.create_timer(self.startup_delay, self._auto_start_callback)
        else:
            self.get_logger().info("Warte auf Start-Befehl: ros2 service call /autofocus/start std_srvs/srv/Trigger")
        
        self._publish_status("IDLE - Bereit")

    # ================================================================
    # Service Callbacks
    # ================================================================

    def _srv_start_callback(self, request, response):
        """Service: Autofokus starten."""
        if self.state == FocusState.IDLE:
            self._start_autofocus()
            response.success = True
            response.message = "Autofokus gestartet"
        elif self.state == FocusState.DONE:
            # Reset und neu starten
            self._reset()
            self._start_autofocus()
            response.success = True
            response.message = "Autofokus neu gestartet"
        else:
            response.success = False
            response.message = f"Autofokus läuft bereits (State: {self.state.name})"
        return response

    def _srv_stop_callback(self, request, response):
        """Service: Autofokus stoppen."""
        if self.state not in [FocusState.IDLE, FocusState.DONE]:
            self.state = FocusState.IDLE
            self._publish_status("STOPPED - Abgebrochen")
            response.success = True
            response.message = "Autofokus gestoppt"
        else:
            response.success = False
            response.message = "Autofokus nicht aktiv"
        return response

    def _srv_get_result_callback(self, request, response):
        """Service: Ergebnis abfragen."""
        if self.best_focus_position is not None:
            response.success = True
            response.message = f"Best Focus: {self.best_focus_position:.4f} mm (Score: {self.best_focus_score:.1f})"
        else:
            response.success = False
            response.message = "Noch kein Ergebnis verfügbar"
        return response

    # ================================================================
    # Interne Methoden
    # ================================================================

    def _auto_start_callback(self):
        """Timer-Callback für Auto-Start."""
        if self.state == FocusState.IDLE:
            self._start_autofocus()
        # Timer nur einmal ausführen
        self.destroy_timer(self._auto_start_callback)

    def _reset(self):
        """Reset aller Variablen für neuen Durchlauf."""
        self.state = FocusState.IDLE
        self.coarse_results = []
        self.current_coarse_pos = 0.0
        self.gs_a = 0.0
        self.gs_b = 0.0
        self.gs_c = 0.0
        self.gs_d = 0.0
        self.score_c = None
        self.score_d = None
        self.target_gs_point = None
        self.best_focus_position = None
        self.best_focus_score = None

    def _start_autofocus(self):
        """Starte den Autofokus-Prozess."""
        self.get_logger().info("━" * 50)
        self.get_logger().info("STARTE HYBRID-AUTOFOKUS")
        self.get_logger().info("━" * 50)
        self.get_logger().info("Phase 1: Grob-Suche (Linear Scan mit Varianz)")
        
        self._publish_status("COARSE_SCAN - Starte Grob-Suche")
        
        self.state = FocusState.COARSE_SCAN_MOVE
        self.current_coarse_pos = self.scan_start
        self._move_stage(self.current_coarse_pos)

    def _publish_status(self, status: str):
        """Status-Nachricht publishen."""
        msg = String()
        msg.data = status
        self.pub_status.publish(msg)

    def _move_stage(self, position: float):
        """Fahre Stage zu Position."""
        if self.use_promoc_services and PROMOC_AVAILABLE:
            # ProMOC Service nutzen
            request = MoveAbsolute.Request()
            request.axis_position = position
            future = self.cli_move_absolute.call_async(request)
            # Nicht blockieren, Status wird durch Callback aktualisiert
        else:
            # Einfacher Topic-basierter Modus
            msg = Float32()
            msg.data = float(position)
            self.pub_stage.publish(msg)
        
        self.last_move_time = time.time()

    def _get_roi(self, cv_img: np.ndarray) -> np.ndarray:
        """Extrahiere ROI aus Bildmitte."""
        h, w = cv_img.shape[:2]
        s = self.roi_size
        
        # Sicherstellen, dass ROI innerhalb des Bildes liegt
        y1 = max(0, h // 2 - s)
        y2 = min(h, h // 2 + s)
        x1 = max(0, w // 2 - s)
        x2 = min(w, w // 2 + s)
        
        return cv_img[y1:y2, x1:x2]

    # ================================================================
    # Fokus-Metriken
    # ================================================================

    def _metric_variance(self, img: np.ndarray) -> float:
        """
        Laplacian-Varianz Metrik (schnell, gut für Grob-Suche).
        
        Berechnet die Varianz des Laplacian-gefilterten Bildes.
        Höhere Werte = schärferes Bild.
        """
        laplacian = cv2.Laplacian(img, cv2.CV_64F)
        return float(laplacian.var())

    def _metric_tenengrad(self, img: np.ndarray) -> float:
        """
        Tenengrad Metrik (präzise, gut für Fein-Suche).
        
        Berechnet die Summe der quadrierten Gradienten.
        Höhere Werte = schärferes Bild.
        """
        gx = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = gx**2 + gy**2
        return float(np.sum(magnitude))

    def _metric_brenner(self, img: np.ndarray) -> float:
        """
        Brenner Gradient Metrik (Alternative).
        
        Einfache aber effektive Gradientenmetrik.
        """
        diff = np.diff(img.astype(np.float64), axis=1)
        return float(np.sum(diff**2))

    # ================================================================
    # Hauptlogik (Image Callback)
    # ================================================================

    def _image_callback(self, msg: Image):
        """Hauptlogik: Verarbeite eingehende Bilder."""
        
        # Ignorieren wenn inaktiv
        if self.state in [FocusState.IDLE, FocusState.DONE, FocusState.ERROR]:
            return
        
        # Warten bis Stage stabil steht
        elapsed = time.time() - self.last_move_time
        if elapsed < self.settle_time:
            return
        
        # Bild konvertieren
        try:
            if msg.encoding in ['mono8', 'mono16']:
                frame = self.cv_bridge.imgmsg_to_cv2(msg, "mono8")
            else:
                frame = self.cv_bridge.imgmsg_to_cv2(msg, "bgr8")
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        except Exception as e:
            self.get_logger().error(f"Bildkonvertierung fehlgeschlagen: {e}")
            return
        
        roi = self._get_roi(frame)
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PHASE 1: GROB-SUCHE (Linear Scan)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        if self.state == FocusState.COARSE_SCAN_MOVE:
            # Angekommen, jetzt messen
            self.state = FocusState.COARSE_SCAN_CAPTURE
            
        elif self.state == FocusState.COARSE_SCAN_CAPTURE:
            score = self._metric_variance(roi)
            
            # Score publishen
            score_msg = Float32()
            score_msg.data = float(score)
            self.pub_current_score.publish(score_msg)
            
            self.get_logger().info(
                f"[GROB] Pos: {self.current_coarse_pos:6.2f} mm | "
                f"Varianz: {score:12.1f}")
            
            self.coarse_results.append((self.current_coarse_pos, score))
            
            # Nächster Schritt?
            next_pos = self.current_coarse_pos + self.coarse_step
            if next_pos <= self.scan_end:
                self.current_coarse_pos = next_pos
                self.state = FocusState.COARSE_SCAN_MOVE
                self._move_stage(next_pos)
                self._publish_status(f"COARSE_SCAN - {next_pos:.1f}mm")
            else:
                # Grob-Suche abgeschlossen
                self.state = FocusState.PREPARE_FINE_SEARCH

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # ÜBERGANG: Setup für Golden Section Search
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        elif self.state == FocusState.PREPARE_FINE_SEARCH:
            # Maximum der Grob-Suche finden
            best_coarse = max(self.coarse_results, key=lambda x: x[1])
            best_pos, best_score = best_coarse
            
            self.get_logger().info("━" * 50)
            self.get_logger().info(f"Grob-Maximum: {best_pos:.2f} mm (Score: {best_score:.1f})")
            self.get_logger().info("Phase 2: Fein-Suche (Golden Section mit Tenengrad)")
            self.get_logger().info("━" * 50)
            
            # Such-Intervall definieren [a, b]
            self.gs_a = max(self.scan_start, best_pos - self.fine_search_range)
            self.gs_b = min(self.scan_end, best_pos + self.fine_search_range)
            
            # Golden Section Konstante
            inv_phi = (math.sqrt(5) - 1) / 2  # ≈ 0.618
            dist = self.gs_b - self.gs_a
            
            # Innere Punkte berechnen
            self.gs_c = self.gs_b - dist * inv_phi
            self.gs_d = self.gs_a + dist * inv_phi
            
            # Mit Punkt c starten
            self.score_c = None
            self.score_d = None
            self.target_gs_point = 'c'
            
            self.state = FocusState.FINE_SEARCH_MOVE
            self._move_stage(self.gs_c)
            self._publish_status(f"FINE_SEARCH - [{self.gs_a:.3f}, {self.gs_b:.3f}]")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PHASE 2: FEIN-SUCHE (Golden Section Search)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        elif self.state == FocusState.FINE_SEARCH_MOVE:
            self.state = FocusState.FINE_SEARCH_CAPTURE
            
        elif self.state == FocusState.FINE_SEARCH_CAPTURE:
            # Tenengrad für Fein-Suche
            score = self._metric_tenengrad(roi)
            
            # Score publishen
            score_msg = Float32()
            score_msg.data = float(score)
            self.pub_current_score.publish(score_msg)
            
            # Ergebnis speichern
            if self.target_gs_point == 'c':
                self.score_c = score
                current_pos = self.gs_c
            else:
                self.score_d = score
                current_pos = self.gs_d
            
            self.get_logger().info(
                f"[FEIN] Pos: {current_pos:.4f} mm | "
                f"Tenengrad: {score:15.1f} | "
                f"Intervall: [{self.gs_a:.4f}, {self.gs_b:.4f}]")

            # Haben wir beide Punkte gemessen?
            if self.score_c is not None and self.score_d is not None:
                inv_phi = (math.sqrt(5) - 1) / 2
                
                if self.score_c > self.score_d:
                    # Maximum liegt links (zwischen a und d)
                    self.gs_b = self.gs_d
                    self.gs_d = self.gs_c
                    self.score_d = self.score_c  # Score recyclen!
                    
                    # Neues c berechnen
                    self.gs_c = self.gs_b - (self.gs_b - self.gs_a) * inv_phi
                    self.score_c = None
                    self.target_gs_point = 'c'
                else:
                    # Maximum liegt rechts (zwischen c und b)
                    self.gs_a = self.gs_c
                    self.gs_c = self.gs_d
                    self.score_c = self.score_d  # Score recyclen!
                    
                    # Neues d berechnen
                    self.gs_d = self.gs_a + (self.gs_b - self.gs_a) * inv_phi
                    self.score_d = None
                    self.target_gs_point = 'd'

                # Abbruchbedingung prüfen
                width = self.gs_b - self.gs_a
                if width < self.fine_tolerance:
                    final_pos = (self.gs_a + self.gs_b) / 2
                    self.best_focus_position = final_pos
                    self.best_focus_score = max(self.score_c or 0, self.score_d or 0)
                    
                    self.get_logger().info("━" * 50)
                    self.get_logger().info(f"✓ FOKUS GEFUNDEN: {final_pos:.4f} mm")
                    self.get_logger().info(f"  Genauigkeit: ±{(width/2)*1000:.1f} µm")
                    self.get_logger().info("━" * 50)
                    
                    self.state = FocusState.GOTO_BEST_POS
                    self._move_stage(final_pos)
                    self._publish_status(f"GOTO_BEST - {final_pos:.4f}mm")
                    return

            # Weiter suchen
            if self.target_gs_point == 'c':
                self._move_stage(self.gs_c)
            else:
                self._move_stage(self.gs_d)
            
            self.state = FocusState.FINE_SEARCH_MOVE
            self._publish_status(f"FINE_SEARCH - [{self.gs_a:.4f}, {self.gs_b:.4f}]")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PHASE 3: FINALE POSITION
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        elif self.state == FocusState.GOTO_BEST_POS:
            # Finale Position erreicht
            self.get_logger().info("Finale Position erreicht.")
            
            # Ergebnis publishen
            pos_msg = Float32()
            pos_msg.data = float(self.best_focus_position)
            self.pub_best_position.publish(pos_msg)
            
            complete_msg = Bool()
            complete_msg.data = True
            self.pub_focus_complete.publish(complete_msg)
            
            self._publish_status(f"DONE - Fokus bei {self.best_focus_position:.4f}mm")
            self.state = FocusState.DONE
            
            self.get_logger().info("=" * 50)
            self.get_logger().info("AUTOFOKUS ABGESCHLOSSEN")
            self.get_logger().info(f"  Beste Position: {self.best_focus_position:.4f} mm")
            self.get_logger().info(f"  Anzahl Grob-Messungen: {len(self.coarse_results)}")
            self.get_logger().info("=" * 50)


def main(args=None):
    rclpy.init(args=args)
    node = HybridFocusNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down...")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
