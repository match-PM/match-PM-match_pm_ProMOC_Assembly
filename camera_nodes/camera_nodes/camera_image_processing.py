import cv2
import numpy as np
import csv

class CameraImageProcessing:
    """A class to hold all image processing and analysis logic."""

    def __init__(self, logger):
        """
        Initializes the image processing class.

        :param logger: ROS2 logger instance for logging messages.
        """
        self.logger = logger

    def calculate_mtf_from_roi(self, roi_image, oversample_factor=4):
        """
        Calculates the MTF from a given ROI containing a slanted edge.

        :param roi_image: The image crop containing the slanted edge.
        :param oversample_factor: The factor for sub-pixel analysis.
        :return: A dictionary {'frequency': array, 'mtf': array} or None on failure.
        """
        esf = self._calculate_esf(roi_image, oversample_factor)
        if esf is None:
            self.logger.error("ESF calculation failed.")
            return None
        
        freq, mtf = self._calculate_lsf_and_mtf(esf, oversample_factor)
        
        return {'frequency': freq, 'mtf': mtf}

    def _calculate_esf(self, roi_image, oversample_factor):
        """Calculates the Edge Spread Function (ESF) from a slanted edge ROI."""
        if roi_image is None or roi_image.size == 0:
            return None

        # 1. Convert to grayscale float
        gray_roi = cv2.cvtColor(roi_image, cv2.COLOR_BGR2GRAY).astype(np.float64)

        # 2. Find the edge line equation
        edges = cv2.Canny(np.uint8(gray_roi), 50, 150)
        points = np.argwhere(edges > 0)
        if len(points) < 10:
            return None # Not enough edge points found

        # OpenCV fitLine needs points in (x,y) format
        points_xy = points[:, ::-1]
        [vx, vy, x0, y0] = cv2.fitLine(points_xy, cv2.DIST_L2, 0, 0.01, 0.01)
        angle = np.arctan2(vy, vx)

        # 3. Project pixel intensities onto the line perpendicular to the edge
        # We create bins to store intensity values based on their sub-pixel distance to the edge.
        min_dist, max_dist = -np.inf, np.inf
        distances = (points_xy[:, 0] - x0) * vy - (points_xy[:, 1] - y0) * vx
        min_dist, max_dist = np.min(distances), np.max(distances)

        num_bins = int(np.ceil(max_dist - min_dist) * oversample_factor)
        if num_bins <= 0:
            return None
            
        bin_sums = np.zeros(num_bins)
        bin_counts = np.zeros(num_bins)

        # Iterate over all pixels in the ROI
        h, w = gray_roi.shape
        y_coords, x_coords = np.mgrid[:h, :w]
        all_points = np.vstack((x_coords.ravel(), y_coords.ravel())).T
        
        # Calculate perpendicular distance for all points
        all_distances = (all_points[:, 0] - x0) * vy - (all_points[:, 1] - y0) * vx
        all_intensities = gray_roi.ravel()

        # Determine bin index for each point
        bin_indices = np.floor((all_distances - min_dist) * oversample_factor).astype(int)

        # Filter out points that are outside our bin range
        valid_mask = (bin_indices >= 0) & (bin_indices < num_bins)
        valid_indices = bin_indices[valid_mask]
        valid_intensities = all_intensities[valid_mask]

        # Use numpy to efficiently sum up values for each bin
        np.add.at(bin_sums, valid_indices, valid_intensities)
        np.add.at(bin_counts, valid_indices, 1)

        # 4. Average the bins to get the ESF
        # Avoid division by zero for empty bins
        valid_bins = bin_counts > 0
        esf = np.full(num_bins, np.nan)
        esf[valid_bins] = bin_sums[valid_bins] / bin_counts[valid_bins]
        
        # Interpolate to fill any empty bins
        if np.isnan(esf).any():
            x = np.arange(num_bins)
            not_nan = ~np.isnan(esf)
            esf = np.interp(x, x[not_nan], esf[not_nan])

        return esf

    def _calculate_lsf_and_mtf(self, esf, oversample_factor):
        """Calculates the LSF and MTF from the ESF."""
        # 1. Calculate LSF (derivative of ESF)
        lsf = np.diff(esf)
        # Normalize LSF to sum to 1
        lsf = lsf / np.sum(lsf)

        # 2. Apply a window function to reduce spectral leakage
        window = np.hamming(len(lsf))
        windowed_lsf = lsf * window

        # 3. Calculate MTF (magnitude of the FFT of the LSF)
        fft_result = np.fft.fft(windowed_lsf)
        mtf = np.abs(fft_result)

        # 4. Normalize MTF
        mtf = mtf / mtf[0]

        # 5. Calculate spatial frequencies
        # Frequency is in cycles/pixel. The oversample_factor scales the frequency axis.
        freq = np.fft.fftfreq(len(mtf), d=1.0/oversample_factor)

        # We only need the positive frequencies up to the Nyquist limit (0.5 cycles/pixel)
        positive_freq_mask = (freq >= 0) & (freq <= 0.5)
        freq = freq[positive_freq_mask]
        mtf = mtf[positive_freq_mask]

        return freq, mtf

    def export_to_csv(self, data_dict, filename):
        """
        Exports a dictionary of data to a CSV file.

        :param data_dict: Dictionary with data arrays (e.g., {'frequency': f, 'mtf': m}).
        :param filename: The name of the output CSV file.
        """
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            # Write header
            header = list(data_dict.keys())
            writer.writerow(header)
            # Write data rows
            rows = zip(*data_dict.values())
            writer.writerows(rows)
        self.logger.info(f"Successfully exported data to {filename}")