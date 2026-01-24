"""
Image processing wrapper for MTF calculation.

This module provides the CameraImageProcessing class as a thin wrapper
around MTFAnalyzer for backward compatibility.

DEPRECATED: Prefer using `algorithms.mtf_analysis.MTFAnalyzer` directly.
This wrapper exists for backward compatibility with older code.
"""

import csv
from typing import Optional
import numpy as np

from .algorithms.mtf_analysis import MTFAnalyzer, MTFConfig


class CameraImageProcessing:
    """
    Image processing wrapper for MTF calculation.
    
    DEPRECATED: Use `algorithms.mtf_analysis.MTFAnalyzer` directly.
    
    This class provides backward compatibility with the old interface.
    Internally delegates to MTFAnalyzer for all MTF calculations.

    Attributes:
        logger: ROS2 logger

    Main Methods:
        calculate_mtf_from_roi(): Calculate MTF from edge ROI
        export_to_csv(): Export results to CSV file
    """

    def __init__(self, logger, pixel_size_um: float = 2.40):
        """Initialize image processing module.

        Args:
            logger: ROS2 logger for diagnostic output
            pixel_size_um: Pixel size in micrometers (default: 2.40 for IDS U3-3800CP)
        """
        self.logger = logger
        self._config = MTFConfig(pixel_size_um=pixel_size_um)
        self._analyzer = MTFAnalyzer(self._config)

    def calculate_mtf_from_roi(self, roi_image, oversample_factor: int = 4) -> Optional[dict]:
        """
        Calculate MTF from slanted edge region of interest.

        Args:
            roi_image: Image region with slanted edge
            oversample_factor: Sub-pixel sampling factor (default: 4)

        Returns:
            dict: {'frequency': array, 'mtf': array} or None on error
        """
        if roi_image is None or roi_image.size == 0:
            self.logger.error('Empty ROI provided')
            return None
        
        # Update config with oversample factor
        self._config.oversample_factor = oversample_factor
        
        # Delegate to MTFAnalyzer
        result = self._analyzer.compute_mtf(roi_image)
        
        if not result.valid:
            self.logger.error(f'MTF calculation failed: {result.error_msg}')
            return None
        
        return {
            'frequency': result.frequencies,
            'mtf': result.mtf_values,
            'mtf50': result.mtf50,
            'mtf20': result.mtf20,
            'mtf10': result.mtf10,
            'edge_angle': result.edge_angle,
        }

    def export_to_csv(self, data_dict: dict, filename: str) -> None:
        """
        Exports MTF data to a CSV file.

        Args:
            data_dict: Dictionary containing data arrays,
                       e.g., {'frequency': f, 'mtf': m}.
            filename: Output filename.
        """
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            # Write header
            header = list(data_dict.keys())
            writer.writerow(header)
            # Write data rows (only array values)
            array_data = {k: v for k, v in data_dict.items() if hasattr(v, '__iter__') and not isinstance(v, str)}
            if array_data:
                rows = zip(*array_data.values())
                writer.writerows(rows)

        self.logger.info(f'Data successfully exported to {filename}')
