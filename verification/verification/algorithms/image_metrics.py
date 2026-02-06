import cv2
import numpy as np
from typing import Tuple, Optional

class ImageMetrics:
    @staticmethod
    def calculate_tenengrad(image: np.ndarray, ksize: int = 3) -> float:
        """
        Calculate Tenengrad focus metric (Sum of squared Sobel gradients).
        
        Args:
            image: Grayscale image (numpy array).
            ksize: Kernel size for Sobel operator (default 3).
        
        Returns:
            float: Tenengrad score.
        """
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
        gx = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=ksize)
        gy = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=ksize)
        
        magnitude_squared = gx**2 + gy**2
        return float(np.mean(magnitude_squared))

    @staticmethod
    def calculate_zernike_angle(image: np.ndarray, threshold_factor: float = 0.5) -> float:
        """
        Calculate edge angle using Zernike Moments ($A_{11}$).
        Ghosal & Mehrotra (1993) approach for sub-pixel edge detection.
        
        The angle of the edge normal is given by tan(phi) = Im(A11) / Re(A11).
        
        Args:
           image: Grayscale image.
           threshold_factor: Factor of max amplitude to select edge pixels.
           
        Returns:
           float: Edge angle in degrees (relative to horizontal).
        """
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
        # Zernike moments A11 masks (7x7 approximation)
        # Sourced from standard literature for N=7
        # Re(A11) ~ horizontal derivative-like
        k_re = np.array([
            [-0.0165, -0.0238, -0.0210, 0.0, 0.0210, 0.0238, 0.0165],
            [-0.0416, -0.0673, -0.0683, 0.0, 0.0683, 0.0673, 0.0416],
            [-0.0637, -0.1162, -0.1432, 0.0, 0.1432, 0.1162, 0.0637],
            [-0.0766, -0.1491, -0.2078, 0.0, 0.2078, 0.1491, 0.0766],
            [-0.0637, -0.1162, -0.1432, 0.0, 0.1432, 0.1162, 0.0637],
            [-0.0416, -0.0673, -0.0683, 0.0, 0.0683, 0.0673, 0.0416],
            [-0.0165, -0.0238, -0.0210, 0.0, 0.0210, 0.0238, 0.0165]
        ])
        
        # Im(A11) ~ vertical derivative-like (transpose of Re)
        k_im = k_re.T
        
        # Convolve
        a11_re = cv2.filter2D(image, cv2.CV_64F, k_re)
        a11_im = cv2.filter2D(image, cv2.CV_64F, k_im)
        
        magnitude = np.sqrt(a11_re**2 + a11_im**2)
        
        # Select strong edge pixels
        thresh_val = np.max(magnitude) * threshold_factor
        mask = magnitude > thresh_val
        
        if np.sum(mask) == 0:
            return 0.0
            
        # Calculate angles at edge pixels
        # phi is the angle of the normal vector to the edge
        # To get the edge direction (tangent), we rotate by 90deg
        phis = np.arctan2(a11_im[mask], a11_re[mask])
        
        # Unwrap/Align angles (slanted edge is usually straight)
        # Simply averaging arctan2 can be tricky if angles wrap around pi/-pi
        # But for a single slanted edge, they should be clustered.
        # We assume the edge is roughy unidirectional in the ROI.
        
        # Weighted average by magnitude?
        # A simpler robust way: PCA of the (Re, Im) vectors themselves!
        # Or just circular mean.
        
        mean_phi = np.arctan2(np.mean(np.sin(phis)), np.mean(np.cos(phis)))
        
        # Convert to degrees
        # Note: This is the angle of the NORMAL vector.
        # Edge angle (tangent) = Normal - 90 deg
        angle_normal_deg = np.degrees(mean_phi)
        
        # Map to typically expected range for slanted edge (e.g. deviation from vertical)
        # If edge is near vertical, normal is near horizontal (0 deg).
        # We usually want the angle of the EDGE line.
        angle_edge_deg = angle_normal_deg + 90.0
        
        return angle_edge_deg

    @staticmethod
    def calculate_mtf_proxy(image: np.ndarray) -> Tuple[float, float]:
        """
        Calculate MTF Proxy (Slanted Edge Gradient 90th percentile) and Edge Angle.
        
        Args:
            image: Grayscale image (numpy array).
            
        Returns:
            Tuple[float, float]: (mtf_score, edge_angle_degrees)
        """
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
        # Calculate Gradient Magnitude
        gx = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
        
        magnitude = np.sqrt(gx**2 + gy**2)
        
        # MTF Proxy: 90th percentile of gradient magnitude
        # This represents the "sharpness" of the strongest edges
        mtf_score = float(np.percentile(magnitude, 90))
        
        # Edge Angle Estimation
        # We focus on pixels with high gradient to determine orientation
        threshold = np.max(magnitude) * 0.5
        mask = magnitude > threshold
        
        if np.sum(mask) == 0:
            return mtf_score, 0.0
            
        # Use Zernike Moment based angle estimation as requested
        edge_angle_deg = ImageMetrics.calculate_zernike_angle(image)

        return mtf_score, edge_angle_deg

        
        return mtf_score, edge_angle_deg

