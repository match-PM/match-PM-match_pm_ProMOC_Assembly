#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
import pandas as pd
import os
import sys
import time
import subprocess
from rosidl_runtime_py.utilities import get_service

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


class SquareBrightnessAnalyzer(Node):

    def __init__(self):
        super().__init__('square_brightness_analyzer')
        self.bridge = CvBridge()

        # --- ZIELPFAD ---
        self.save_dir = "/home/pmlab/Dokumente/Messungen/Yannis Wesser/Messungen/Helligkeitsverteilung"
        os.makedirs(self.save_dir, exist_ok=True)

        # --- KAMERA / TOPIC ---
        self.image_topic = "/promoc/promoc_camera/stream0/image_raw"

        # --- BELICHTUNGS-SERVICE ---
        self.exposure_service_name = "/promoc/camera/set_exposure"
        # None = automatisch per 'ros2 service type' ermitteln; sonst z.B. "camera_srvs/srv/SetExposure"
        self.exposure_service_type_str = None

        self.exposure_field_name = "exposure_time"

        self.start_exposure_us = 6000   # dein aktueller Startwert (6 ms)
        self.min_exposure_us = 50
        self.max_exposure_us = 100000
        self.current_exposure_us = self.start_exposure_us

        # None = automatisch aus dtype ableiten (np.iinfo); ggf. manuell setzen,
        # z.B. 4095 falls 12-bit-Sensordaten in einem 16-bit-Container stecken
        self.sensor_native_max_value = None
        self.bit_max = None  # wird beim ersten Frame bestimmt

        # --- QUADRAT-ERKENNUNG ---
        self.min_square_side_px = 200
        self.inner_margin_fraction = 0.10

        # --- REGELUNGS-ZIELWERTE ---
        # Zielband: der Großteil der Pixel soll zwischen 90% und 95% des Vollausschlags liegen
        self.target_band_low_fraction = 0.935
        self.target_band_high_fraction = 0.965
        # Anteil der Pixel, der mindestens im Zielband liegen muss, damit die Regelung konvergiert
        self.min_pixel_fraction_in_band = 0.70   # >= 90% der Pixel im 90-95%-Band
        # Harte Sättigungsgrenze (Clipping) - unabhaengig vom Zielband nie ueberschreiten
        self.saturation_pixel_fraction_of_max = 0.98
        self.max_sat_fraction_percent = 1.0      # max. erlaubter Anteil wirklich gesaettigter Pixel

        # Pixelbereiche (x, y, w, h), in denen jeweils gesucht wird
        self.rois = {
            "1_Mitte":         (2265, 1375, 1000, 1000),
            "2_Oben_links":    (1, 1, 1000, 1000),
            "3_Oben_rechts":   (4560, 1, 1000, 1000),
            "4_Unten_rechts":  (4560, 2770, 1000, 1000),
            "5_Unten_links":   (1, 2770, 1000, 1000),
            "6_Mitte_Quadrat": (1436, 986, 1106, 1102),
        }

        # --- MESSSTRATEGIE ---
        self.FRAMES_PER_TUNING_CHECK = 3
        self.FRAMES_PER_MEASUREMENT = 10
        self.MAX_TUNING_ITERATIONS = 15

        self.tuning_frame_buffer = []
        self.frame_buffer = []
        self.tuning_iteration = 0
        self.state = 'INIT'  # INIT -> TUNING -> MEASURING -> DONE

        # --- CALLBACK-GRUPPEN (wichtig: Bild-Callback darf nicht blockieren,
        #     waehrend der Service-Response verarbeitet wird -> getrennte Gruppen) ---
        self.image_cb_group = MutuallyExclusiveCallbackGroup()
        self.service_cb_group = MutuallyExclusiveCallbackGroup()

        # Service-Client aufbauen (Typ automatisch/​manuell ermitteln)
        self._resolve_exposure_service()

        self.subscription = self.create_subscription(
            Image, self.image_topic, self.image_callback, 10,
            callback_group=self.image_cb_group)

        self.get_logger().info("=" * 60)
        self.get_logger().info("HELLIGKEITSVERTEILUNG mit automatischer Belichtungsregelung")
        self.get_logger().info(f"Topic: {self.image_topic}")
        self.get_logger().info(f"Start-Belichtung: {self.start_exposure_us} us")
        self.get_logger().info(f"Speicherpfad: {self.save_dir}")
        self.get_logger().info("=" * 60)

    # -----------------------------------------------------------------
    # SERVICE-TYP / -FELD AUTOMATISCH ERMITTELN
    # -----------------------------------------------------------------
    def _resolve_exposure_service(self):
        if self.exposure_service_type_str is not None:
            type_str = self.exposure_service_type_str
            self.get_logger().info(f"Verwende manuell konfigurierten Service-Typ: {type_str}")
        else:
            self.get_logger().info(
                f"Ermittle Service-Typ fuer '{self.exposure_service_name}' automatisch...")
            try:
                result = subprocess.run(
                    ['ros2', 'service', 'type', self.exposure_service_name],
                    capture_output=True, text=True, timeout=5.0)
                type_str = result.stdout.strip()
            except Exception as e:
                raise RuntimeError(
                    f"Konnte 'ros2 service type {self.exposure_service_name}' nicht ausfuehren: {e}")

            if not type_str:
                raise RuntimeError(
                    f"Service-Typ fuer '{self.exposure_service_name}' konnte nicht ermittelt "
                    f"werden. Laeuft der Kamera-Node? Pruefe mit: "
                    f"ros2 service list | grep exposure")

            self.get_logger().info(f"Service-Typ automatisch erkannt: {type_str}")

        self._exposure_srv_type = get_service(type_str)

        if self.exposure_field_name is not None:
            field_name = self.exposure_field_name
            self.get_logger().info(f"Verwende manuell konfiguriertes Request-Feld: '{field_name}'")
        else:
            req_instance = self._exposure_srv_type.Request()
            req_fields = req_instance.get_fields_and_field_types()
            int_fields = [f for f, t in req_fields.items()
                          if 'int' in t and 'sequence' not in t]
            if len(int_fields) == 1:
                field_name = int_fields[0]
                self.get_logger().info(f"Request-Feld automatisch erkannt: '{field_name}'")
            else:
                raise RuntimeError(
                    f"Konnte das Request-Feld nicht eindeutig automatisch bestimmen. "
                    f"Gefundene Felder: {req_fields}. Bitte 'self.exposure_field_name' "
                    f"im Konstruktor manuell setzen. Pruefe mit: "
                    f"ros2 interface show {type_str}")

        self._srv_field_name = field_name

        self.exposure_client = self.create_client(
            self._exposure_srv_type, self.exposure_service_name,
            callback_group=self.service_cb_group)

        self.get_logger().info(
            f"Warte auf Verfuegbarkeit von Service '{self.exposure_service_name}' ...")
        if not self.exposure_client.wait_for_service(timeout_sec=15.0):
            raise RuntimeError(
                f"Service '{self.exposure_service_name}' ist nach 15s nicht verfuegbar. "
                f"Laeuft der Kamera-Node?")
        self.get_logger().info("Exposure-Service ist verfuegbar.")

    def call_set_exposure(self, exposure_us):
        exposure_us = int(round(exposure_us))
        request = self._exposure_srv_type.Request()
        # Service erwartet 'exposure_time' als double -> float übergeben
        setattr(request, self._srv_field_name, float(exposure_us))

        self.get_logger().info(f"Setze Belichtungszeit: {exposure_us} us ...")
        future = self.exposure_client.call_async(request)

        timeout_s = 5.0
        start_t = time.time()
        while not future.done():
            if time.time() - start_t > timeout_s:
                self.get_logger().error(
                    f"Timeout beim Setzen der Belichtungszeit auf {exposure_us} us!")
                return False
            time.sleep(0.01)

        if future.exception() is not None:
            self.get_logger().error(
                f"Service-Fehler beim Setzen der Belichtung: {future.exception()}")
            return False

        response = future.result()
        self.get_logger().info(
            f"Belichtungszeit gesetzt: {exposure_us} us (Antwort: {response})")
        self.current_exposure_us = exposure_us

        # Kurze Pause, damit die neue Belichtung sicher in den naechsten Frames wirksam ist
        time.sleep(0.3)
        return True

    # -----------------------------------------------------------------
    # BILD-CALLBACK / ZUSTANDSAUTOMAT
    # -----------------------------------------------------------------
    def image_callback(self, msg):
        if self.state == 'DONE':
            return
        try:
            raw_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
            gray = raw_img[:, :, 1] if len(raw_img.shape) == 3 else raw_img

            if self.bit_max is None:
                self.bit_max = self._get_bit_max(gray)
                self.get_logger().info(
                    f"Erkannte Bittiefe: dtype={gray.dtype}, Vollausschlag={self.bit_max}")

            if self.state == 'INIT':
                self.call_set_exposure(self.start_exposure_us)
                self.state = 'TUNING'
                self.tuning_frame_buffer.clear()
                return  # dieser Frame hatte noch die alte Belichtung -> verwerfen

            if self.state == 'TUNING':
                self._handle_tuning_frame(gray)
                return

            if self.state == 'MEASURING':
                self._handle_measuring_frame(gray)
                return

        except Exception as e:
            self.get_logger().error(f"Fehler im Image-Callback: {e}")

    def _get_bit_max(self, gray):
        if self.sensor_native_max_value is not None:
            return float(self.sensor_native_max_value)
        if np.issubdtype(gray.dtype, np.integer):
            return float(np.iinfo(gray.dtype).max)
        return 255.0

    def _handle_tuning_frame(self, gray):
        self.tuning_frame_buffer.append(gray.astype(np.float32))
        if len(self.tuning_frame_buffer) < self.FRAMES_PER_TUNING_CHECK:
            return

        averaged = np.mean(self.tuning_frame_buffer, axis=0).astype(gray.dtype)
        self.tuning_frame_buffer.clear()
        self.tuning_iteration += 1

        results = self.evaluate_rois(averaged, save_outputs=False)
        converged, new_exposure = self._decide_next_exposure(results)

        if converged:
            self.get_logger().info(
                f"Belichtung konvergiert nach {self.tuning_iteration} Iteration(en) "
                f"bei {self.current_exposure_us} us.")
            self.state = 'MEASURING'
            self.frame_buffer.clear()
            return

        if self.tuning_iteration >= self.MAX_TUNING_ITERATIONS:
            self.get_logger().warn(
                f"Maximale Anzahl Tuning-Iterationen ({self.MAX_TUNING_ITERATIONS}) erreicht. "
                f"Verwende letzten Wert: {self.current_exposure_us} us.")
            self.state = 'MEASURING'
            self.frame_buffer.clear()
            return

        self.call_set_exposure(new_exposure)

    def _handle_measuring_frame(self, gray):
        self.frame_buffer.append(gray.astype(np.float32))
        if len(self.frame_buffer) < self.FRAMES_PER_MEASUREMENT:
            return

        averaged = np.mean(self.frame_buffer, axis=0).astype(gray.dtype)
        self.frame_buffer.clear()
        self.state = 'DONE'
        self.evaluate_rois(averaged, save_outputs=True)
        self.finish()

    def _decide_next_exposure(self, results):
        if not results:
            self.get_logger().warn(
                "Kein Quadrat waehrend der Belichtungsanpassung gefunden - "
                "Belichtung wird nicht weiter angepasst.")
            return True, self.current_exposure_us

        # Schlechtestes (kritischstes) Quadrat bestimmt die Entscheidung:
        # - hoechste Saettigung -> Risiko fuer Clipping
        # - geringster Anteil im Zielband -> am weitesten von "fertig" entfernt
        max_sat = max(r['Saettigungsanteil_Prozent'] for r in results)
        min_band_fraction = min(r['Anteil_im_Zielband_Prozent'] for r in results)
        # Repraesentativer Median ueber alle gefundenen Quadrate, um die Regelrichtung zu bestimmen
        median_values = [r['Median'] for r in results]
        metric_median = float(np.median(median_values))

        band_low = self.target_band_low_fraction * self.bit_max
        band_high = self.target_band_high_fraction * self.bit_max
        band_mid = (band_low + band_high) / 2.0
        current = self.current_exposure_us

        # 1. Harte Sättigungsgrenze hat immer Vorrang -> Belichtung reduzieren
        if max_sat > self.max_sat_fraction_percent:
            new_exp = current * 0.9
            reason = f"Saettigung {max_sat:.2f}% > {self.max_sat_fraction_percent}% (Clipping-Schutz)"

        # 2. Konvergenzkriterium: Großteil der Pixel liegt im 90-95%-Band UND keine Übersättigung
        elif min_band_fraction >= self.min_pixel_fraction_in_band * 100.0:
            self.get_logger().info(
                f"Zielband erreicht: min. {min_band_fraction:.1f}% der Pixel "
                f"(>= {self.min_pixel_fraction_in_band*100:.0f}% gefordert) "
                f"liegen zwischen {band_low:.0f} und {band_high:.0f}.")
            return True, current

        # 3. Median oberhalb des Zielbands -> Belichtung reduzieren
        elif metric_median > band_high:
            ratio = band_mid / max(metric_median, 1.0)
            ratio = max(0.5, min(ratio, 0.97))
            new_exp = current * ratio
            reason = (f"Median {metric_median:.1f} > Zielband-Obergrenze {band_high:.1f}, "
                      f"nur {min_band_fraction:.1f}% der Pixel im Zielband")

        # 4. Median unterhalb des Zielbands -> Belichtung erhoehen
        elif metric_median < band_low:
            ratio = band_mid / max(metric_median, 1.0)
            ratio = max(1.03, min(ratio, 1.6))
            new_exp = current * ratio
            reason = (f"Median {metric_median:.1f} < Zielband-Untergrenze {band_low:.1f}, "
                      f"nur {min_band_fraction:.1f}% der Pixel im Zielband")

        # 5. Median liegt im Band, aber noch nicht genug Pixel darin (z.B. hohe Streuung) ->
        #    minimal weiter in Richtung Bandmitte nachregeln, keine grossen Spruenge mehr
        else:
            if metric_median < band_mid:
                new_exp = current * 1.03
            else:
                new_exp = current * 0.97
            reason = (f"Median {metric_median:.1f} im Zielband, aber nur "
                      f"{min_band_fraction:.1f}% der Pixel darin - feinjustieren")

        new_exp = int(round(new_exp))
        new_exp = max(self.min_exposure_us, min(new_exp, self.max_exposure_us))

        self.get_logger().info(
            f"Belichtungsanpassung: {reason} -> {current} us -> {new_exp} us "
            f"(Anteil im Zielband: {min_band_fraction:.1f}%)")
        return False, new_exp

    # -----------------------------------------------------------------
    # QUADRAT-ERKENNUNG
    # -----------------------------------------------------------------
    def find_square_in_roi(self, roi_gray):
        """Findet GENAU EIN Referenzquadrat (>= self.min_square_side_px) im ROI."""
        if roi_gray.dtype != np.uint8:
            roi_8u = cv2.normalize(roi_gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        else:
            roi_8u = roi_gray

        blurred = cv2.GaussianBlur(roi_8u, (5, 5), 0)
        median_val = np.median(blurred)
        if median_val > 127:
            _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        else:
            _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        short_side = min(roi_8u.shape)
        k = max(9, int(short_side * 0.015))
        if k % 2 == 0:
            k += 1
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
        opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        min_area = self.min_square_side_px * self.min_square_side_px

        best_cnt = None
        best_rect = None
        best_area = -1.0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            rect = cv2.minAreaRect(cnt)
            (cx, cy), (w, h), angle = rect
            if w == 0 or h == 0:
                continue
            if min(w, h) < self.min_square_side_px:
                continue
            aspect = min(w, h) / max(w, h)
            extent = area / (w * h)
            if aspect < 0.85 or extent < 0.85:
                continue
            if area > best_area:
                best_area = area
                best_cnt = cnt
                best_rect = rect

        if best_cnt is None:
            return None
        return best_rect

    def shrink_rect(self, rect, fraction):
        (cx, cy), (w, h), angle = rect
        new_w = w * (1.0 - 2.0 * fraction)
        new_h = h * (1.0 - 2.0 * fraction)
        return ((cx, cy), (new_w, new_h), angle)

    def extract_polygon_pixels(self, gray_full, rect_local, offset_xy):
        ox, oy = offset_xy
        (cx, cy), (w, h), angle = rect_local
        rect_full = ((cx + ox, cy + oy), (w, h), angle)

        box = cv2.boxPoints(rect_full).astype(np.int32)

        mask = np.zeros(gray_full.shape, dtype=np.uint8)
        cv2.fillConvexPoly(mask, box, 255)

        pixel_values = gray_full[mask == 255]
        return pixel_values, box

    # -----------------------------------------------------------------
    # AUSWERTUNG ALLER ROIS
    # -----------------------------------------------------------------
    def evaluate_rois(self, gray_full, save_outputs=False):
        sat_pixel_threshold = self.saturation_pixel_fraction_of_max * self.bit_max

        results = []
        found_in = []
        not_found_in = []

        overlay = None
        if save_outputs:
            if gray_full.dtype == np.uint8:
                overlay = cv2.cvtColor(gray_full, cv2.COLOR_GRAY2BGR)
            else:
                disp = cv2.normalize(gray_full, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
                overlay = cv2.cvtColor(disp, cv2.COLOR_GRAY2BGR)

        for name, (x, y, w, h) in self.rois.items():
            x0 = max(0, x)
            y0 = max(0, y)
            x1 = min(gray_full.shape[1], x + w)
            y1 = min(gray_full.shape[0], y + h)

            if x1 <= x0 or y1 <= y0:
                not_found_in.append(name)
                continue

            roi_gray = gray_full[y0:y1, x0:x1]
            square_rect = self.find_square_in_roi(roi_gray)
            if square_rect is None:
                not_found_in.append(name)
                continue

            found_in.append(name)

            inner_rect = self.shrink_rect(square_rect, self.inner_margin_fraction)
            pixel_values, box_full = self.extract_polygon_pixels(gray_full, inner_rect, (x0, y0))

            if pixel_values.size == 0:
                continue

            sat_fraction = float(np.mean(pixel_values >= sat_pixel_threshold) * 100.0)

            band_low = self.target_band_low_fraction * self.bit_max
            band_high = self.target_band_high_fraction * self.bit_max
            band_fraction = float(
                np.mean((pixel_values >= band_low) & (pixel_values <= band_high)) * 100.0)
            below_band_fraction = float(np.mean(pixel_values < band_low) * 100.0)

            stats = {
                'Bereich': name,
                'ROI_X': x, 'ROI_Y': y, 'ROI_W': w, 'ROI_H': h,
                'Quadrat_CX_px': round(square_rect[0][0] + x0, 2),
                'Quadrat_CY_px': round(square_rect[0][1] + y0, 2),
                'Quadrat_Breite_px': round(square_rect[1][0], 2),
                'Quadrat_Hoehe_px': round(square_rect[1][1], 2),
                'Quadrat_Winkel_deg': round(square_rect[2], 2),
                'Anzahl_Pixel': int(pixel_values.size),
                'Mittelwert': float(np.mean(pixel_values)),
                'Median': float(np.median(pixel_values)),
                'StdAbw': float(np.std(pixel_values)),
                'Min': float(np.min(pixel_values)),
                'Max': float(np.max(pixel_values)),
                'P05': float(np.percentile(pixel_values, 5)),
                'P95': float(np.percentile(pixel_values, 95)),
                'Saettigungsanteil_Prozent': round(sat_fraction, 3),
                'Anteil_im_Zielband_Prozent': round(band_fraction, 3),
                'Anteil_unter_Zielband_Prozent': round(below_band_fraction, 3),
                'Bit_Max': float(self.bit_max),
                'Belichtungszeit_us': int(self.current_exposure_us),
            }
            results.append(stats)

            if save_outputs:
                self.get_logger().info(
                    f"[{name}] Mittelwert={stats['Mittelwert']:.1f}  "
                    f"Saettigung={stats['Saettigungsanteil_Prozent']:.2f}%  "
                    f"Min={stats['Min']:.0f}  Max={stats['Max']:.0f}  n={stats['Anzahl_Pixel']}")

                outer_box_full = cv2.boxPoints(
                    ((square_rect[0][0] + x0, square_rect[0][1] + y0),
                     square_rect[1], square_rect[2])
                ).astype(np.int32)
                cv2.polylines(overlay, [outer_box_full], True, (0, 0, 255), 3)
                cv2.polylines(overlay, [box_full], True, (0, 255, 0), 3)
                cv2.putText(overlay, name, (x0 + 10, y0 + 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)

                self.save_histogram(name, pixel_values, stats, self.bit_max)

        if save_outputs:
            self.get_logger().info("=" * 60)
            self.get_logger().info(f"Quadrat gefunden in: {found_in if found_in else 'KEINEM Bereich'}")
            self.get_logger().info(f"Kein Quadrat in:     {not_found_in if not_found_in else '-'}")
            self.get_logger().info("=" * 60)

            if results:
                df = pd.DataFrame(results)
                csv_path = os.path.join(self.save_dir, "helligkeitsverteilung_statistik.csv")
                df.to_csv(csv_path, index=False, sep=';', decimal='.')
                self.get_logger().info(f"Statistik gespeichert: {csv_path}")
            else:
                self.get_logger().error("In keinem der Bereiche wurde ein Referenzquadrat gefunden!")

            overlay_path = os.path.join(self.save_dir, "overlay_erkannte_quadrate.png")
            cv2.imwrite(overlay_path, overlay)
            self.get_logger().info(f"Uebersichtsbild gespeichert: {overlay_path}")

        return results

    def save_histogram(self, name, pixel_values, stats, bit_max):
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.hist(pixel_values, bins=64, range=(0, bit_max), color='steelblue',
                edgecolor='black', alpha=0.8)
        ax.axvline(stats['Mittelwert'], color='crimson', linestyle='--', linewidth=2,
                   label=f"Mittelwert = {stats['Mittelwert']:.1f}")
        ax.axvline(stats['Median'], color='darkorange', linestyle=':', linewidth=2,
                   label=f"Median = {stats['Median']:.1f}")
        ax.axvline(0.95 * bit_max, color='red', linestyle='-', linewidth=1.2, alpha=0.6,
                   label=f"95% Helligkeit ({0.95 * bit_max:.0f})")
        ax.set_title(
            f"Helligkeitsverteilung - {name}\n"
            f"Belichtung: {stats['Belichtungszeit_us']} us", 
            fontsize=11, fontweight='bold')
        ax.set_xlabel(f'Grauwert (0-{int(bit_max)})')
        ax.set_ylabel('Anzahl Pixel')
        ax.set_xlim(0, bit_max)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9)
        fig.tight_layout()

        out_path_png = os.path.join(self.save_dir, f"histogramm_{name}.png")
        fig.savefig(out_path_png, format='png', dpi=200)
        out_path_svg = os.path.join(self.save_dir, f"histogramm_{name}.svg")
        fig.savefig(out_path_svg, format='svg')
        plt.close(fig)

    def finish(self):
        self.get_logger().info("=" * 60)
        self.get_logger().info("Auswertung abgeschlossen.")
        self.get_logger().info(f"Finale Belichtungszeit: {self.current_exposure_us} us")
        self.get_logger().info(f"Ergebnisse in: {self.save_dir}")
        self.get_logger().info("=" * 60)
        self.destroy_subscription(self.subscription)
        rclpy.shutdown()


def main():
    rclpy.init()
    node = SquareBrightnessAnalyzer()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    except Exception:
        pass
    finally:
        node.destroy_node()


if __name__ == '__main__':
    main()