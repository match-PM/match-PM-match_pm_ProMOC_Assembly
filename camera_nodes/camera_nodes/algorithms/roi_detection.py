"""
ROI Detection Algorithm for MTF Targets.

Detects slanted edge targets (bars) and squares in images.
Squares are automatically split into 4 edge ROIs for comprehensive MTF measurement.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional

class RoiDetector:
    """Detector for MTF targets (slanted edges and squares)."""

    @staticmethod
    def detect_targets(image: np.ndarray, 
                       min_area: int = 30,
                       square_min_area: int = 100) -> Tuple[np.ndarray, List[tuple], List[tuple]]:
        """
        Detects potential MTF targets in the image.

        Args:
            image: Input image (grayscale or color)
            min_area: Minimum contour area to consider
            square_min_area: Minimum area for squares (to filter noise/text)

        Returns:
            vis_img: Debug image with drawn contours
            rois_bars: List of rotated rects (minAreaRect) for bar targets
            rois_squares: List of rotated rects (minAreaRect) for square targets
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            vis_img = image.copy()
        else:
            gray = image
            vis_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        # Normalize and Blur
        img_norm = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
        blur = cv2.GaussianBlur(img_norm, (5, 5), 0)
        
        # Otsu Thresholding
        _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Find Contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        rois_bars = []
        rois_squares = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue

            # Rotated Rectangle
            rect = cv2.minAreaRect(cnt)
            (center, (w, h), angle) = rect
            
            # Normalize width/height (w always smaller)
            if w > h:
                w, h = h, w
            
            aspect_ratio = h / w if w > 0 else 0
            
            box = np.int32(cv2.boxPoints(rect))

            # Logic Switch
            # Case A: MTF Bar (Long & Narrow)
            if 2.5 < aspect_ratio < 20.0:
                rois_bars.append(rect)
                cv2.drawContours(vis_img, [box], 0, (0, 255, 0), 2) # Green for bars

            # Case B: Square (Quadratic & Large enough)
            elif 0.8 < aspect_ratio < 1.3 and area > square_min_area:
                rois_squares.append(rect)
                cv2.drawContours(vis_img, [box], 0, (255, 0, 0), 2) # Blue for squares

        return vis_img, rois_bars, rois_squares

    @staticmethod
    def split_square_into_edges(image: np.ndarray, square_rect: tuple) -> List[np.ndarray]:
        """
        Splits a detected square ROI into 4 measurable edge ROIs.
        Avoids warping to preserve raw pixel data for MTF accuracy.
        """
        (center_x, center_y), (w, h), angle = square_rect
        
        # Sicherstellen, dass wir auf Graustufen arbeiten
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        box = cv2.boxPoints(square_rect)
        box = np.int32(box) 
        
        # Sortieren der Punkte: Top-Left, Top-Right, Bottom-Right, Bottom-Left
        # Dies funktioniert zuverlässig für Rotation < 45 Grad
        cnt_pts = sorted(box, key=lambda p: p[1]) # Sort by Y
        top_pts = sorted(cnt_pts[:2], key=lambda p: p[0]) # Top by X
        bot_pts = sorted(cnt_pts[2:], key=lambda p: p[0]) # Bottom by X
        
        tl, tr = top_pts
        bl, br = bot_pts # Beachte: bot_pts[0] ist links (kleineres x), bot_pts[1] ist rechts
        
        edges_rois = []
        
        # Crop Size: 40% der Seitenlänge garantiert Ausschluss der Ecken
        side_len = min(w, h)
        crop_size = int(side_len * 0.4) 
        crop_size = max(16, crop_size) # Mindestgröße sicherstellen
        half_crop = crop_size // 2
        
        # Reihenfolge: Oben, Rechts, Unten, Links
        edge_pairs = [(tl, tr), (tr, br), (br, bl), (bl, tl)]
        
        img_h, img_w = gray.shape[:2]
        
        for p1, p2 in edge_pairs:
            # Mittelpunkt der Kante berechnen
            cx = (p1[0] + p2[0]) / 2
            cy = (p1[1] + p2[1]) / 2
            
            # Koordinaten für den Crop
            ix = int(cx - half_crop)
            iy = int(cy - half_crop)
            
            # Boundary Checks (wichtig!)
            # Verhindert Abstürze am Bildrand
            if ix < 0: ix = 0
            if iy < 0: iy = 0
            if ix + crop_size > img_w: ix = img_w - crop_size
            if iy + crop_size > img_h: iy = img_h - crop_size
            
            # Validierung: Ist der Crop innerhalb des Bildes möglich?
            if ix < 0 or iy < 0 or crop_size <= 0:
                continue # Überspringen, falls ROI außerhalb

            roi = gray[iy:iy+crop_size, ix:ix+crop_size]
            
            # Validierung: Leere ROIs abfangen
            if roi.size > 0:
                edges_rois.append(roi)
            
        return edges_rois

    @staticmethod
    def calculate_michelson_contrast(roi: np.ndarray) -> float:
        """Calculates Michelson contrast: (max - min) / (max + min)."""
        if roi.size == 0:
            return 0.0
        min_val = float(np.min(roi))
        max_val = float(np.max(roi))
        denominator = max_val + min_val + 1e-6
        return (max_val - min_val) / denominator

    @staticmethod
    def create_debug_visualization(edge_rois: List[np.ndarray]) -> Tuple[np.ndarray, int]:
        """
        Creates a combined debug image showing the detected ROIs/Edges.
        Returns (canvas_image, tile_width).
        """
        if not edge_rois:
            return np.zeros((100, 100, 3), dtype=np.uint8), 0

        n_images = len(edge_rois)
        # Labels (Cycle if more than 4, or just generic)
        default_labels = ["Top", "Right", "Bottom", "Left"]
        
        # Determine tile size (max dimensions)
        max_h = max(r.shape[0] for r in edge_rois)
        max_w = max(r.shape[1] for r in edge_rois)
        
        # Pad tile size for text
        tile_h = max_h + 60
        tile_w = max(max_w, 150) # Min width for text
        
        # Create canvas (1 row, N columns)
        canvas = np.zeros((tile_h, tile_w * n_images, 3), dtype=np.uint8)
        
        for i, roi in enumerate(edge_rois):
            # Convert to BGR if needed
            if len(roi.shape) == 2:
                roi_bgr = cv2.cvtColor(roi, cv2.COLOR_GRAY2BGR)
            else:
                roi_bgr = roi
            
            # Contrast
            contrast = RoiDetector.calculate_michelson_contrast(roi)
            
            # Place ROI centered in tile
            h, w = roi.shape[:2]
            x_off = i * tile_w + (tile_w - w) // 2
            y_off = 30 # space for title
            
            canvas[y_off:y_off+h, x_off:x_off+w] = roi_bgr
            
            # Draw Crosshair
            cx = x_off + w // 2
            cy = y_off + h // 2
            cv2.line(canvas, (cx, y_off), (cx, y_off+h), (0, 0, 255), 1)
            cv2.line(canvas, (x_off, cy), (x_off+w, cy), (0, 0, 255), 1)
            
            # Text info
            label = default_labels[i] if i < 4 else f"ROI {i+1}"
            color = (0, 255, 0) if contrast > 0.4 else (0, 0, 255)
            cv2.putText(canvas, label, (i * tile_w + 10, 20), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(canvas, f"C:{contrast:.2f}", (i * tile_w + 10, tile_h - 15), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        return canvas, tile_w
