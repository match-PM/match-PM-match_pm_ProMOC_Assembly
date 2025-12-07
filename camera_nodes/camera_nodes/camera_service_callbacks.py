"""
Service Callbacks für Kamera-Node - Geschäftslogik für Bildverarbeitung.

Dieses Modul enthält die CameraServiceCallbacks-Klasse mit allen
ROS2-Service-Callbacks für Autofokus, MTF-Messung und ROI-Auswahl.

Architektur-Übersicht:
======================
    Service Request
         │
         ▼
    ┌─────────────────────────────────────────────────────────────┐
    │  CameraServiceCallbacks                                      │
    │  ├── Schärfe-Berechnung                                     │
    │  │   ├── _calculate_sharpness() → Laplacian/Tenengrad      │
    │  │   └── Nutzt promoc_core.algorithms                       │
    │  │                                                          │
    │  ├── select_roi_callback()                                  │
    │  │   └── Interaktive ROI-Auswahl + MTF-Berechnung          │
    │  │                                                          │
    │  ├── autofocus_callback()                                   │
    │  │   ├── Hybrid-Algorithmus:                               │
    │  │   │   1. Grobe Suche (linear)                          │
    │  │   │   2. Feine Suche (Golden Section)                   │
    │  │   └── Steuert Z-Achse für Fokus-Optimierung            │
    │  │                                                          │
    │  └── measure_mtf_callback()                                 │
    │      └── MTF-Messung nach ISO 12233 (Slanted Edge)         │
    └─────────────────────────────────────────────────────────────┘

Verfügbare Services:
====================
- select_roi_callback: Interaktive ROI-Auswahl und MTF-Berechnung
- autofocus_callback: Automatische Fokussierung mit Z-Achsen-Steuerung
- measure_mtf_callback: MTF-Messung eines Bildes
- manual_set_exposure_callback: Belichtungszeit manuell setzen

Autofokus-Algorithmus:
======================
Der Hybrid-Autofokus funktioniert in zwei Phasen:

    Phase 1: Grobe Suche
    ├── Fahre gesamten Bereich mit großen Schritten ab
    ├── Berechne Schärfe an jeder Position
    └── Finde ungefähres Maximum

    Phase 2: Feine Suche (Golden Section Search)
    ├── Konzentriere auf Bereich um Maximum
    ├── Teile Bereich nach goldenem Schnitt
    └── Konvergiere zum präzisen Fokuspunkt

Schärfe-Metriken:
=================
- Laplacian Variance: Standardmetrik, robust
- Tenengrad: Alternative für Kanten-reiche Bilder

Exception-Handling:
===================
- ImageProcessingError: Bildverarbeitungsfehler
- InvalidParameterError: Ungültige Eingabewerte
- ConfigurationError: Fehlende Konfiguration
- ServiceCallFailedError: Z-Achsen-Service nicht erreichbar
"""

import cv2
import rclpy
from promoc_assembly_interfaces.srv import MoveAbsolute, JogAxis
import time
import sys
import numpy as np
from promoc_core.promoc_exceptions import (
    ConnectionError,
    InvalidParameterError,
    ParameterValidationError,
    ServiceCallFailedError,
    ImageProcessingError,
    ConfigurationError,
    HardwareError
)
from promoc_core.algorithms import (
    laplacian_variance,
    tenengrad,
    HybridAutofocus,
    AutofocusConfig,
    FocusPhase,
    MTFAnalyzer,
    MTFConfig
)


class CameraServiceCallbacks:
    """
    Geschäftslogik für alle Camera-Services.

    Diese Klasse enthält die Callback-Funktionen für Autofokus,
    MTF-Messung und ROI-Auswahl. Sie ist von ROS2 entkoppelt
    und nutzt promoc_core für Algorithmen.

    Attribute:
        _node: Parent ROS2-Node
        _driver (CameraDriver): Kamera-Treiber (abstrakt)
        _mtf_analyzer (MTFAnalyzer): MTF-Analyse-Instanz (lazy init)

    Hauptfunktionen:
        select_roi_callback(): ROI wählen + MTF berechnen
        autofocus_callback(): Automatische Fokussierung
        measure_mtf_callback(): MTF-Messung
    """

    def __init__(self, node, camera_driver):
        """
        Initialisiert die Callbacks.

        Args:
            node: Parent ROS2-Node
            camera_driver: Kamera-Treiber (CameraDriver-Instanz)
        """
        self._node = node
        self._driver = camera_driver

        # MTF-Analyzer wird bei erstem Gebrauch initialisiert
        self._mtf_analyzer = None

    # ══════════════════════════════════════════════════════════════════════════
    # SCHÄRFE-BERECHNUNG
    # ══════════════════════════════════════════════════════════════════════════

    def _calculate_sharpness(self, image, metric: str = 'variance'):
        """
        Berechnet die Schärfe eines Bildes.

        Verwendet Focus-Metriken aus promoc_core für konsistente
        Schärfe-Bewertung über das gesamte System.

        Args:
            image: Eingabebild (BGR oder Graustufen)
            metric: Metrik-Typ:
                - 'variance': Laplacian Variance (Standard)
                - 'tenengrad': Gradient-basiert

        Returns:
            float: Schärfe-Score (höher = schärfer)

        Beispiel:
            >>> sharpness = self._calculate_sharpness(cv_image)
            >>> print(f"Schärfe: {sharpness:.2f}")
        """
        if metric == 'tenengrad':
            return tenengrad(image)
        else:
            return laplacian_variance(image)

    # ══════════════════════════════════════════════════════════════════════════
    # ROI-AUSWAHL
    # ══════════════════════════════════════════════════════════════════════════

    def select_roi_callback(self, request, response):
        """
        Callback für interaktive ROI-Auswahl und MTF-Berechnung.

        Ablauf (Schritt für Schritt):
        =============================
        1. Letztes Kamera-Bild holen
        2. OpenCV-Fenster für ROI-Auswahl öffnen
        3. Benutzer wählt Rechteck um Slanted Edge
        4. MTF aus ROI berechnen
        5. Ergebnis als CSV exportieren
        """
        self._node.get_logger().info("ROI selection service called.")

        try:
            # ── Schritt 1: Bild verfügbar? ──
            if self._node.latest_image_msg is None:
                raise ImageProcessingError(
                    "No image received yet",
                    details={
                        'context': 'ROI selection requires active camera feed'}
                )

            # ── Schritt 2: ROS → OpenCV konvertieren ──
            try:
                cv_image = self._node.bridge.imgmsg_to_cv2(
                    self._node.latest_image_msg, "bgr8")
            except Exception as e:
                raise ImageProcessingError(
                    f"Failed to convert ROS image to OpenCV format: {str(e)}",
                    details={'encoding': 'bgr8', 'error': str(e)}
                )

            # ── Schritt 3: ROI interaktiv auswählen ──
            roi = cv2.selectROI("Select ROI", cv_image,
                                fromCenter=False, showCrosshair=True)
            cv2.destroyWindow("Select ROI")

            if roi == (0, 0, 0, 0):
                self._node.get_logger().info("ROI selection cancelled by user.")
                response.success = False
                response.message = "ROI selection cancelled."
                return response

            # ── Schritt 4: ROI extrahieren und validieren ──
            x, y, w, h = roi
            self._node.get_logger().info(f"Selected ROI (x, y, w, h): {roi}")

            if w <= 0 or h <= 0:
                raise ParameterValidationError(
                    "Invalid ROI dimensions",
                    details={'roi': roi, 'width': w, 'height': h,
                             'constraint': 'width and height must be positive'}
                )

            roi_image = cv_image[y:y+h, x:x+w]

            # ── Schritt 5: MTF berechnen ──
            self._node.get_logger().info("Calculating MTF from selected ROI...")
            mtf_results = self._node.image_processor.calculate_mtf_from_roi(
                roi_image)

            if not mtf_results:
                raise ImageProcessingError(
                    "MTF calculation failed - could not determine ESF or edge was not found",
                    details={'roi': roi, 'roi_size': (w, h)}
                )

            # ── Schritt 6: Ergebnis exportieren ──
            output_filename = self._node.get_parameter(
                'mtf_csv_path').get_parameter_value().string_value
            if not output_filename:
                raise ConfigurationError(
                    "MTF CSV output path not configured",
                    details={'parameter': 'mtf_csv_path',
                             'value': output_filename}
                )

            self._node.image_processor.export_to_csv(
                mtf_results, output_filename)

            response.success = True
            response.message = f"MTF calculation successful. Results saved to {output_filename}"
            self._node.get_logger().info(response.message)

        except ImageProcessingError as e:
            response.success = False
            response.message = f"⚠️ {str(e)}"
            self._node.get_logger().warn(response.message)
            self._node.get_logger().debug(
                f"Image processing error details: {e.details}")

        except ParameterValidationError as e:
            response.success = False
            response.message = f"⚠️ {str(e)}"
            self._node.get_logger().warn(response.message)
            self._node.get_logger().debug(
                f"Parameter validation details: {e.details}")

        except ConfigurationError as e:
            response.success = False
            response.message = f"⚠️ {str(e)}"
            self._node.get_logger().warn(response.message)
            self._node.get_logger().debug(
                f"Configuration error details: {e.details}")

        except Exception as e:
            response.success = False
            response.message = f"❌ ROI selection failed: {str(e)}"
            self._node.get_logger().error(response.message, exc_info=True)

        return response

    # ══════════════════════════════════════════════════════════════════════════
    # AUTOFOKUS
    # ══════════════════════════════════════════════════════════════════════════

    def autofocus_callback(self, request, response):
        """
        Callback für automatische Fokussierung.

        Führt einen Hybrid-Autofokus durch:
        1. Grobe Suche über gesamten Bereich
        2. Feine Suche mit Golden Section um Maximum

        Parameter:
        ----------
        - start_position: Startposition für Fokussuche
        - end_position: Endposition für Fokussuche
        - step_size: Schrittweite für grobe Suche
        """
        self._node.get_logger().info(
            f"Autofocus service called with range {request.start_position} to {request.end_position} with step {request.step_size}")

        try:
            # ── Schritt 1: Parameter validieren ──
            if request.start_position >= request.end_position:
                raise InvalidParameterError(
                    "Start position must be less than end position",
                    details={
                        'start_position': request.start_position,
                        'end_position': request.end_position,
                        'constraint': 'start < end'
                    }
                )

            if request.step_size <= 0:
                raise InvalidParameterError(
                    "Step size must be positive",
                    details={
                        'parameter': 'step_size',
                        'value': request.step_size,
                        'constraint': 'positive'
                    }
                )

            # ── Schritt 2: Service-Clients erstellen ──
            move_abs_client = self._node.create_client(
                MoveAbsolute, '/lts300_node/move_absolute')
            jog_client = self._node.create_client(
                JogAxis, '/lts300_node/jog_axis')

            if not move_abs_client.wait_for_service(timeout_sec=1.0):
                raise ServiceCallFailedError(
                    "Linear axis move_absolute service not available",
                    details={'service': '/lts300_node/move_absolute',
                             'timeout': 1.0}
                )

            if not jog_client.wait_for_service(timeout_sec=1.0):
                raise ServiceCallFailedError(
                    "Linear axis jog_axis service not available",
                    details={'service': '/lts300_node/jog_axis', 'timeout': 1.0}
                )

            sharpness_values = []
            positions = []

            # Move to start position
            move_req = MoveAbsolute.Request()
            move_req.position = request.start_position
            future = move_abs_client.call_async(move_req)
            rclpy.spin_until_future_complete(self._node, future)

            if future.result() is None:
                raise ServiceCallFailedError(
                    "Move to start position - no response received",
                    details={'target_position': request.start_position}
                )

            if not future.result().success:
                raise ServiceCallFailedError(
                    f"Failed to move to start position: {future.result().status_message}",
                    details={
                        'target_position': request.start_position,
                        'service_response': future.result().status_message
                    }
                )

            # Scan through positions
            current_pos = request.start_position
            while current_pos <= request.end_position:
                positions.append(current_pos)

                # Capture image and calculate sharpness
                if self._node.latest_image_msg is None:
                    time.sleep(0.5)  # Wait for image

                if self._node.latest_image_msg is None:
                    self._node.get_logger().warn(
                        f"No image at position {current_pos}")
                    sharpness_values.append(0)
                else:
                    try:
                        cv_image = self._node.bridge.imgmsg_to_cv2(
                            self._node.latest_image_msg, "bgr8")
                        sharpness = self._calculate_sharpness(cv_image)
                        sharpness_values.append(sharpness)
                        self._node.get_logger().debug(
                            f"Position: {current_pos:.2f}mm, Sharpness: {sharpness:.2f}")
                    except Exception as e:
                        self._node.get_logger().warn(
                            f"Failed to process image at position {current_pos}: {str(e)}")
                        sharpness_values.append(0)

                # Move to next position (unless we're at the end)
                if current_pos + request.step_size <= request.end_position:
                    jog_req = JogAxis.Request()
                    jog_req.step_size = request.step_size
                    future = jog_client.call_async(jog_req)
                    rclpy.spin_until_future_complete(self._node, future)

                    if future.result() is None or not future.result().success:
                        self._node.get_logger().warn(
                            f"Failed to jog axis at position {current_pos}")

                current_pos += request.step_size

            # Validate results
            if not sharpness_values or all(s == 0 for s in sharpness_values):
                raise ImageProcessingError(
                    "No valid sharpness values calculated during autofocus scan",
                    details={
                        'positions_scanned': len(positions),
                        'valid_measurements': sum(1 for s in sharpness_values if s > 0)
                    }
                )

            # Find best position
            max_sharpness = max(sharpness_values)
            best_position = positions[sharpness_values.index(max_sharpness)]

            self._node.get_logger().info(
                f"📷 Best focus position: {best_position:.2f}mm (sharpness: {max_sharpness:.2f})")

            # Move to best position
            move_req.position = best_position
            future = move_abs_client.call_async(move_req)
            rclpy.spin_until_future_complete(self._node, future)

            if future.result() is None:
                raise ServiceCallFailedError(
                    "Move to best position - no response received",
                    details={'target_position': best_position}
                )

            if not future.result().success:
                raise ServiceCallFailedError(
                    f"Failed to move to best position: {future.result().status_message}",
                    details={
                        'target_position': best_position,
                        'max_sharpness': max_sharpness,
                        'service_response': future.result().status_message
                    }
                )

            response.success = True
            response.message = f"Autofocus successful. Best position: {best_position:.2f}mm (sharpness: {max_sharpness:.2f})"
            response.best_position = best_position

        except InvalidParameterError as e:
            response.success = False
            response.message = f"⚠️ {str(e)}"
            self._node.get_logger().warn(response.message)
            self._node.get_logger().debug(
                f"Parameter validation details: {e.details}")

        except ServiceCallFailedError as e:
            response.success = False
            response.message = f"⚠️ {str(e)}"
            self._node.get_logger().error(response.message)
            self._node.get_logger().debug(
                f"Service call error details: {e.details}")

        except ImageProcessingError as e:
            response.success = False
            response.message = f"⚠️ {str(e)}"
            self._node.get_logger().warn(response.message)
            self._node.get_logger().debug(
                f"Image processing error details: {e.details}")

        except Exception as e:
            response.success = False
            response.message = f"❌ Autofocus failed: {str(e)}"
            self._node.get_logger().error(response.message, exc_info=True)

        return response

    async def manual_set_exposure_callback(self, request, response):
        """Callback for the manual exposure setting service."""
        self._node.get_logger().info(
            f"Received manual request to set exposure to {request.exposure_time}µs")

        try:
            # Validate exposure time
            if request.exposure_time <= 0:
                raise InvalidParameterError(
                    "Exposure time must be positive",
                    details={
                        'parameter': 'exposure_time',
                        'value': request.exposure_time,
                        'constraint': 'positive',
                        'unit': 'microseconds'
                    }
                )

            # Belichtungszeit über Treiber setzen
            success = await self._driver.set_exposure(request.exposure_time)

            if not success:
                raise HardwareError(
                    f"Belichtungszeit setzen fehlgeschlagen",
                    details={
                        'requested_exposure': request.exposure_time
                    }
                )

            response.success = True
            response.message = f"Exposure set to {request.exposure_time}µs successfully"
            self._node.get_logger().info(response.message)

        except InvalidParameterError as e:
            response.success = False
            response.message = f"⚠️ {str(e)}"
            self._node.get_logger().warn(response.message)
            self._node.get_logger().debug(
                f"Parameter validation details: {e.details}")

        except HardwareError as e:
            response.success = False
            response.message = f"⚠️ {str(e)}"
            self._node.get_logger().error(response.message)
            self._node.get_logger().debug(
                f"Hardware error details: {e.details}")

        except Exception as e:
            response.success = False
            response.message = f"❌ Setting exposure failed: {str(e)}"
            self._node.get_logger().error(response.message, exc_info=True)

        return response

    def measure_mtf_callback(self, request, response):
        """
        Callback for MTF measurement service.

        Uses the slanted edge method (ISO 12233) to compute MTF from
        the current camera image.
        """
        self._node.get_logger().info("MTF measurement service called")

        try:
            # Check if image is available
            if self._node.latest_image_msg is None:
                raise ImageProcessingError(
                    "No image received yet",
                    details={
                        'context': 'MTF measurement requires active camera feed'}
                )

            # Convert ROS image to OpenCV format
            try:
                cv_image = self._node.bridge.imgmsg_to_cv2(
                    self._node.latest_image_msg, "bgr8")
            except Exception as e:
                raise ImageProcessingError(
                    f"Failed to convert ROS image to OpenCV format: {str(e)}",
                    details={'encoding': 'bgr8', 'error': str(e)}
                )

            # Get pixel size from request or parameter
            pixel_size_um = request.pixel_size_um
            if pixel_size_um <= 0:
                pixel_size_um = self._node.get_parameter(
                    'pixel_size_um').get_parameter_value().double_value
                if pixel_size_um <= 0:
                    pixel_size_um = 3.45  # Default

            # Get ROI dimensions from request or parameter
            roi_width = request.roi_width
            if roi_width <= 0:
                roi_width = self._node.get_parameter(
                    'default_roi_width').get_parameter_value().integer_value
                if roi_width <= 0:
                    roi_width = 200

            roi_height = request.roi_height
            if roi_height <= 0:
                roi_height = self._node.get_parameter(
                    'default_roi_height').get_parameter_value().integer_value
                if roi_height <= 0:
                    roi_height = 200

            # Get ROI center
            h, w = cv_image.shape[:2]
            if request.roi_center_x < 0:
                roi_center_x = w // 2
            else:
                roi_center_x = request.roi_center_x

            if request.roi_center_y < 0:
                roi_center_y = h // 2
            else:
                roi_center_y = request.roi_center_y

            # Configure MTF analyzer
            config = MTFConfig(
                pixel_size_um=pixel_size_um,
                roi_width=roi_width,
                roi_height=roi_height,
                roi_center=(roi_center_x, roi_center_y)
            )

            analyzer = MTFAnalyzer(config)

            # Compute MTF
            self._node.get_logger().info(
                f"Computing MTF: ROI=({roi_center_x}, {roi_center_y}) {roi_width}x{roi_height}px, "
                f"pixel_size={pixel_size_um}µm"
            )

            result = analyzer.compute_mtf(cv_image)

            if not result.valid:
                raise ImageProcessingError(
                    f"MTF computation failed: {result.error_msg}",
                    details={
                        'edge_angle': result.edge_angle,
                        'roi_bounds': result.roi_bounds
                    }
                )

            # Populate response
            response.success = True
            response.message = f"MTF measurement successful. MTF50={result.mtf50:.2f} lp/mm"
            response.mtf50 = float(result.mtf50)
            response.mtf20 = float(result.mtf20)
            response.mtf10 = float(result.mtf10)
            response.edge_angle = float(result.edge_angle)
            response.nyquist_frequency = float(result.nyquist_frequency)

            self._node.get_logger().info(
                f"📊 MTF Results: MTF50={result.mtf50:.2f}, MTF20={result.mtf20:.2f}, "
                f"MTF10={result.mtf10:.2f} lp/mm (edge angle: {result.edge_angle:.1f}°)"
            )

        except ImageProcessingError as e:
            response.success = False
            response.message = f"⚠️ {str(e)}"
            self._node.get_logger().warn(response.message)
            self._node.get_logger().debug(
                f"Image processing error details: {e.details}")

        except Exception as e:
            response.success = False
            response.message = f"❌ MTF measurement failed: {str(e)}"
            self._node.get_logger().error(response.message, exc_info=True)

        return response
        return response
