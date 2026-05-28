#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
import pandas as pd
import os
import math
import sys

# NEU: Headless-Modus für Matplotlib aktivieren (MUSS vor plt stehen)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

class HeadlessScientificAnalyzer(Node):

    def __init__(self):
        super().__init__('headless_scientific_analyzer')
        self.bridge = CvBridge()

        # --- ZIELPFAD FÜR DATENSPEICHERUNG ---
        self.save_dir = "/home/pmlab/Dokumente/Messungen/Yannis Wesser/Messungen/V0012_MTF0_Verz1_Versch0_RotY0_RotP0_Transl0_Cam2"
        os.makedirs(self.save_dir, exist_ok=True)

        # --- PHYSIKALISCHE KONFIGURATION ---
        self.image_topic = "/promoc/promoc_camera/stream0/image_raw"
        self.grid_spacing_mm = 0.1   # Realer Gitterabstand: 100 µm

        # --- MESSSTRATEGIE ---
        self.FRAMES_PER_MEASUREMENT = 10
        self.TOTAL_MEASUREMENTS_NEEDED = 100

        # --- FILTER-KONFIGURATION ---
        self.filter_strictness = 0.25
        self.paraxial_threshold_percent = 0.05

        # --- DATENSPEICHER ---
        self.frame_buffer = []
        self.all_points_data = []

        # Speicher für den 2D-Sensor-Plot
        self.all_sensor_pts = []
        self.all_cods = []
        self.img_width = 0
        self.img_height = 0

        self.measurement_counter = 0
        self.is_finished = False

        self.subscription = self.create_subscription(
            Image, self.image_topic, self.image_callback, 10)

        self.get_logger().info("=" * 60)
        self.get_logger().info("WISSENSCHAFTLICHE VERZEICHNUNGSANALYSE")
        self.get_logger().info("Modus: Schnurrbart-Verzeichnung (3-Parameter-Polynom)")
        self.get_logger().info("Export: SVG-Plots & Excel-kompatible CSV")
        self.get_logger().info(f"Speicherpfad: {self.save_dir}")
        self.get_logger().info("=" * 60)

    def image_callback(self, msg):
        if self.is_finished:
            return
        try:
            raw_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
            gray = raw_img[:, :, 1] if len(raw_img.shape) == 3 else raw_img

            self.img_height, self.img_width = gray.shape

            if gray.dtype != np.uint8:
                gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            if np.median(blurred) > 127:
                _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            else:
                _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            self.frame_buffer.append(binary.astype(np.float32))
            if len(self.frame_buffer) == self.FRAMES_PER_MEASUREMENT:
                denoised_binary = np.mean(self.frame_buffer, axis=0).astype(np.uint8)
                self.frame_buffer.clear()
                self.process_denoised_frame(denoised_binary)
        except Exception as e:
            self.get_logger().error(f"Fehler im Image-Callback: {e}")

    def _fit_affine_lsq(self, pts_src: np.ndarray, pts_dst: np.ndarray):
        N = len(pts_src)
        ones = np.ones((N, 1), dtype=np.float64)
        X = np.hstack([pts_src.astype(np.float64), ones])

        A_u, _, _, _ = np.linalg.lstsq(X, pts_dst[:, 0].astype(np.float64), rcond=None)
        A_v, _, _, _ = np.linalg.lstsq(X, pts_dst[:, 1].astype(np.float64), rcond=None)

        return np.array([A_u, A_v])

    def process_denoised_frame(self, binary_img: np.ndarray):
        self.measurement_counter += 1

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

        if len(valid_circular_contours) < 15:
            self.measurement_counter -= 1
            return

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

        if N < 15:
            self.measurement_counter -= 1
            return

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

        estimated_pitch_px = (np.median(valid_pitches) if len(valid_pitches) > 0
                              else np.median(dists[:, sorted_idx[:, 1]]))

        pts_ideal_mm_list = []
        pts_real_filtered = []
        min_u, min_v = np.min(pts_rotated[:, 0]), np.min(pts_rotated[:, 1])

        for i, pt in enumerate(pts_rotated):
            approx_col = round((pt[0] - min_u) / estimated_pitch_px)
            approx_row = round((pt[1] - min_v) / estimated_pitch_px)

            # NEU: Punkte ausschließen, die weniger als 15 Pixel vom Sensorrand entfernt sind
            margin = 15
            sensor_u_pos = pts_real[i][0]
            sensor_v_pos = pts_real[i][1]
            if (sensor_u_pos < margin or sensor_u_pos > (self.img_width - margin) or
                sensor_v_pos < margin or sensor_v_pos > (self.img_height - margin)):
                continue  # Überspringe diesen abgeschnittenen Randpunkt!

            expected_u = min_u + approx_col * estimated_pitch_px
            expected_v = min_v + approx_row * estimated_pitch_px

            snap_err = math.sqrt((pt[0] - expected_u) ** 2 + (pt[1] - expected_v) ** 2)
            if snap_err < self.filter_strictness * estimated_pitch_px:
                pts_ideal_mm_list.append([approx_col * self.grid_spacing_mm,
                                          approx_row * self.grid_spacing_mm])
                pts_real_filtered.append(pts_real[i])

        pts_ideal_mm   = np.array(pts_ideal_mm_list,  dtype=np.float64)
        pts_real_final = np.array(pts_real_filtered,  dtype=np.float64)

        num_points = len(pts_real_final)
        self.get_logger().info(f"Punkte erkannt in diesem Frame: {num_points}")

        if num_points < 700:
            self.get_logger().warn(
                f"WARNUNG: Nur {num_points} Punkte erkannt! (Ziel > 700). "
                "Die Qualität der Verzeichnungsmessung könnte sinken.")

        if num_points < 250:
            self.measurement_counter -= 1
            return

        mean_ideal = np.mean(pts_ideal_mm, axis=0)
        pts_ideal_centered = pts_ideal_mm - mean_ideal

        center_u, center_v = np.mean(pts_real_final, axis=0)
        dists_to_center = np.sqrt((pts_real_final[:, 0] - center_u) ** 2 +
                                  (pts_real_final[:, 1] - center_v) ** 2)

        threshold_dist = np.percentile(dists_to_center, self.paraxial_threshold_percent * 100)
        paraxial_mask = dists_to_center <= threshold_dist

        A_affine = self._fit_affine_lsq(pts_ideal_centered[paraxial_mask],
                                         pts_real_final[paraxial_mask])

        ones_all = np.ones((len(pts_ideal_centered), 1), dtype=np.float64)
        X_all = np.hstack([pts_ideal_centered, ones_all])
        pts_ideal_px = X_all @ A_affine.T

        cod_x, cod_y = A_affine[0, 2], A_affine[1, 2]

        self.all_sensor_pts.append(pts_real_final)
        self.all_cods.append([cod_x, cod_y])

        r_ideal_px = np.sqrt((pts_ideal_px[:, 0]  - cod_x) ** 2 +
                             (pts_ideal_px[:, 1]  - cod_y) ** 2)
        r_real_px  = np.sqrt((pts_real_final[:, 0] - cod_x) ** 2 +
                             (pts_real_final[:, 1] - cod_y) ** 2)
        r_ideal_mm_field = np.sqrt(pts_ideal_centered[:, 0] ** 2 +
                                   pts_ideal_centered[:, 1] ** 2)

        for i in range(len(pts_real_final)):
            distortion_percent = (0.0 if r_ideal_px[i] < 1e-3
                                  else ((r_real_px[i] - r_ideal_px[i]) / r_ideal_px[i]) * 100.0)
            
            # NEU: Berechnung des Polarwinkels relativ zum Verzeichnungszentrum (CoD)
            angle_rad = math.atan2(pts_real_final[i, 1] - cod_y, pts_real_final[i, 0] - cod_x)

            # ERWEITERT: Zusätzliche Diagnose-Metriken im Dictionary speichern
            self.all_points_data.append({
                'Messung_Nr': self.measurement_counter,
                'Feldhoehe_r_mm': r_ideal_mm_field[i],
                'Verzeichnung_Prozent': distortion_percent,
                'Sensor_U': pts_real_final[i, 0],
                'Sensor_V': pts_real_final[i, 1],
                'Polar_Winkel_Rad': angle_rad
            })

        if self.measurement_counter >= self.TOTAL_MEASUREMENTS_NEEDED:
            self.is_finished = True
            self.generate_plots_and_tables()

    def generate_plots_and_tables(self):
        self.get_logger().info("Generiere Plots und Tabellen...")
        df = pd.DataFrame(self.all_points_data)

        max_r = df['Feldhoehe_r_mm'].max()
        bins_edges = np.linspace(0.0, max_r, 16)
        df['Feldhoehe_Bin'] = pd.cut(df['Feldhoehe_r_mm'], bins=bins_edges, include_lowest=True)

        stats = df.groupby('Feldhoehe_Bin', observed=False).agg(
            Feldhoehe_mm=('Feldhoehe_r_mm', 'mean'),
            Verzeichnung_Mittelwert_Prozent=('Verzeichnung_Prozent', 'mean'),
            Sigma_Raw=('Verzeichnung_Prozent', 'std'),
            Anzahl_Punkte=('Verzeichnung_Prozent', 'count'),
        ).dropna().reset_index(drop=True)

        stats['Sigma_Raw'] = stats['Sigma_Raw'].fillna(0.0)
        stats['3_Sigma_Prozent'] = 3 * stats['Sigma_Raw']
        stats['Anzahl_Punkte'] = (stats['Anzahl_Punkte'] / self.TOTAL_MEASUREMENTS_NEEDED).round(0).astype(int)

        r_fit = stats['Feldhoehe_mm'].to_numpy()
        d_fit = stats['Verzeichnung_Mittelwert_Prozent'].to_numpy()
        w     = stats['Anzahl_Punkte'].to_numpy().astype(float)

        # --- 3-PARAMETER-POLYNOMFIT (Schnurrbart-fähig) ---

        w_sqrt = np.sqrt(w)
        X_poly = np.column_stack([r_fit**2, r_fit**4, r_fit**6])
        coeffs, _, _, _ = np.linalg.lstsq(X_poly * w_sqrt[:, None], d_fit * w_sqrt, rcond=None)
        k1, k2, k3 = coeffs
        r_dense = np.linspace(0, max_r, 400)
        d_poly = k1*r_dense**2 + k2*r_dense**4 + k3*r_dense**6

        # --- NULLDURCHGÄNGE BERECHNEN (Schnurrbart-Erkennung) ---
        zero_crossings = []
        for i in range(len(d_poly) - 1):
            if d_poly[i] * d_poly[i + 1] < 0:
                r_zero = (r_dense[i]
                          - d_poly[i] * (r_dense[i + 1] - r_dense[i])
                          / (d_poly[i + 1] - d_poly[i]))
                zero_crossings.append(r_zero)

        # ---------------------------------------------------------
        # CSV EXPORT
        # ---------------------------------------------------------
        csv_path = os.path.join(self.save_dir, "verzeichnungsdaten_statistik.csv")
        stats.to_csv(csv_path, index=False, sep=';', decimal='.')

        poly_path = os.path.join(self.save_dir, "polynom_koeffizienten.csv")
        pd.DataFrame({
            'k1': [round(k1, 6)],
            'k2': [round(k2, 6)],
            'k3': [round(k3, 6)]
        }).to_csv(poly_path, index=False, sep=';', decimal='.')

        self.get_logger().info(f"Daten wurden gespeichert in {csv_path}")

        # ---------------------------------------------------------
        # PLOTS (SVG)
        # ---------------------------------------------------------
        fh = stats['Feldhoehe_mm'].to_numpy()
        mu = stats['Verzeichnung_Mittelwert_Prozent'].to_numpy()
        s3 = stats['3_Sigma_Prozent'].to_numpy()

        # Y-Achse oben um 20% verlängern, um Platz für die Legende zu schaffen
        y_max = max_r * 1.20 

        # NEU: setup_plot nimmt jetzt x_lim entgegen, um jeden Plot passend zu zoomen
        def setup_plot(title, x_lim):
            fig, ax = plt.subplots(figsize=(8, 10))
            
            # Barrel-Region (negativ) = Tonnenverzeichnung
            ax.axvspan(-x_lim, 0, color='#FFF3CD', alpha=0.5, label='Tonnen-Verzeichnung')
            # Pincushion-Region (positiv) = Kissenverzeichnung
            ax.axvspan(0, x_lim, color='#D4EDDA', alpha=0.5, label='Kissen-Verzeichnung')
            ax.axvline(0, color='black', linestyle='-', linewidth=1.0)
            
            ax.set_xlim(-x_lim, x_lim)
            ax.set_ylim(0, y_max)
            ax.set_title(title, fontsize=12, fontweight='bold', pad=15)
            ax.set_xlabel('Relative radiale Verzeichnung $D(r)$ [%]', fontsize=11)
            ax.set_ylabel('Feldhöhe $r$ [mm]', fontsize=11)
            ax.grid(True, alpha=0.3)
            return fig, ax
        
        # Korrekte Anzeige der Polynomkoeffizienten im Plot-Label
        term1 = f"{k1:.4f}r^2"
        term2 = f" - {abs(k2):.4f}r^4" if k2 < 0 else f" + {k2:.4f}r^4"
        term3 = f" - {abs(k3):.4f}r^6" if k3 < 0 else f" + {k3:.4f}r^6"
        poly_label_clean = f"Polynomfit: $D(r) = {term1}{term2}{term3}$"

        # ---------------------------------------------------------
        # PLOT 1: Kombinierte Analyse (Mittelwert + Fit)
        # Optimaler Zoom direkt auf den Verlauf der Kurven
        # ---------------------------------------------------------
        x_lim_comb = max(0.05, abs(mu).max() * 1.2, abs(d_poly).max() * 1.2)
        
        fig_comb, ax_comb = setup_plot('Verzeichnung — Mittelwert und Polynomfit (n=100)', x_lim_comb)
        
        ax_comb.plot(mu, fh, 'o-', color='navy', markersize=5, linewidth=1.5,
                     label='Kurve der Mittelwerte')
        ax_comb.plot(d_poly, r_dense, '--', color='crimson', linewidth=2.0,
                     label=poly_label_clean)
        
        for r_z in zero_crossings:
            ax_comb.axhline(r_z, color='darkorange', linestyle=':', linewidth=1.5,
                            label=f'Vorzeichenwechsel r = {r_z:.3f} mm')
        
        # Doppelte Einträge in der Legende verhindern
        handles, labels = ax_comb.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax_comb.legend(by_label.values(), by_label.keys(), loc='upper left', fontsize=10, framealpha=0.9)
        
        fig_comb.tight_layout()
        fig_comb.savefig(os.path.join(self.save_dir, "plot_01_analyse_kombiniert.svg"), format='svg')
        fig_comb.savefig(os.path.join(self.save_dir, "plot_01_analyse_kombiniert.png"), format='png', dpi=300)
        plt.close(fig_comb)

        # ---------------------------------------------------------
        # PLOT 2: Kombiniert (Alle)
        # Braucht die maximale Breite wegen des 3-Sigma Bereichs
        # ---------------------------------------------------------
        x_lim_2 = max(0.1,
                      abs((mu - s3)).max() * 1.1,
                      abs((mu + s3)).max() * 1.1,
                      abs(d_poly).max() * 1.1)
        
        fig2, ax2 = setup_plot('Verzeichnung — Mittelwert, ± 3σ und Polynomfit (n=100)', x_lim_2)
        ax2.fill_betweenx(fh, mu - s3, mu + s3, color='royalblue', alpha=0.15,
                          label='3 $\sigma$ (99,7 %)')
        ax2.plot(mu, fh, 'o-', color='navy', markersize=4, linewidth=1.5,
                 label='Kurve der Mittelwerte')
        ax2.plot(d_poly, r_dense, '--', color='crimson', linewidth=2.0,
                 label=poly_label_clean)
        for r_z in zero_crossings:
            ax2.axhline(r_z, color='darkorange', linestyle=':', linewidth=1.5,
                        label=f'Vorzeichenwechsel r = {r_z:.3f} mm')
        
        ax2.legend(loc='upper left', fontsize=10, framealpha=0.9)
        fig2.tight_layout()
        
        fig2.savefig(os.path.join(self.save_dir, "plot_02_kombiniert.svg"), format='svg')
        fig2.savefig(os.path.join(self.save_dir, "plot_02_kombiniert.png"), format='png', dpi=300)
        plt.close(fig2)

        # ---------------------------------------------------------
        # PLOT 03: Sensoransicht (Punkte + optisches Zentrum)
        # ---------------------------------------------------------
        fig3, ax3 = plt.subplots(figsize=(8, 8))
        
        # Holt die Punkte und das CoD der letzten gültigen Messung
        last_pts = self.all_sensor_pts[-1]
        last_cod = self.all_cods[-1]

        # Punkte und Zentrum einzeichnen
        ax3.scatter(last_pts[:, 0], last_pts[:, 1], s=3, color='royalblue',
                    alpha=0.6, label=f'Erkannte Gitterpunkte (n={len(last_pts)})')
        ax3.plot(last_cod[0], last_cod[1], 'rX', markersize=12, markeredgewidth=2,
                 label=f'Center of Distortion (CoD):\nU={last_cod[0]:.1f} px, V={last_cod[1]:.1f} px')

        # Sensor-Grenzen dynamisch oder fix setzen
        ax3.set_xlim(0, self.img_width if self.img_width > 0 else 2464)
        ax3.set_ylim(0, self.img_height if self.img_height > 0 else 2056)
        ax3.invert_yaxis()  # Bildkoordinatenursprung ist oben links!

        ax3.set_aspect('equal', adjustable='box')
        ax3.set_title('Sensoransicht: Punktabdeckung & Optisches Zentrum', fontsize=12, fontweight='bold', pad=15)
        ax3.set_xlabel('Sensor X [Pixel]', fontsize=11)
        ax3.set_ylabel('Sensor Y [Pixel]', fontsize=11)
        ax3.legend(loc='upper right', fontsize=10, framealpha=0.9)
        ax3.grid(True, alpha=0.3)
        
        fig3.tight_layout()
        
        # Parallel-Export in beiden Formaten
        fig3.savefig(os.path.join(self.save_dir, "plot_03_sensor_punkte.svg"), format='svg')
        fig3.savefig(os.path.join(self.save_dir, "plot_03_sensor_punkte.png"), format='png', dpi=300)
        plt.close(fig3)

        # ---------------------------------------------------------
        # NEU: PLOT 04 - DIAGNOSTISCHE FEHLERANALYSE (SPEZIELL FÜR BIN 10 & 11)
        # ---------------------------------------------------------
        self.get_logger().info("Erzeuge messtechnischen Diagnose-Plot...")
        fig4, (ax4_1, ax4_2) = plt.subplots(1, 2, figsize=(16, 7))

        # Grenzen für Bin 10 und Bin 11 ermitteln (Kantenindizes 9, 10, 11)
        r_bin10_start = bins_edges[9]
        r_bin11_end = bins_edges[12]
        
        # Daten für die fehlerhaften Bins isolieren (letzter Frame als repräsentative Stichprobe)
        df_last_frame = df[df['Messung_Nr'] == self.measurement_counter]
        df_bins_10_11 = df_last_frame[(df_last_frame['Feldhoehe_r_mm'] >= r_bin10_start) & 
                                      (df_last_frame['Feldhoehe_r_mm'] <= r_bin11_end)]

        # Dynamische Skalierung der Farbkarte (95%-Perzentil fängt extreme Ausreißer ab)
        v_max_cmap = max(1.0, np.percentile(np.abs(df_last_frame['Verzeichnung_Prozent']), 95))

        # Subplot 1: Räumliche Fehlerkarte auf dem Sensor
        sc = ax4_1.scatter(df_last_frame['Sensor_U'], df_last_frame['Sensor_V'], 
                            c=df_last_frame['Verzeichnung_Prozent'], 
                            cmap='coolwarm', vmin=-v_max_cmap, vmax=v_max_cmap, s=15, edgecolors='none')
        
        # Umrechnung von mm Feldhöhe in Pixelradius für die Ring-Visualisierung
        cod_x, cod_y = last_cod
        pts_r_px = np.sqrt((df_last_frame['Sensor_U'] - cod_x)**2 + (df_last_frame['Sensor_V'] - cod_y)**2)
        scale_mm_to_px = np.mean(pts_r_px / df_last_frame['Feldhoehe_r_mm'])
        
        # Ringe für Bin 10 und 11 einzeichnen
        circle_start = plt.Circle((cod_x, cod_y), r_bin10_start * scale_mm_to_px, color='black', fill=False, linestyle='--', alpha=0.5)
        circle_end = plt.Circle((cod_x, cod_y), r_bin11_end * scale_mm_to_px, color='black', fill=False, linestyle='--', alpha=0.5)
        ax4_1.add_patch(circle_start)
        ax4_1.add_patch(circle_end)

        ax4_1.plot(cod_x, cod_y, 'kX', markersize=10, label='CoD')
        ax4_1.set_xlim(0, self.img_width if self.img_width > 0 else 2464)
        ax4_1.set_ylim(0, self.img_height if self.img_height > 0 else 2056)
        ax4_1.invert_yaxis()
        ax4_1.set_aspect('equal')
        ax4_1.set_title('Räumliche Verteilungs-Map (Farbe = Verzeichnung %)\nGestrichelte Linien = Bereich von Bin 10 & 11', fontsize=11, fontweight='bold')
        ax4_1.set_xlabel('Sensor U [px]')
        ax4_1.set_ylabel('Sensor V [px]')
        fig4.colorbar(sc, ax=ax4_1, label='Verzeichnung [%]')

        # Subplot 2: Verzeichnung vs. Polarwinkel in Bin 10 & 11
        if len(df_bins_10_11) > 0:
            angles_deg = np.degrees(df_bins_10_11['Polar_Winkel_Rad'])
            ax4_2.scatter(angles_deg, df_bins_10_11['Verzeichnung_Prozent'], color='crimson', s=25, alpha=0.8, label='Punkte in Bin 10 & 11')
            ax4_2.axhline(0, color='black', linestyle='-', alpha=0.5)
            ax4_2.set_xlim(-180, 180)
            ax4_2.set_title('Analyse für Bin 10 & 11: Verzeichnung vs. Winkel\n[Sinusform = Target-Kippung | Einzelne Punkte = Match-Fehler]', fontsize=11, fontweight='bold')
            ax4_2.set_xlabel('Polarwinkel auf dem Sensor [Grad°]')
            ax4_2.set_ylabel('Berechnete Verzeichnung [%]')
            ax4_2.grid(True, alpha=0.3)
            ax4_2.legend()
        else:
            ax4_2.text(0.5, 0.5, 'Keine Daten im betroffenen Bin-Bereich.', ha='center', va='center')

        fig4.tight_layout()
        fig4.savefig(os.path.join(self.save_dir, "plot_04_diagnose_standardabweichung.svg"), format='svg')
        fig4.savefig(os.path.join(self.save_dir, "plot_04_diagnose_standardabweichung.png"), format='png', dpi=300)
        plt.close(fig4)

        # --- ABBRECH-LOGIK AM ENDE DER FUNKTION ---
        if len(zero_crossings) > 0:
            self.get_logger().info(f"Schnurrbart-Verzeichnung erkannt! Vorzeichenwechsel bei r = {[round(z, 4) for z in zero_crossings]} mm")
        else:
            self.get_logger().info("Kein Vorzeichenwechsel im Polynomfit – keine Schnurrbart-Verzeichnung.")

        self.get_logger().info(f"Polynomkoeffizienten: k1={k1:.6f}, k2={k2:.6f}, k3={k3:.6f}")
        self.get_logger().info(f"Auswertung beendet! Diagnose-Plots liegen in: {self.save_dir}")
        
        # NEU: Verbindung sauber trennen und Node beenden
        self.destroy_subscription(self.subscription)
        rclpy.shutdown()
        sys.exit(0)
        ## PLOT 4: Sensoransicht (Punkte + optisches Zentrum)
        #fig4, ax4 = plt.subplots(figsize=(7, 7))
        #last_pts = self.all_sensor_pts[-1]
        #last_cod = self.all_cods[-1]

        #ax4.scatter(last_pts[:, 0], last_pts[:, 1], s=2, color='royalblue',
         #           alpha=0.7, label='Erkannte Punkte')
        #ax4.plot(last_cod[0], last_cod[1], 'rX', markersize=12,
         #        label='Center of Distortion (CoD)')

        #ax4.set_xlim(0, self.img_width  if self.img_width  > 0 else 2000)
        #ax4.set_ylim(0, self.img_height if self.img_height > 0 else 2000)
        #ax4.invert_yaxis()

        #ax4.set_aspect('equal', adjustable='box')
        #ax4.set_title('Sensoransicht: Erkannte Punkte & Optisches Zentrum',
        #              fontweight='bold')
        #ax4.set_xlabel('Pixel U')
        #ax4.set_ylabel('Pixel V')
        #ax4.legend(loc='upper right')
        #ax4.grid(True, alpha=0.3)
        #fig4.tight_layout()
        #fig4.savefig(os.path.join(self.save_dir, "plot_04_sensor_punkte.svg"), format='svg')
        #fig4.savefig(os.path.join(self.save_dir, "plot_04_sensor_punkte.png"), format='png', dpi=300)
        #plt.close(fig4)

        # --- SCHNURRBART-DIAGNOSE ---
        if len(zero_crossings) > 0:
            self.get_logger().info(
                f"Schnurrbart-Verzeichnung erkannt! "
                f"Vorzeichenwechsel bei r = {[round(z, 4) for z in zero_crossings]} mm")
        else:
            self.get_logger().info(
                "Kein Vorzeichenwechsel im Polynomfit – keine Schnurrbart-Verzeichnung.")

        self.get_logger().info(
            f"Polynomkoeffizienten: k1={k1:.6f}, k2={k2:.6f}, k3={k3:.6f}")
        self.get_logger().info(
            f"Auswertung beendet! Dateien liegen in: {self.save_dir}")
        rclpy.shutdown()


def main():
    rclpy.init()
    node = HeadlessScientificAnalyzer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()


if __name__ == '__main__':
    main()