"""Focus/Sharpness Metrics for Image Quality Assessment.

This module provides several focus quality metrics typically used in
autofocus algorithms. The core idea is the same for all:

    **The higher the score, the sharper ("more in focus") the image.**

Which metric to use?
    - `laplacian_variance`: Fast, good for coarse focusing.
    - `tenengrad`: Robust, good for fine focusing.
    - `brenner_gradient`: Very simple, gradient-based.
    - `normalized_variance`: Variance normalized by the mean (more robust to brightness changes).
    - `sml`: Sum of Modified Laplacian (second derivative, often good edge sensitivity).

Quickstart:
    from camera_nodes.algorithms.focus_metrics import laplacian_variance, tenengrad

    score = laplacian_variance(image)
    score = tenengrad(image, threshold=0.0)

Important:
    - All functions expect a grayscale image as a NumPy array.
    - Color images are automatically converted to grayscale.
    - OpenCV (`cv2`) is required for conversion and some filters.
"""

from typing import Optional
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None  # Will raise on usage


def _ensure_grayscale(image: np.ndarray) -> np.ndarray:
    """Converts an image to grayscale if necessary.

    Raises:
        ImportError: if OpenCV (`cv2`) is not available.
        ValueError: if the image is empty or None.
    """
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
    Calculates the variance of the Laplacian as a focus metric.

    This is a fast metric suitable for coarse focus searches. It measures the
    variance of the Laplacian response (2nd derivative)—sharper images typically
    contain more high-frequency content/edges, leading to larger values.

    Args:
        image: Input image (grayscale or color).
        ksize: Kernel size for the Laplacian operator (default: 3).

    Returns:
        The variance of the Laplacian response. Higher is sharper.

    Raises:
        ValueError: if the image is empty or None.
        ImportError: if OpenCV is not available.

    Example:
        >>> score = laplacian_variance(image)
        >>> print(f"Focus score: {score:.2f}")
    """
    gray = _ensure_grayscale(image)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=ksize)
    return float(laplacian.var())


def tenengrad(image: np.ndarray, ksize: int = 3, threshold: float = 0.0) -> float:
    """
    Calculates the Tenengrad focus metric (using Sobel gradients).

    This is a robust metric suitable for fine-grained focusing. It is based on
    the gradient energy (sum of squared Sobel gradients) in the image.

    Args:
        image: Input image (grayscale or color).
        ksize: Kernel size for the Sobel operator (default: 3).
        threshold: Minimum gradient magnitude to consider (default: 0.0).

    Returns:
        The sum of squared gradients above the threshold. Higher is sharper.

    Raises:
        ValueError: if the image is empty or None.
        ImportError: if OpenCV is not available.

    Example:
        >>> score = tenengrad(image, threshold=100.0)
        >>> print(f"Focus score: {score:.2f}")
    """
    gray = _ensure_grayscale(image)

    # Sobel gradients
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=ksize)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=ksize)

    # Sum of squared gradients
    gradient_magnitude = gx**2 + gy**2

    # Optional thresholding
    if threshold > 0:
        gradient_magnitude[gradient_magnitude < threshold**2] = 0

    return float(gradient_magnitude.sum())


def brenner_gradient(image: np.ndarray, step: int = 2) -> float:
    """
    Calculates the Brenner gradient metric.

    A very simple and fast metric based on horizontal pixel differences
    at a fixed distance (`step`).

    Args:
        image: Input image (grayscale or color).
        step: Pixel distance for the difference calculation (default: 2).

    Returns:
        The sum of the squared differences. Higher is sharper.

    Raises:
        ValueError: if the image is empty or None.

    Example:
        >>> score = brenner_gradient(image)
        >>> print(f"Focus score: {score:.2f}")
    """
    gray = _ensure_grayscale(image)
    gray = gray.astype(np.float64)

    # Horizontal differences with a fixed step
    diff = gray[:, step:] - gray[:, :-step]

    return float((diff**2).sum())


def normalized_variance(image: np.ndarray) -> float:
    """
    Calculates a normalized variance as a focus metric.

    This metric is the variance normalized by the mean intensity, making it
    less sensitive to brightness fluctuations than a pure variance measure.

    Args:
        image: Input image (grayscale or color).

    Returns:
        The variance divided by the mean. Higher is sharper.
        Returns 0.0 if the mean is 0 to avoid division by zero.

    Raises:
        ValueError: if the image is empty or None.

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
    Calculates the "Sum of Modified Laplacian" (SML) focus metric.

    The "Modified Laplacian" is based on the absolute values of the second
    derivative. In practice, this is an edge/detail metric (high-frequency
    content) that often correlates well with sharpness.

    Args:
        image: Input image (grayscale or color).
        threshold: Minimum value to consider (default: 0.0).

    Returns:
        The sum of the Modified Laplacian values above the threshold. Higher is sharper.

    Raises:
        ValueError: if the image is empty or None.
        ImportError: if OpenCV is not available.
    """
    gray = _ensure_grayscale(image)
    gray = gray.astype(np.float64)

    # Second derivatives
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
