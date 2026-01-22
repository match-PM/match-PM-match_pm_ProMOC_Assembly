"""
Image processing algorithms for MTF (Modulation Transfer Function) calculation.

This module provides the CameraImageProcessing class implementing the Slanted
Edge Method (ISO 12233) for MTF calculation and image analysis.

MTF describes how well an optical system transmits contrast at different spatial
frequencies. Higher MTF values indicate better image quality at those frequencies.

Processing Pipeline:
- ESF (Edge Spread Function): Extract intensity profile perpendicular to edge
- LSF (Line Spread Function): Derivative of ESF
- MTF: FFT of LSF (normalized)

Slanted Edge Method:
The edge must be at ~5° angle to extract sub-pixel information across multiple
rows, improving measurement accuracy.

Usage:
    processor = CameraImageProcessing(logger)
    results = processor.calculate_mtf_from_roi(roi_image)
    processor.export_to_csv(results, "mtf_results.csv")
"""

import csv

import cv2
import numpy as np


class CameraImageProcessing:
    """
    Image processing for MTF calculation using slanted edge method.

    Implements ISO 12233 standard for optical system quality measurement.

    Attributes:
        logger: ROS2 logger

    Main Methods:
        calculate_mtf_from_roi(): Calculate MTF from edge ROI
        export_to_csv(): Export results to CSV file
    """

    def __init__(self, logger):
        """Initialize image processing module.

        Args:
            logger: ROS2 logger for diagnostic output
        """
        self.logger = logger

    # MTF CALCULATION

    def calculate_mtf_from_roi(self, roi_image, oversample_factor=4):
        """
        Calculate MTF from slanted edge region of interest.

        Steps:
        1. Compute ESF (Edge Spread Function)
        2. Derive LSF (Line Spread Function) from ESF
        3. Calculate MTF as FFT of LSF

        Args:
            roi_image: Image region with slanted edge
            oversample_factor: Sub-pixel sampling factor (default: 4)

        Returns:
            dict: {'frequency': array, 'mtf': array} or None on error
        """
        esf = self._calculate_esf(roi_image, oversample_factor)
        if esf is None:
            self.logger.error('ESF calculation failed.')
            return None

        freq, mtf = self._calculate_lsf_and_mtf(esf, oversample_factor)

        return {'frequency': freq, 'mtf': mtf}

    def _calculate_esf(self, roi_image, oversample_factor):
        """
        Calculate Edge Spread Function (ESF) from a slanted edge ROI.

        Steps:
        1. Convert image to grayscale.
        2. Detect the edge using the Canny algorithm.
        3. Fit a line to the detected edge points.
        4. Project all pixel intensities perpendicularly onto the fitted line.
        5. Collect the projected intensities into bins to form the ESF.
        """
        if roi_image is None or roi_image.size == 0:
            return None

        # Convert to grayscale
        gray_roi = cv2.cvtColor(
            roi_image, cv2.COLOR_BGR2GRAY).astype(np.float64)

        # Light blur to stabilize edge detection
        gray_u8 = np.uint8(gray_roi)
        gray_u8 = cv2.GaussianBlur(gray_u8, (3, 3), 0)

        # Detect edge: try multiple Canny thresholds
        points = None
        for low, high in [(30, 100), (50, 150), (10, 40)]:
            edges = cv2.Canny(gray_u8, low, high)
            pts = np.argwhere(edges > 0)
            if len(pts) >= 20:
                points = pts
                break

        # Fallback: Sobel magnitude threshold
        if points is None:
            gx = cv2.Sobel(gray_u8, cv2.CV_64F, 1, 0, ksize=3)
            gy = cv2.Sobel(gray_u8, cv2.CV_64F, 0, 1, ksize=3)
            mag = np.sqrt(gx * gx + gy * gy)
            thresh = np.percentile(mag, 90)
            edges = (mag >= thresh).astype(np.uint8)
            points = np.argwhere(edges > 0)

        if points is None or len(points) < 20:
            return None  # Too few edge points

        # Fit line through edge points. OpenCV fitLine expects (x,y) format.
        points_xy = points[:, ::-1]
        [vx, vy, x0, y0] = cv2.fitLine(points_xy, cv2.DIST_L2, 0, 0.01, 0.01)

        # Project pixels onto the perpendicular line to the edge
        min_dist, max_dist = -np.inf, np.inf
        distances = (points_xy[:, 0] - x0) * vy - (points_xy[:, 1] - y0) * vx
        min_dist, max_dist = np.min(distances), np.max(distances)

        num_bins = int(np.ceil(max_dist - min_dist) * oversample_factor)
        if num_bins <= 0:
            return None

        bin_sums = np.zeros(num_bins)
        bin_counts = np.zeros(num_bins)

        # Process all pixels in the ROI
        h, w = gray_roi.shape
        y_coords, x_coords = np.mgrid[:h, :w]
        all_points = np.vstack((x_coords.ravel(), y_coords.ravel())).T

        # Calculate perpendicular distance for all points
        all_distances = (all_points[:, 0] - x0) * \
            vy - (all_points[:, 1] - y0) * vx
        all_intensities = gray_roi.ravel()

        # Determine the bin index for each point
        bin_indices = np.floor((all_distances - min_dist)
                               * oversample_factor).astype(int)

        # Filter out points that fall outside the bin range
        valid_mask = (bin_indices >= 0) & (bin_indices < num_bins)
        valid_indices = bin_indices[valid_mask]
        valid_intensities = all_intensities[valid_mask]

        # Accumulate intensity values and counts for each bin
        np.add.at(bin_sums, valid_indices, valid_intensities)
        np.add.at(bin_counts, valid_indices, 1)

        # Calculate the average intensity for each bin to get the ESF
        valid_bins = bin_counts > 0
        esf = np.full(num_bins, np.nan)
        esf[valid_bins] = bin_sums[valid_bins] / bin_counts[valid_bins]

        # Interpolate empty bins to create a continuous ESF
        if np.isnan(esf).any():
            x = np.arange(num_bins)
            not_nan = ~np.isnan(esf)
            esf = np.interp(x, x[not_nan], esf[not_nan])

        return esf

    def _calculate_lsf_and_mtf(self, esf, oversample_factor):
        """
        Calculates the LSF and MTF from the ESF.

        Mathematical relationship:
        ===========================
            LSF = d/dx ESF       (Derivative)
            MTF = |FFT(LSF)|     (Fourier Transform)

        Args:
            esf (np.ndarray): 1D array representing the Edge Spread Function.
            oversample_factor (int): The oversampling factor used.

        Returns:
            tuple: (frequency_axis, mtf_values)
        """
        # Calculate LSF (derivative of ESF) and normalize it to sum to 1.
        lsf = np.diff(esf)
        lsf = lsf / np.sum(lsf)

        # Apply a Hamming window to reduce spectral leakage from edge effects.
        window = np.hamming(len(lsf))
        windowed_lsf = lsf * window

        # Calculate MTF by taking the Fourier Transform of the LSF.
        fft_result = np.fft.fft(windowed_lsf)
        mtf = np.abs(fft_result)  # Magnitude is the MTF

        # Normalize the MTF to its DC value (MTF at frequency 0 is 1.0 by definition).
        mtf = mtf / mtf[0]

        # Calculate the frequency axis in cycles/pixel.
        freq = np.fft.fftfreq(len(mtf), d=1.0/oversample_factor)

        # Return only the positive frequencies up to the Nyquist limit (0.5 cycles/pixel).
        positive_freq_mask = (freq >= 0) & (freq <= 0.5)
        freq = freq[positive_freq_mask]
        mtf = mtf[positive_freq_mask]

        return freq, mtf

    # EXPORT

    def export_to_csv(self, data_dict, filename):
        """
        Exports MTF data to a CSV file.

        Args:
            data_dict (dict): A dictionary containing data arrays,
                              e.g., {'frequency': f, 'mtf': m}.
            filename (str): The output filename.

        Example CSV output:
            frequency,mtf
            0.0,1.0
            0.1,0.95
            ...
        """
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            # Write header
            header = list(data_dict.keys())
            writer.writerow(header)
            # Write data rows
            rows = zip(*data_dict.values())
            writer.writerows(rows)

        self.logger.info(f'Data successfully exported to {filename}')
