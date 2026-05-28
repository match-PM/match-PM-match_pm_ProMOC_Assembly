#!/usr/bin/env python3
"""
Wissenschaftlich korrektes Verschiebungsmessungssystem.
Berechnet die subpixel-genaue, rotationsbereinigte horizontale Verschiebung.
Headless-Version (ohne Live-Bild) mit Fehlerabsicherung gegen NoneType-Abstürze.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import math
import threading

class HeadlessGridDisplacementAnalyzer(Node):

    def __init__(self):
        super().__init__('headless_grid_displacement_analyzer')
        self.bridge = CvBridge()

        # --- ZIELPFAD FÜR DATENSPEICHERUNG ---
        self.save_dir = "/home/pmlab/Dokumente/Messungen/Yannis Wesser/Verschiebung"
        os.makedirs(self.save_dir, exist_ok=True)

        # --- PHYSIKALISCHE KONFIGURATION ---
        self.image_topic = "/promoc/promoc_camera/stream0/image_raw"
        self.FRAMES_PER_MEASUREMENT = 10
        
        # Optische Parameter
        self.pixel_size_um = 2.4 # Hier anpassen MESSUNG
        self.magnification = 3.0 # Hier anpassen MESSUNG
        self.effective_pixel_size = self.pixel_size_um / self.magnification  # 0.8 µm/px
        self.filter_strictness = 0.25

        # --- ABBRUCH-LOGIK (TIMEOUT) ---
        self.consecutive_empty_frames = 0
        self.MAX_EMPTY_FRAMES = 100  # Bricht ab, wenn 100 Frames in Folge ungültig sind

        # --- ZUSTANDSAUTOMAT ---
        # States: 'COLLECT_REF', 'WAIT_FOR_INPUT', 'COLLECT_TARGET', 'DONE'
        self.state = 'COLLECT_REF'
        
        self.frame_buffer = []
        self.img_width = 0
        self.img_height = 0

        # Speicher für Gitterdaten: {(approx_col, approx_row): [x_px, y_px]}
        self.ref_grid_points = {}
        self.final_target_grid_points = {}

        self.subscription = self.create_subscription(
            Image, self.image_topic, self.image_callback, 10)

        self.get_logger().info("=" * 60)
        self.get_logger().info("HEADLESS GITTER-VERSCHIEBUNGSANALYSE")
        self.get_logger().info(f"Effektive Pixelgröße: {self.effective_pixel_size:.2f} µm/px")
        self.get_logger().info("Ankerpunkt: Rechter Bildrand (robust gegen Punktverlust)")
        self.get_logger().info("=" * 60)
        self.get_logger().info("Sammle Bilder für das REFERENZBILD...")

    def image_callback(self, msg):
        if self.state in ['WAIT_FOR_INPUT', 'DONE']:
            return

        try:
            raw_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
            gray = raw_img[:, :, 1] if len(raw_img.shape) == 3 else raw_img
            self.img_height, self.img_width = gray.shape

            if gray.dtype != np.uint8:
                gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

            # Binarisierung
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            if np.median(blurred) > 127:
                _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            else:
                _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # --- VORAB-CHECK FÜR ABBRUCH-LOGIK ---
            # Schneller Check des aktuellen Einzelbildes, um ein Feststecken (z.B. bei Dunkelheit) zu verhindern
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if len(contours) < 100:
                self.consecutive_empty_frames += 1
                if self.consecutive_empty_frames >= self.MAX_EMPTY_FRAMES:
                    self.get_logger().error(f"ABBRUCH: Seit {self.MAX_EMPTY_FRAMES} Frames keine Gitterpunkte erkannt!")
                    rclpy.shutdown()
                    return
            else:
                self.consecutive_empty_frames = 0

            # --- BUFFER BEFÜLLEN UND MITTELN ---
            self.frame_buffer.append(binary.astype(np.float32))
            
            if len(self.frame_buffer) == self.FRAMES_PER_MEASUREMENT:
                denoised_binary = np.mean(self.frame_buffer, axis=0).astype(np.uint8)
                self.frame_buffer.clear()
                
                # Punkte aus dem gemittelten Bild extrahieren
                pts_dict = self.extract_grid_points(denoised_binary)
                
                # FEHLERSCHUTZ: Prüfen, ob die Extraktion erfolgreich war (nicht None)
                if pts_dict is None or len(pts_dict) < 100:
                    self.get_logger().warn("Gemitteltes Bild enthielt keine validen Gitterpunkte. Starte neue Bildserie...")
                    return

                if pts_dict is not None and len(pts_dict) >= 100:
                    if self.state == 'COLLECT_REF':
                        self.ref_grid_points = pts_dict
                        self.ref_point_count_initial = len(pts_dict)
                        self.state = 'WAIT_FOR_INPUT'
                        threading.Thread(target=self.wait_for_user_input, daemon=True).start()
                    
                    # WICHTIG: Das elif muss auf der gleichen Ebene wie das erste if sein!
                    elif self.state == 'COLLECT_TARGET':
                        self.final_target_grid_points = pts_dict
                        self.state = 'DONE'
                        self.calculate_final_displacement()
                
                elif pts_dict is None:
                    self.get_logger().warn("Keine Gitterpunkte erkannt...")

        except Exception as e:
            self.get_logger().error(f"Fehler im Image-Callback: {e}")

    def extract_grid_points(self, binary_img: np.ndarray):
        """Identifiziert Gitterpunkte und indiziert sie relativ zum RECHTEN Rand (max_u)."""
        contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_circular_contours = []
        detected_areas = []
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 2.0:
                perimeter = cv2.arcLength(cnt, True)
                if perimeter > 0 and ((4 * np.pi * area) / (perimeter ** 2)) > 0.5:
                    valid_circular_contours.append(cnt)
                    detected_areas.append(area)

        if len(valid_circular_contours) < 100:
            return None

        median_target_area = np.median(detected_areas)
        pts_list = []
        for cnt in valid_circular_contours:
            area = cv2.contourArea(cnt)
            if 0.4 * median_target_area < area < 1.8 * median_target_area:
                M = cv2.moments(cnt)
                if M["m00"] != 0:
                    pts_list.append([M["m10"] / M["m00"], M["m01"] / M["m00"]])

        N = len(pts_list)
        pts_real = np.array(pts_list, dtype=np.float64)

        if N < 100:
            return None

        x_coords = pts_real[:, 0].reshape(-1, 1)
        y_coords = pts_real[:, 1].reshape(-1, 1)
        dists = np.sqrt((x_coords - x_coords.T) ** 2 + (y_coords - y_coords.T) ** 2)
        sorted_idx = np.argsort(dists, axis=1)

        angles = []
        for i in range(N):
            for j in range(1, min(5, N)):
                n_idx = sorted_idx[i, j]
                dx = pts_real[n_idx, 0] - pts_real[i, 0]
                dy = pts_real[n_idx, 1] - pts_real[i, 1]
                if abs(dx) > 1e-2 or abs(dy) > 1e-2:
                    angles.append(math.atan2(dy, dx) % (np.pi / 2.0))

        grid_angle = np.median(angles)
        R = np.array([[math.cos(-grid_angle), -math.sin(-grid_angle)],
                      [math.sin(-grid_angle),  math.cos(-grid_angle)]])
        pts_rotated = pts_real @ R.T

        valid_pitches = []
        for i in range(N):
            for j in range(1, min(5, N)):
                n_idx = sorted_idx[i, j]
                dx = abs(pts_rotated[n_idx, 0] - pts_rotated[i, 0])
                dy = abs(pts_rotated[n_idx, 1] - pts_rotated[i, 1])
                if dx > 3 and dy < dx * 0.3: valid_pitches.append(dx)
                elif dy > 3 and dx < dy * 0.3: valid_pitches.append(dy)

        estimated_pitch_px = (np.median(valid_pitches) if len(valid_pitches) > 0 else np.median(dists[:, sorted_idx[:, 1]]))

        grid_dict = {}
        # VERANKERUNG AM RECHTEN RAND: max_u bestimmt die Basis-Spalte (0)
        max_u = np.max(pts_rotated[:, 0])
        min_v = np.min(pts_rotated[:, 1])

        for i, pt in enumerate(pts_rotated):
            approx_col = round((pt[0] - max_u) / estimated_pitch_px)
            approx_row = round((pt[1] - min_v) / estimated_pitch_px)
            expected_u = max_u + approx_col * estimated_pitch_px
            expected_v = min_v + approx_row * estimated_pitch_px

            snap_err = math.sqrt((pt[0] - expected_u) ** 2 + (pt[1] - expected_v) ** 2)
            if snap_err < self.filter_strictness * estimated_pitch_px:
                grid_dict[(approx_col, approx_row)] = pts_real[i]

        return grid_dict

    def wait_for_user_input(self):
        user_input = ""
        print("\n" + "="*60)
        # Durch die Absicherung im Callback ist self.ref_grid_points hier garantiert ein gültiges Dictionary
        print(f">>> REFERENZBILD GESPEICHERT ({len(self.ref_grid_points)} Punkte am rechten Rand verankert) <<<")
        print("Bitte Target verschieben und 'x' drücken + ENTER für Zielbildaufnahme.")
        print("="*60 + "\n")
        
        while user_input.strip().lower() != 'x':
            user_input = input("Eingabe: ")
        
        self.get_logger().info(f"Sammle {self.FRAMES_PER_MEASUREMENT} Bilder für das ZIELBILD...")
        self.state = 'COLLECT_TARGET'

    def _fit_affine_lsq(self, pts_src: np.ndarray, pts_dst: np.ndarray):
        N = len(pts_src)
        ones = np.ones((N, 1), dtype=np.float64)
        X = np.hstack([pts_src.astype(np.float64), ones])
        A_u, _, _, _ = np.linalg.lstsq(X, pts_dst[:, 0].astype(np.float64), rcond=None)
        A_v, _, _, _ = np.linalg.lstsq(X, pts_dst[:, 1].astype(np.float64), rcond=None)
        return np.array([A_u, A_v])

    def calculate_final_displacement(self):
        self.get_logger().info("Berechne finale, rotationsbereinigte Verschiebung...")

        # Schnittmenge über die stabilen IDs vom rechten Rand bilden
        common_keys = set(self.ref_grid_points.keys()).intersection(set(self.final_target_grid_points.keys()))
        
        if len(common_keys) < 100:
            self.get_logger().error("Abbruch: Zu wenige übereinstimmende Punkte am rechten Rand vorhanden!")
            rclpy.shutdown()
            return

        pts_ref_matched = np.array([self.ref_grid_points[k] for k in common_keys])
        pts_tar_matched = np.array([self.final_target_grid_points[k] for k in common_keys])

        # Über Kleinste-Quadrate-Methode (LSQ) die Rotationsmatrix ermitteln
        M = self._fit_affine_lsq(pts_ref_matched, pts_tar_matched)

        # Transformation des Bildmittelpunkts zur Eliminierung des Rotations-Hebelarms
        cx, cy = self.img_width / 2.0, self.img_height / 2.0
        transformed_center = M @ np.array([cx, cy, 1.0], dtype=np.float64)
        
        dx_px = transformed_center[0] - cx
        dx_um = dx_px * self.effective_pixel_size

        # ---------------------------------------------------------
        # CSV EXPORT
        # ---------------------------------------------------------
        csv_path = os.path.join(self.save_dir, "horizontale_verschiebung.csv")
        df_export = pd.DataFrame({
            'Metrik': ['Horizontale_Verschiebung_px', 'Horizontale_Verschiebung_um', 
                       'Punkte_Referenzbild_Anzahl', 'Punkte_Match_Anzahl'],
            'Wert': [round(dx_px, 4), round(dx_um, 4), self.ref_point_count_initial, len(common_keys)]
        })
        df_export.to_csv(csv_path, index=False, sep=';', decimal='.')

        # ---------------------------------------------------------
        # SVG PLOT VISUALISIERUNG
        # ---------------------------------------------------------
        svg_path = os.path.join(self.save_dir, "plot_verschiebung.svg")
        png_path = os.path.join(self.save_dir, "plot_verschiebung.png")
        fig, ax = plt.subplots(figsize=(8, 6))
        
        ax.scatter(pts_ref_matched[:, 0], pts_ref_matched[:, 1], s=20, color='royalblue', alpha=0.6, label='Referenz-Gitter')
        ax.scatter(pts_tar_matched[:, 0], pts_tar_matched[:, 1], s=20, color='crimson', alpha=0.6, label='Ziel-Gitter (Teilmenge)')
        
        # Verschiebungsvektor im Bildzentrum einzeichnen
        ax.quiver(cx, cy, dx_px, 0, angles='xy', scale_units='xy', scale=1, color='darkgreen', 
                  linewidth=3, label=f'Verschiebung $\Delta X$: {dx_um:+.2f} µm')

        ax.set_xlim(0, self.img_width)
        ax.set_ylim(0, self.img_height)
        ax.invert_yaxis()
        ax.set_aspect('equal', adjustable='box')
        ax.set_title('Verschiebungsmessung', fontweight='bold')
        ax.set_xlabel('Pixel U (X-Achse)')
        ax.set_ylabel('Pixel V (Y-Achse)')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left')
        
        fig.tight_layout()
        fig.savefig(svg_path, format='svg')
        fig.savefig(png_path, format='png')
        plt.close(fig)

        # ---------------------------------------------------------
        # ENDAUSGABE IN DER KONSOLE
        # ---------------------------------------------------------
        self.get_logger().info("\n" + "=" * 50)
        self.get_logger().info("FINALES MESSERGEBNIS:")
        self.get_logger().info(f"Horizontale Verschiebung: {dx_um:+.4f} µm")
        self.get_logger().info("=" * 50)

        rclpy.shutdown()

def main():
    rclpy.init()
    node = HeadlessGridDisplacementAnalyzer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()

if __name__ == '__main__':
    main()