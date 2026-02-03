"""Field Curvature Analysis Module.

Provides tools for measuring MTF across the image field to detect:
- Field curvature (focus shift across FOV)
- Lens aberrations (corner vs center performance)
- Overall optical quality distribution

Usage:
    from camera_nodes.algorithms.field_curvature import analyze_field_curvature
    
    field_data = analyze_field_curvature(image, pixel_size_um=2.40)
    print(f"Center MTF50: {field_data['center']:.1f} lp/mm")
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None


@dataclass
class FieldPosition:
    """Represents a field position for MTF measurement."""
    name: str
    relative_x: float  # 0-1, relative to image width
    relative_y: float  # 0-1, relative to image height
    roi_size: int = 200  # Default ROI size in pixels


# Standard 5-point field positions (center + corners at 70% field)
FIELD_POSITIONS = [
    FieldPosition('center', 0.5, 0.5),
    FieldPosition('top_left', 0.15, 0.15),
    FieldPosition('top_right', 0.85, 0.15),
    FieldPosition('bottom_left', 0.15, 0.85),
    FieldPosition('bottom_right', 0.85, 0.85),
]


def detect_field_rois(image: np.ndarray, 
                      positions: Optional[List[FieldPosition]] = None,
                      roi_size: int = 200) -> Dict[str, Tuple[int, int, int, int]]:
    """
    Detect ROIs at standard field positions.
    
    Args:
        image: Input image (grayscale or color)
        positions: List of FieldPosition objects. Uses 5-point default if None.
        roi_size: Size of square ROI in pixels
        
    Returns:
        Dict mapping position names to ROI bounds (x1, y1, x2, y2)
    """
    if positions is None:
        positions = FIELD_POSITIONS
        
    h, w = image.shape[:2]
    rois = {}
    
    for pos in positions:
        # Calculate center
        cx = int(w * pos.relative_x)
        cy = int(h * pos.relative_y)
        
        # Use specified ROI size or position's default
        size = roi_size if roi_size > 0 else pos.roi_size
        half = size // 2
        
        # Calculate bounds with clamping
        x1 = max(0, cx - half)
        x2 = min(w, cx + half)
        y1 = max(0, cy - half)
        y2 = min(h, cy + half)
        
        # Ensure minimum size
        if x2 - x1 >= 50 and y2 - y1 >= 50:
            rois[pos.name] = (x1, y1, x2, y2)
    
    return rois


def analyze_field_curvature(image: np.ndarray,
                            pixel_size_um: float = 2.40,
                            roi_size: int = 200,
                            positions: Optional[List[FieldPosition]] = None
                            ) -> Dict[str, float]:
    """
    Analyze MTF across the image field.
    
    Measures MTF50 at multiple field positions to detect:
    - Field curvature (focus variation across FOV)
    - Lens aberrations (edge vs center performance)
    
    Args:
        image: Input image containing slanted edges at each position
        pixel_size_um: Pixel size in micrometers
        roi_size: Size of ROI at each position
        positions: Custom field positions (uses 5-point default if None)
        
    Returns:
        Dict mapping position names to MTF50 values (lp/mm)
        Invalid measurements are excluded.
    """
    # Import here to avoid circular imports
    try:
        from .mtf_analysis import MTFAnalyzer, MTFConfig
    except ImportError:
        from camera_nodes.algorithms.mtf_analysis import MTFAnalyzer, MTFConfig
    
    # Get ROI positions
    rois = detect_field_rois(image, positions, roi_size)
    
    # Configure analyzer
    config = MTFConfig(pixel_size_um=pixel_size_um, roi_width=roi_size, roi_height=roi_size)
    analyzer = MTFAnalyzer(config)
    
    results = {}
    
    for name, (x1, y1, x2, y2) in rois.items():
        result = analyzer.compute_mtf(image, roi=(x1, y1, x2, y2))
        
        if result.valid:
            results[name] = result.mtf50
        # Skip invalid measurements
    
    return results


def analyze_field_curvature_detailed(image: np.ndarray,
                                     pixel_size_um: float = 2.40,
                                     roi_size: int = 200
                                     ) -> Dict[str, dict]:
    """
    Detailed field curvature analysis with full MTF results.
    
    Returns:
        Dict mapping position names to full MTF result dicts
    """
    try:
        from .mtf_analysis import MTFAnalyzer, MTFConfig
    except ImportError:
        from camera_nodes.algorithms.mtf_analysis import MTFAnalyzer, MTFConfig
    
    rois = detect_field_rois(image, FIELD_POSITIONS, roi_size)
    
    config = MTFConfig(pixel_size_um=pixel_size_um, roi_width=roi_size, roi_height=roi_size)
    analyzer = MTFAnalyzer(config)
    
    results = {}
    
    for name, (x1, y1, x2, y2) in rois.items():
        result = analyzer.compute_mtf(image, roi=(x1, y1, x2, y2))
        
        results[name] = {
            'valid': result.valid,
            'mtf50': result.mtf50 if result.valid else None,
            'mtf20': result.mtf20 if result.valid else None,
            'mtf10': result.mtf10 if result.valid else None,
            'edge_angle': result.edge_angle,
            'contrast': result.contrast,
            'error': result.error_msg if not result.valid else None,
            'roi': (x1, y1, x2, y2),
            'frequencies': result.frequencies.tolist() if result.valid else [],
            'mtf_values': result.mtf_values.tolist() if result.valid else []
        }
    
    return results


def calculate_field_metrics(field_data: Dict[str, float]) -> dict:
    """
    Calculate metrics from field curvature data.
    
    Args:
        field_data: Dict from analyze_field_curvature()
        
    Returns:
        Dict with:
        - center_mtf50: Center MTF50
        - corner_mean: Mean corner MTF50
        - corner_min: Worst corner
        - corner_max: Best corner
        - uniformity: corner_mean / center (0-1, 1=perfect)
        - falloff_percent: (center - corner_mean) / center * 100
    """
    if not field_data:
        return {'error': 'No field data provided'}
    
    center = field_data.get('center')
    
    # Get corner values
    corner_names = ['top_left', 'top_right', 'bottom_left', 'bottom_right']
    corners = [field_data[n] for n in corner_names if n in field_data]
    
    if center is None:
        return {'error': 'No center measurement'}
    
    if not corners:
        return {
            'center_mtf50': center,
            'error': 'No corner measurements'
        }
    
    corner_mean = np.mean(corners)
    corner_min = np.min(corners)
    corner_max = np.max(corners)
    
    uniformity = corner_mean / center if center > 0 else 0
    falloff = (center - corner_mean) / center * 100 if center > 0 else 0
    
    return {
        'center_mtf50': center,
        'corner_mean': corner_mean,
        'corner_min': corner_min,
        'corner_max': corner_max,
        'uniformity': uniformity,
        'falloff_percent': falloff,
        'n_corners': len(corners)
    }
