import os
import sys

import matplotlib.pyplot as plt

# Ensure we can import project-local modules when run directly.
_SCRIPT_DIR = os.path.dirname(__file__)
_PACKAGE_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, ".."))
_FIXTURE_DIR = os.path.join(_PACKAGE_ROOT, "test", "fixtures")
for _path in (_PACKAGE_ROOT, _FIXTURE_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from camera_nodes.domain.algorithms.mtf import MTFAnalyzer, MTFConfig  # noqa: E402
from synthetic_targets import generate_slanted_edge  # noqa: E402


def plot_mtf_curve(result, title, filename):
    """Plots the MTF curve (contrast vs frequency)."""
    if not result.valid:
        print(f"Cannot plot invalid result for {title}")
        return

    plt.figure(figsize=(10, 6))
    plt.plot(result.frequencies, result.mtf_values, label="Measured MTF", linewidth=2)
    plt.scatter(
        [result.mtf50],
        [0.5],
        color="r",
        zorder=5,
        label=f"MTF50: {result.mtf50:.1f} lp/mm",
    )
    plt.scatter(
        [result.mtf20],
        [0.2],
        color="orange",
        zorder=5,
        label=f"MTF20: {result.mtf20:.1f} lp/mm",
    )
    plt.axvline(
        x=result.nyquist_frequency,
        color="k",
        linestyle="--",
        label=f"Nyquist: {result.nyquist_frequency:.1f} lp/mm",
    )

    plt.title(f"MTF Curve - {title}")
    plt.xlabel("Spatial Frequency (lp/mm)")
    plt.ylabel("Contrast (MTF)")
    plt.grid(True, which="both", linestyle="--", alpha=0.7)
    plt.legend()
    plt.xlim(0, result.nyquist_frequency * 1.1)
    plt.ylim(0, 1.1)
    print(f"Saving plot to {filename}...")
    plt.savefig(filename)
    plt.close()


def test_simulation():
    print("--- MTF Simulation Test (Verification of Fix) ---")
    config = MTFConfig(pixel_size_um=2.4, min_edge_angle=1.0, max_edge_angle=15.0)
    analyzer = MTFAnalyzer(config)

    print("\n--- Generating PERFECT Edge (+5.0 deg) ---")
    img_sharp = generate_slanted_edge(
        angle=5.0, size=400, contrast=0.8, blur_sigma=0.01
    )
    result_sharp = analyzer.compute_mtf(img_sharp)
    if result_sharp.valid:
        print("  OK Valid: True")
        print(f"  Angle: {result_sharp.edge_angle:.2f}")
        print(f"  MTF50: {result_sharp.mtf50:.2f} lp/mm")

    print("\n--- Generating PERFECT Edge (-5.0 deg) ---")
    img_neg = generate_slanted_edge(angle=-5.0, size=400, contrast=0.8, blur_sigma=0.01)
    result_neg = analyzer.compute_mtf(img_neg)
    if result_neg.valid:
        print("  OK Valid: True")
        print(f"  Angle: {result_neg.edge_angle:.2f}")
        print(f"  MTF50: {result_neg.mtf50:.2f} lp/mm")
    else:
        print(f"  FAIL Invalid: {result_neg.error_msg}")

    print("\n--- Generating BLURRY Edge (Sigma=4.0) ---")
    img_blur = generate_slanted_edge(angle=5.0, size=400, contrast=0.8, blur_sigma=4.0)
    result_blur = analyzer.compute_mtf(img_blur)
    if result_blur.valid:
        print("  OK Valid: True")
        print(f"  MTF50: {result_blur.mtf50:.2f} lp/mm")
        plot_mtf_curve(result_blur, "Blurry Simulation (Sigma=4.0)", "mtf_blur.png")
    else:
        print(f"  FAIL Invalid: {result_blur.error_msg}")


if __name__ == "__main__":
    test_simulation()
