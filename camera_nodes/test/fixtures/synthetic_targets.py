"""
Synthetic MTF Target Generation for Algorithm Validation.

This module generates synthetic test targets with known MTF characteristics
to validate the correctness of the MTF measurement algorithms.

This is test/verification-only helper code and intentionally lives outside the
runtime package under `camera_nodes/camera_nodes/`.

Usage:
    from synthetic_targets import generate_slanted_edge

    # Generate perfect edge with 5 deg slant
    test_img = generate_slanted_edge(angle=5.0, size=200)

    # Measure MTF
    result = analyzer.compute_mtf(test_img)

    # Expected: MTF50 close to theoretical Nyquist/2
"""

import numpy as np
from dataclasses import dataclass

try:
    import cv2
except ImportError:
    cv2 = None


@dataclass
class SyntheticTargetSpec:
    """Specification for a synthetic target with expected MTF values."""

    image: np.ndarray
    expected_mtf50: float  # Expected MTF50 in lp/mm (if pixel_size known)
    expected_mtf50_cycpx: float  # Expected MTF50 in cycles/pixel
    edge_angle: float  # Exact edge angle in degrees
    description: str  # Human-readable description


def generate_slanted_edge(
    angle: float = 5.0,
    size: int = 200,
    contrast: float = 1.0,
    blur_sigma: float = 0.0,
    noise_level: float = 0.0,
) -> np.ndarray:
    """
    Generate a synthetic slanted edge target.

    This creates a perfect step edge with controllable slant angle,
    useful for validating MTF measurement algorithms.

    Args:
        angle: Edge angle in degrees (2-10° recommended for slanted-edge MTF)
        size: Image size in pixels (creates square image)
        contrast: Edge contrast (0-1, default 1.0 = full black-to-white)
        blur_sigma: Gaussian blur sigma to simulate defocus (0 = no blur)
        noise_level: Additive Gaussian noise std dev (0-1 scale, 0 = no noise)

    Returns:
        Grayscale image (uint8) with slanted edge

    Expected MTF:
        - No blur: MTF50 ≈ 0.45 cycles/pixel (near Nyquist limit)
        - With blur (σ=1): MTF50 ≈ 0.25 cycles/pixel
    """
    # Create coordinate grid
    y, x = np.ogrid[:size, :size]

    # Center coordinates
    x_c = x - size / 2
    y_c = y - size / 2

    # Rotate coordinates by angle
    angle_rad = np.radians(angle)
    x_rot = x_c * np.cos(angle_rad) + y_c * np.sin(angle_rad)

    # Create step edge (0 left, 1 right of x_rot=0)
    edge = (x_rot > 0).astype(np.float64)

    # Scale contrast
    low_val = (1.0 - contrast) / 2.0
    high_val = low_val + contrast
    edge = edge * (high_val - low_val) + low_val

    # Apply Gaussian blur if requested (simulates defocus)
    if blur_sigma > 0 and cv2 is not None:
        # Convert to uint8 for cv2
        edge_blur = (edge * 255).astype(np.uint8)
        ksize = int(6 * blur_sigma + 1)
        if ksize % 2 == 0:
            ksize += 1
        edge_blur = cv2.GaussianBlur(edge_blur, (ksize, ksize), blur_sigma)
        edge = edge_blur.astype(np.float64) / 255.0

    # Add noise if requested
    if noise_level > 0:
        noise = np.random.normal(0, noise_level, edge.shape)
        edge = edge + noise
        edge = np.clip(edge, 0, 1)

    # Convert to uint8
    image = (edge * 255).astype(np.uint8)

    return image


def generate_slanted_edge_with_spec(
    angle: float = 5.0,
    size: int = 200,
    blur_sigma: float = 0.0,
    pixel_size_um: float = 2.40,
) -> SyntheticTargetSpec:
    """
    Generate slanted edge with complete specification for validation.

    Returns:
        SyntheticTargetSpec with image and expected MTF values
    """
    image = generate_slanted_edge(angle=angle, size=size, blur_sigma=blur_sigma)

    # Calculate expected MTF50
    if blur_sigma == 0:
        # Perfect edge: MTF50 ≈ 0.45 cycles/pixel
        expected_cycpx = 0.45
    else:
        # Gaussian blur: MTF(f) = exp(-2π²σ²f²)
        # MTF50: solve 0.5 = exp(-2π²σ²f²)
        # f = sqrt(-ln(0.5) / (2π²σ²))
        expected_cycpx = np.sqrt(-np.log(0.5) / (2 * np.pi**2 * blur_sigma**2))
        expected_cycpx = min(expected_cycpx, 0.5)  # Cap at Nyquist

    # Convert to lp/mm
    expected_lpmm = expected_cycpx / (pixel_size_um / 1000.0)

    description = f"Slanted edge (angle={angle}°"
    if blur_sigma > 0:
        description += f", blur σ={blur_sigma}px"
    description += ")"

    return SyntheticTargetSpec(
        image=image,
        expected_mtf50=expected_lpmm,
        expected_mtf50_cycpx=expected_cycpx,
        edge_angle=angle,
        description=description,
    )


def generate_square_target(
    size: int = 400, square_size: int = 200, angle: float = 5.0
) -> np.ndarray:
    """
    Generate a square target with slanted edges (like USAF 1951).

    Useful for testing edge detection and ROI extraction.

    Args:
        size: Overall image size (pixels)
        square_size: Size of the inner square (pixels)
        angle: Rotation angle of square (degrees)

    Returns:
        Grayscale image with centered rotated square
    """
    image = np.zeros((size, size), dtype=np.uint8)

    # Create white square in center
    center = size // 2
    half_sq = square_size // 2

    # Draw square
    pts = np.array(
        [
            [center - half_sq, center - half_sq],
            [center + half_sq, center - half_sq],
            [center + half_sq, center + half_sq],
            [center - half_sq, center + half_sq],
        ],
        dtype=np.int32,
    )

    if cv2 is not None and angle != 0:
        # Rotate square
        M = cv2.getRotationMatrix2D((center, center), angle, 1.0)
        pts_homog = np.concatenate([pts, np.ones((4, 1))], axis=1)
        pts_rot = (M @ pts_homog.T).T
        pts = pts_rot.astype(np.int32)

    if cv2 is not None:
        cv2.fillPoly(image, [pts], 255)
    else:
        # Fallback: axis-aligned square
        image[
            center - half_sq : center + half_sq, center - half_sq : center + half_sq
        ] = 255

    return image


def add_noise(
    image: np.ndarray, noise_type: str = "gaussian", level: float = 0.05
) -> np.ndarray:
    """
    Add realistic noise to test robustness.

    Args:
        image: Input image (uint8)
        noise_type: 'gaussian' or 'poisson'
        level: Noise level (0-1 scale for Gaussian std dev)

    Returns:
        Noisy image (uint8)
    """
    img_float = image.astype(np.float64) / 255.0

    if noise_type == "gaussian":
        noise = np.random.normal(0, level, img_float.shape)
        noisy = img_float + noise
    elif noise_type == "poisson":
        # Poisson noise: λ = pixel value
        scale = 1.0 / level if level > 0 else 1.0
        noisy = np.random.poisson(img_float * scale) / scale
    else:
        raise ValueError(f"Unknown noise type: {noise_type}")

    noisy = np.clip(noisy, 0, 1)
    return (noisy * 255).astype(np.uint8)


def validate_mtf_algorithm(
    analyzer, pixel_size_um: float = 2.40, tolerance_percent: float = 15.0
) -> dict:
    """
    Validate MTF analyzer using synthetic targets.

    Args:
        analyzer: MTFAnalyzer instance
        pixel_size_um: Pixel size in micrometers
        tolerance_percent: Acceptable deviation from expected (%)

    Returns:
        dict with validation results
    """
    results = {"passed": True, "tests": []}

    # Test 1: Perfect edge
    spec1 = generate_slanted_edge_with_spec(
        angle=5.0, blur_sigma=0.0, pixel_size_um=pixel_size_um
    )
    result1 = analyzer.compute_mtf(spec1.image)

    if result1.valid:
        error_pct = (
            abs(result1.mtf50 - spec1.expected_mtf50) / spec1.expected_mtf50 * 100
        )
        test_passed = error_pct < tolerance_percent

        results["tests"].append(
            {
                "name": "Perfect Edge",
                "expected_mtf50": spec1.expected_mtf50,
                "measured_mtf50": result1.mtf50,
                "error_percent": error_pct,
                "passed": test_passed,
            }
        )

        if not test_passed:
            results["passed"] = False
    else:
        results["passed"] = False
        results["tests"].append(
            {"name": "Perfect Edge", "passed": False, "error": result1.error_msg}
        )

    # Test 2: Blurred edge
    spec2 = generate_slanted_edge_with_spec(
        angle=5.0, blur_sigma=1.0, pixel_size_um=pixel_size_um
    )
    result2 = analyzer.compute_mtf(spec2.image)

    if result2.valid:
        error_pct = (
            abs(result2.mtf50 - spec2.expected_mtf50) / spec2.expected_mtf50 * 100
        )
        test_passed = error_pct < tolerance_percent

        results["tests"].append(
            {
                "name": "Blurred Edge (σ=1px)",
                "expected_mtf50": spec2.expected_mtf50,
                "measured_mtf50": result2.mtf50,
                "error_percent": error_pct,
                "passed": test_passed,
            }
        )

        if not test_passed:
            results["passed"] = False
    else:
        results["passed"] = False
        results["tests"].append(
            {"name": "Blurred Edge", "passed": False, "error": result2.error_msg}
        )

    return results
