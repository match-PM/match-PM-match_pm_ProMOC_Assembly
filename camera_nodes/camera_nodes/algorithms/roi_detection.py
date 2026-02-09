"""
ROI Detection Algorithm for MTF Targets.

Detects slanted edge targets (bars) and squares in images.
Squares are automatically split into 4 edge ROIs for comprehensive MTF measurement.

Features:
- Adaptive thresholding with Otsu fallback
- Contrast pre-filtering to skip low-quality ROIs
- Multi-target support for field measurements
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass


# Minimum contrast threshold for usable MTF edges
MIN_CONTRAST_THRESHOLD = 0.2


@dataclass
class DetectedTarget:
    """Represents a detected MTF target with metadata."""
    rect: tuple  # minAreaRect
    target_type: str  # 'bar' or 'square'
    area: float
    aspect_ratio: float
    contrast: float = 0.0  # Filled after extraction
    position: Tuple[int, int] = (0, 0)  # Center position
    
    @property
    def is_valid_for_mtf(self) -> bool:
        """Check if target has sufficient contrast for MTF measurement."""
        return self.contrast >= MIN_CONTRAST_THRESHOLD


@dataclass
class EdgeROI:
    """
    Detailed info about an extracted edge ROI for MTF measurement.
    
    This dataclass provides full traceability of which edge was used
    and its exact position in the image.
    """
    image: np.ndarray                     # The extracted ROI image
    bbox: Tuple[int, int, int, int]       # (x, y, width, height) in original image
    edge_direction: str                    # 'vertical' or 'horizontal'
    edge_name: str                         # 'top', 'right', 'bottom', 'left'
    contrast: float = 0.0                  # Michelson contrast
    parent_center: Tuple[int, int] = (0, 0)  # Center of parent rectangle
    
    @property
    def is_valid(self) -> bool:
        """Check if edge has sufficient contrast for MTF."""
        return self.contrast >= MIN_CONTRAST_THRESHOLD and self.image.size > 0
    
    @property
    def center(self) -> Tuple[int, int]:
        """Center point of this ROI."""
        x, y, w, h = self.bbox
        return (x + w // 2, y + h // 2)
    
    def format_coords(self) -> str:
        """Format coordinates as string for display."""
        x, y, w, h = self.bbox
        return f"x={x},y={y} {w}x{h}px"


class RoiDetector:
    """Detector for MTF targets (slanted edges and squares).
    
    Features:
    - Adaptive thresholding with Otsu fallback for robust detection
    - Contrast pre-filter to skip unusable ROIs early
    - Multi-target support returning all detected targets
    """

    @staticmethod
    def detect_targets(image: np.ndarray, 
                       min_area: int = 30,
                       square_min_area: int = 100,
                       use_adaptive: bool = True) -> Tuple[np.ndarray, List[tuple], List[tuple]]:
        """
        Detects potential MTF targets in the image.

        Args:
            image: Input image (grayscale or color)
            min_area: Minimum contour area to consider
            square_min_area: Minimum area for squares (to filter noise/text)
            use_adaptive: Try adaptive thresholding if Otsu finds few contours

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
        
        # Try Otsu thresholding first
        _, thresh_otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours_otsu, _ = cv2.findContours(thresh_otsu, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Fallback to adaptive thresholding if Otsu finds too few contours
        contours = contours_otsu
        if use_adaptive and len(contours_otsu) < 2:
            # Adaptive thresholding works better with uneven lighting
            thresh_adaptive = cv2.adaptiveThreshold(
                blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            contours_adaptive, _ = cv2.findContours(
                thresh_adaptive, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            if len(contours_adaptive) > len(contours_otsu):
                contours = contours_adaptive
        
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
                cv2.drawContours(vis_img, [box], 0, (0, 255, 0), 2)  # Green for bars

            # Case B: Square (Quadratic & Large enough)
            elif 0.8 < aspect_ratio < 1.3 and area > square_min_area:
                rois_squares.append(rect)
                cv2.drawContours(vis_img, [box], 0, (255, 0, 0), 2)  # Blue for squares

        return vis_img, rois_bars, rois_squares

    @staticmethod
    def detect_all_targets(image: np.ndarray,
                           min_area: int = 30,
                           square_min_area: int = 100,
                           compute_contrast: bool = True) -> List[DetectedTarget]:
        """
        Detects all MTF targets and returns them as structured objects.
        
        This is the multi-target version that returns ALL detected targets
        with metadata including contrast values.
        
        Args:
            image: Input image (grayscale or color)
            min_area: Minimum contour area
            square_min_area: Minimum area for squares
            compute_contrast: Pre-compute contrast for each target
            
        Returns:
            List of DetectedTarget objects, sorted by area (largest first)
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        _, bars, squares = RoiDetector.detect_targets(
            image, min_area, square_min_area, use_adaptive=True
        )
        
        targets = []
        
        # Process bars
        for rect in bars:
            (cx, cy), (w, h), angle = rect
            area = w * h
            aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0
            
            target = DetectedTarget(
                rect=rect,
                target_type='bar',
                area=area,
                aspect_ratio=aspect_ratio,
                position=(int(cx), int(cy))
            )
            
            if compute_contrast:
                # Extract ROI and compute contrast
                box = cv2.boxPoints(rect)
                x, y, bw, bh = cv2.boundingRect(np.int32(box))
                x = max(0, x)
                y = max(0, y)
                roi = gray[y:y+bh, x:x+bw]
                if roi.size > 0:
                    target.contrast = RoiDetector.calculate_michelson_contrast(roi)
            
            targets.append(target)
        
        # Process squares
        for rect in squares:
            (cx, cy), (w, h), angle = rect
            area = w * h
            aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0
            
            target = DetectedTarget(
                rect=rect,
                target_type='square',
                area=area,
                aspect_ratio=aspect_ratio,
                position=(int(cx), int(cy))
            )
            
            if compute_contrast:
                # For squares, compute contrast from center region
                box = cv2.boxPoints(rect)
                x, y, bw, bh = cv2.boundingRect(np.int32(box))
                x = max(0, x)
                y = max(0, y)
                roi = gray[y:y+bh, x:x+bw]
                if roi.size > 0:
                    target.contrast = RoiDetector.calculate_michelson_contrast(roi)
            
            targets.append(target)
        
        # Sort by area (largest first for priority)
        targets.sort(key=lambda t: t.area, reverse=True)
        
        return targets

    @staticmethod
    def filter_by_contrast(targets: List[DetectedTarget], 
                           min_contrast: float = MIN_CONTRAST_THRESHOLD) -> List[DetectedTarget]:
        """
        Filter targets by minimum contrast threshold.
        
        Use this before MTF calculation to skip unusable ROIs.
        
        Args:
            targets: List of DetectedTarget objects
            min_contrast: Minimum Michelson contrast (default: 0.2)
            
        Returns:
            Filtered list with only usable targets
        """
        return [t for t in targets if t.contrast >= min_contrast]

    @staticmethod
    def split_square_into_edges(image: np.ndarray, square_rect: tuple) -> List[np.ndarray]:
        """
        Splits a detected square ROI into 4 measurable edge ROIs.
        Avoids warping to preserve raw pixel data for MTF accuracy.
        """
        (center_x, center_y), (w, h), angle = square_rect
        
        # Ensure we're working on grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        box = cv2.boxPoints(square_rect)
        box = np.int32(box) 
        
        # Sort points: Top-Left, Top-Right, Bottom-Right, Bottom-Left
        # This works reliably for rotation < 45 degrees
        cnt_pts = sorted(box, key=lambda p: p[1])  # Sort by Y
        top_pts = sorted(cnt_pts[:2], key=lambda p: p[0])  # Top by X
        bot_pts = sorted(cnt_pts[2:], key=lambda p: p[0])  # Bottom by X
        
        tl, tr = top_pts
        bl, br = bot_pts  # Note: bot_pts[0] is left (smaller x), bot_pts[1] is right
        
        edges_rois = []
        
        # Crop size: 40% of side length ensures corner exclusion
        side_len = min(w, h)
        crop_size = int(side_len * 0.4) 
        crop_size = max(16, crop_size)  # Ensure minimum size
        half_crop = crop_size // 2
        
        # Order: Top, Right, Bottom, Left
        edge_pairs = [(tl, tr), (tr, br), (br, bl), (bl, tl)]
        
        img_h, img_w = gray.shape[:2]
        
        for p1, p2 in edge_pairs:
            # Calculate edge midpoint
            cx = (p1[0] + p2[0]) / 2
            cy = (p1[1] + p2[1]) / 2
            
            # Coordinates for the crop
            ix = int(cx - half_crop)
            iy = int(cy - half_crop)
            
            # Boundary checks (important!)
            # Prevents crashes at image edges
            if ix < 0: ix = 0
            if iy < 0: iy = 0
            if ix + crop_size > img_w: ix = img_w - crop_size
            if iy + crop_size > img_h: iy = img_h - crop_size
            
            # Validation: Check if crop is possible within image bounds
            if ix < 0 or iy < 0 or crop_size <= 0:
                continue  # Skip if ROI is outside bounds

            roi = gray[iy:iy+crop_size, ix:ix+crop_size]
            
            # Validation: Catch empty ROIs
            if roi.size > 0:
                edges_rois.append(roi)
            
        return edges_rois

    @staticmethod
    def split_square_into_edges_with_contrast(image: np.ndarray, 
                                               square_rect: tuple,
                                               min_contrast: float = MIN_CONTRAST_THRESHOLD
                                               ) -> List[Tuple[np.ndarray, float, str]]:
        """
        Splits square into edges and returns only those with sufficient contrast.
        
        Args:
            image: Input image
            square_rect: Square rotated rect
            min_contrast: Minimum contrast threshold
            
        Returns:
            List of (roi_image, contrast, edge_name) tuples
        """
        edges = RoiDetector.split_square_into_edges(image, square_rect)
        edge_names = ['top', 'right', 'bottom', 'left']
        
        result = []
        for i, edge_img in enumerate(edges):
            contrast = RoiDetector.calculate_michelson_contrast(edge_img)
            name = edge_names[i] if i < 4 else f'edge_{i}'
            
            if contrast >= min_contrast:
                result.append((edge_img, contrast, name))
        
        return result

    @staticmethod
    def split_square_into_edges_with_boxes(image: np.ndarray,
                                           square_rect: tuple,
                                           fixed_size: Optional[Tuple[int, int]] = None
                                           ) -> List[Tuple[np.ndarray, Tuple[int, int, int, int], str]]:
        """
        Splits square into edges and returns ROIs with crop boxes.
        
        Args:
            image: Input image
            square_rect: Square rotated rect
            fixed_size: Optional (long_dim, short_dim) to enforce fixed ROI size.
                        If None, uses 40% of side length (square).

        Returns:
            List of (roi_image, (x, y, w, h), edge_name)
        """
        (center_x, center_y), (w, h), angle = square_rect

        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        box = cv2.boxPoints(square_rect)
        box = np.int32(box)

        cnt_pts = sorted(box, key=lambda p: p[1])
        top_pts = sorted(cnt_pts[:2], key=lambda p: p[0])
        bot_pts = sorted(cnt_pts[2:], key=lambda p: p[0])

        tl, tr = top_pts
        bl, br = bot_pts

        edge_pairs = [(tl, tr), (tr, br), (br, bl), (bl, tl)]
        edge_names = ['top', 'right', 'bottom', 'left']
        # Orientation of the edge itself:
        # Top: Horizontal, Right: Vertical, Bottom: Horizontal, Left: Vertical
        edge_orientations = ['horizontal', 'vertical', 'horizontal', 'vertical']

        img_h, img_w = gray.shape[:2]
        results = []

        # Default dynamic size
        side_len = min(w, h)
        default_crop = int(side_len * 0.4)
        default_crop = max(16, default_crop)

        for idx, (p1, p2) in enumerate(edge_pairs):
            orientation = edge_orientations[idx]
            
            if fixed_size:
                long_dim_req, short_dim_req = fixed_size
                
                # Safety: Ensure we don't exceed the square's actual physical size
                # We enable getting close to corners but leave 10% safety margin on each side
                max_len = int(side_len * 0.8) 
                
                # We can keep the requested width (50px is small), but must limit length
                actual_long = min(long_dim_req, max_len)
                actual_short = short_dim_req # Usually 50px, fits easily
                
                if orientation == 'horizontal':
                    crop_w, crop_h = actual_long, actual_short
                else:
                    crop_w, crop_h = actual_short, actual_long
            else:
                crop_w, crop_h = default_crop, default_crop

            cx = (p1[0] + p2[0]) / 2
            cy = (p1[1] + p2[1]) / 2

            ix = int(cx - crop_w // 2)
            iy = int(cy - crop_h // 2)

            # Clamp to image bounds explicitly (avoid negative/overflow slicing)
            x1 = max(0, ix)
            y1 = max(0, iy)
            x2 = min(img_w, ix + crop_w)
            y2 = min(img_h, iy + crop_h)

            final_w = x2 - x1
            final_h = y2 - y1

            if final_w < 4 or final_h < 4:
                continue

            roi = gray[y1:y2, x1:x2]
            if roi.size > 0:
                name = edge_names[idx] if idx < len(edge_names) else f'edge_{idx}'
                results.append((roi, (x1, y1, final_w, final_h), name))

        return results

    @staticmethod
    def create_edge_rois_from_rect(image: np.ndarray,
                                    rect: tuple,
                                    roi_width: int = 60) -> List['EdgeROI']:
        """
        Create EdgeROI objects at all 4 edges of a detected rectangle.
        
        ROIs are positioned PERPENDICULAR to each edge, spanning across the edge
        boundary (50% inside, 50% outside) for optimal edge detection.
        
        This is the improved version that provides:
        - Explicit edge direction (vertical/horizontal) for correct ESF extraction
        - Full coordinate tracking for output display
        - Contrast pre-calculation for filtering
        
        Args:
            image: Input image (grayscale or color)
            rect: minAreaRect tuple ((cx, cy), (w, h), angle)
            roi_width: Width of ROI perpendicular to edge (default: 60px)
            
        Returns:
            List of EdgeROI objects for each valid edge
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        img_h, img_w = gray.shape[:2]
        (center_x, center_y), (w, h), angle = rect
        
        # Get box points
        box = cv2.boxPoints(rect)
        box = np.int32(box)
        
        # Sort corners: Top-Left, Top-Right, Bottom-Right, Bottom-Left
        cnt_pts = sorted(box, key=lambda p: p[1])  # Sort by Y
        top_pts = sorted(cnt_pts[:2], key=lambda p: p[0])  # Top by X
        bot_pts = sorted(cnt_pts[2:], key=lambda p: p[0])  # Bottom by X
        
        tl, tr = top_pts
        bl, br = bot_pts
        
        # Edge definitions: (point1, point2, edge_name, edge_direction)
        # vertical edges -> measure horizontal MTF
        # horizontal edges -> measure vertical MTF
        edges = [
            (tl, tr, 'top', 'horizontal'),      # Top edge runs horizontally
            (tr, br, 'right', 'vertical'),      # Right edge runs vertically
            (br, bl, 'bottom', 'horizontal'),   # Bottom edge runs horizontally
            (bl, tl, 'left', 'vertical'),       # Left edge runs vertically
        ]
        
        # ROI length along the edge (40% of edge length to avoid corners)
        edge_len = min(w, h)
        roi_len = int(edge_len * 0.4)
        roi_len = max(20, roi_len)  # Minimum 20px
        
        half_width = roi_width // 2
        half_len = roi_len // 2
        
        edge_rois = []
        
        for p1, p2, edge_name, edge_direction in edges:
            # Edge midpoint
            mx = (p1[0] + p2[0]) / 2
            my = (p1[1] + p2[1]) / 2
            
            # Calculate ROI bounds based on edge direction
            if edge_direction == 'horizontal':
                # Edge runs horizontally -> ROI is wider in X, perpendicular in Y
                x1 = int(mx - half_len)
                x2 = int(mx + half_len)
                y1 = int(my - half_width)
                y2 = int(my + half_width)
            else:  # vertical
                # Edge runs vertically -> ROI is perpendicular in X, longer in Y
                x1 = int(mx - half_width)
                x2 = int(mx + half_width)
                y1 = int(my - half_len)
                y2 = int(my + half_len)
            
            # Clamp to image bounds
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(img_w, x2)
            y2 = min(img_h, y2)
            
            # Validate ROI size
            roi_w = x2 - x1
            roi_h = y2 - y1
            
            if roi_w < 10 or roi_h < 10:
                continue  # Skip too small ROIs
                
            # Extract ROI
            roi_img = gray[y1:y2, x1:x2]
            
            if roi_img.size == 0:
                continue
                
            # Calculate contrast
            contrast = RoiDetector.calculate_michelson_contrast(roi_img)
            
            edge_roi = EdgeROI(
                image=roi_img,
                bbox=(x1, y1, roi_w, roi_h),
                edge_direction=edge_direction,
                edge_name=edge_name,
                contrast=contrast,
                parent_center=(int(center_x), int(center_y))
            )
            
            edge_rois.append(edge_roi)
        
        return edge_rois

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
        tile_w = max(max_w, 150)  # Min width for text
        
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
            y_off = 30  # space for title
            
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
