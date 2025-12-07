"""
Focus Quality Metrics for Image Sharpness Evaluation.

This module provides various focus quality metrics used in autofocus algorithms.
All metrics return higher values for sharper (more in-focus) images.

Metrics:
    - laplacian_variance: Fast, good for coarse focusing
    - tenengrad: Robust, good for fine focusing
    - brenner_gradient: Simple gradient-based metric
    - normalized_variance: Intensity-normalized variance

Usage:
    from promoc_core.algorithms.focus_metrics import laplacian_variance, tenengrad
    
    score = laplacian_variance(image)
    score = tenengrad(image, threshold=0.0)

Note:
    All functions expect grayscale images as numpy arrays.
    Color images will be automatically converted to grayscale.
"""

from typing import Optional
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None  # Will raise on usage


def _ensure_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert image to grayscale if needed."""
    if cv2 is None:
        raise ImportError("OpenCV (cv2) is required for focus metrics")

    if image is None or image.size == 0:
        raise ValueError("Image is empty or None")

    if len(image.shape) == 3:
        if image.shape[2] == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        elif image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        else:
            return image[:, :, 0]
    return image


def laplacian_variance(image: np.ndarray, ksize: int = 3) -> float:
    """
    Compute Laplacian variance as focus metric.

    Fast metric suitable for coarse focusing. Measures the amount of
    edges/high-frequency content in the image.

    Args:
        image: Input image (grayscale or color)
        ksize: Kernel size for Laplacian operator (default: 3)

    Returns:
        Variance of Laplacian response. Higher = sharper.

    Raises:
        ValueError: If image is empty or None
        ImportError: If OpenCV is not available

    Example:
        >>> score = laplacian_variance(image)
        >>> print(f"Focus score: {score:.2f}")
    """
    gray = _ensure_grayscale(image)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=ksize)
    return float(laplacian.var())


def tenengrad(image: np.ndarray, ksize: int = 3, threshold: float = 0.0) -> float:
    """
    Compute Tenengrad focus metric using Sobel gradients.

    Robust metric suitable for fine focusing. Measures gradient magnitude
    across the image.

    Args:
        image: Input image (grayscale or color)
        ksize: Kernel size for Sobel operator (default: 3)
        threshold: Minimum gradient to consider (default: 0.0)

    Returns:
        Sum of squared gradients above threshold. Higher = sharper.

    Raises:
        ValueError: If image is empty or None
        ImportError: If OpenCV is not available

    Example:
        >>> score = tenengrad(image, threshold=100.0)
        >>> print(f"Focus score: {score:.2f}")
    """
    gray = _ensure_grayscale(image)

    # Compute Sobel gradients
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=ksize)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=ksize)

    # Compute gradient magnitude squared
    gradient_magnitude = gx**2 + gy**2

    # Apply threshold if specified
    if threshold > 0:
        gradient_magnitude[gradient_magnitude < threshold**2] = 0

    return float(gradient_magnitude.sum())


def brenner_gradient(image: np.ndarray, step: int = 2) -> float:
    """
    Compute Brenner gradient focus metric.

    Simple and fast metric based on horizontal pixel differences.

    Args:
        image: Input image (grayscale or color)
        step: Pixel step for gradient calculation (default: 2)

    Returns:
        Sum of squared differences. Higher = sharper.

    Raises:
        ValueError: If image is empty or None

    Example:
        >>> score = brenner_gradient(image)
        >>> print(f"Focus score: {score:.2f}")
    """
    gray = _ensure_grayscale(image)
    gray = gray.astype(np.float64)

    # Compute horizontal differences with step
    diff = gray[:, step:] - gray[:, :-step]

    return float((diff**2).sum())


def normalized_variance(image: np.ndarray) -> float:
    """
    Compute normalized variance focus metric.

    Variance normalized by mean intensity. Less sensitive to
    illumination changes than raw variance.

    Args:
        image: Input image (grayscale or color)

    Returns:
        Variance divided by mean. Higher = sharper.
        Returns 0.0 if mean is zero to avoid division by zero.

    Raises:
        ValueError: If image is empty or None

    Example:
        >>> score = normalized_variance(image)
        >>> print(f"Focus score: {score:.4f}")
    """
    gray = _ensure_grayscale(image)
    gray = gray.astype(np.float64)

    mean = gray.mean()
    if mean == 0:
        return 0.0

    return float(gray.var() / mean)


def sml(image: np.ndarray, threshold: float = 0.0) -> float:
    """
    Compute Sum of Modified Laplacian (SML) focus metric.

    Modified Laplacian using absolute values of second derivatives.

    Args:
        image: Input image (grayscale or color)
        threshold: Minimum value to consider (default: 0.0)

    Returns:
        Sum of modified Laplacian above threshold. Higher = sharper.

    Raises:
        ValueError: If image is empty or None
        ImportError: If OpenCV is not available
    """
    gray = _ensure_grayscale(image)
    gray = gray.astype(np.float64)

    # Compute second derivatives
    kernel_x = np.array([[1, -2, 1]], dtype=np.float64)
    kernel_y = np.array([[1], [-2], [1]], dtype=np.float64)

    lx = cv2.filter2D(gray, cv2.CV_64F, kernel_x)
    ly = cv2.filter2D(gray, cv2.CV_64F, kernel_y)

    # Modified Laplacian = |Lxx| + |Lyy|
    ml = np.abs(lx) + np.abs(ly)

    # Apply threshold
    if threshold > 0:
        ml[ml < threshold] = 0

    return float(ml.sum())
