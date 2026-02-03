
import cv2
import numpy as np
import sys
import os
import matplotlib.pyplot as plt

# Ensure we can import the camera_nodes modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'camera_nodes'))

from camera_nodes.algorithms.mtf_analysis import MTFAnalyzer, MTFConfig

def create_slanted_edge(angle_deg, width=200, height=200, contrast=0.8, sigma=2.0):
    """
    Creates a synthetic slanted edge image.
    sigma: controls blur (lower = sharper)
    """
    img = np.zeros((height, width), dtype=np.uint8)
    center_x, center_y = width // 2, height // 2
    
    # Angle in radians (for rotation)
    angle_rad = np.radians(angle_deg)
    
    # Normal vector to the edge
    nx = np.cos(angle_rad)
    ny = np.sin(angle_rad)
    
    # Generate pixel grid
    y, x = np.mgrid[0:height, 0:width]
    
    # Project pixels onto normal vector (distance from edge line passing through center)
    dist = (x - center_x) * nx + (y - center_y) * ny
    
    # Sigmoid edge profile (simulating some blur for realistic MTF)
    # val = -dist / sigma. Clip to avoid overflow.
    val = -dist / sigma
    val = np.clip(val, -500, 500)
    edge_profile = 1.0 / (1.0 + np.exp(val))
    
    # Apply contrast
    low = 128 - (128 * contrast)
    high = 128 + (128 * contrast)
    
    img_float = low + (high - low) * edge_profile
    return img_float.astype(np.uint8)

def plot_mtf_curve(result, title, filename):
    """Plots the MTF curve (Contrast vs Frequency)."""
    if not result.valid:
        print(f"Cannot plot invalid result for {title}")
        return

    plt.figure(figsize=(10, 6))
    
    # Plot Measured Data
    plt.plot(result.frequencies, result.mtf_values, label='Measured MTF', linewidth=2)
    
    # Plot Interpolated points (MTF50, MTF10)
    plt.scatter([result.mtf50], [0.5], color='r', zorder=5, label=f'MTF50: {result.mtf50:.1f} lp/mm')
    plt.scatter([result.mtf20], [0.2], color='orange', zorder=5, label=f'MTF20: {result.mtf20:.1f} lp/mm')
    
    # Plot Nyquist Limit
    plt.axvline(x=result.nyquist_frequency, color='k', linestyle='--', label=f'Nyquist: {result.nyquist_frequency:.1f} lp/mm')
    
    plt.title(f"MTF Curve - {title}")
    plt.xlabel("Spatial Frequency (lp/mm)")
    plt.ylabel("Contrast (MTF)")
    plt.grid(True, which='both', linestyle='--', alpha=0.7)
    plt.legend()
    plt.xlim(0, result.nyquist_frequency * 1.1)
    plt.ylim(0, 1.1)
    
    print(f"Saving plot to {filename}...")
    plt.savefig(filename)
    plt.close()

def test_simulation():
    print("--- MTF Simulation Test (Verification of Fix) ---")
    
    # 1. Setup Analyzer
    config = MTFConfig(
        pixel_size_um=2.4,
        min_edge_angle=1.0, 
        max_edge_angle=15.0
    )
    analyzer = MTFAnalyzer(config)
    
    # Case A: Sharp Edge (simulate in-focus)
    print("\n--- Generating PERFECT Edge (+5.0 deg) ---")
    img_sharp = create_slanted_edge(5.0, width=400, height=400, sigma=0.01) 
    result_sharp = analyzer.compute_mtf(img_sharp)
    if result_sharp.valid:
        print(f"  ✅ Valid: True")
        print(f"  Angle: {result_sharp.edge_angle:.2f}")
        print(f"  MTF50: {result_sharp.mtf50:.2f} lp/mm")

    print("\n--- Generating PERFECT Edge (-5.0 deg) ---")
    img_neg = create_slanted_edge(-5.0, width=400, height=400, sigma=0.01) 
    result_neg = analyzer.compute_mtf(img_neg)
    if result_neg.valid:
        print(f"  ✅ Valid: True")
        print(f"  Angle: {result_neg.edge_angle:.2f}")
        print(f"  MTF50: {result_neg.mtf50:.2f} lp/mm")
    else:
        print(f"  ❌ Invalid: {result_sharp.error_msg}")

    # Case B: Blurry Edge (simulate current state)
    print("\n--- Generating BLURRY Edge (Sigma=4.0) ---")
    img_blur = create_slanted_edge(5.0, width=400, height=400, sigma=4.0) 
    result_blur = analyzer.compute_mtf(img_blur)
    
    if result_blur.valid:
        print(f"  ✅ Valid: True")
        print(f"  MTF50: {result_blur.mtf50:.2f} lp/mm")
        plot_mtf_curve(result_blur, "Blurry Simulation (Sigma=4.0)", "mtf_blur.png")
    else:
        print(f"  ❌ Invalid: {result_blur.error_msg}")

if __name__ == "__main__":
    test_simulation()
