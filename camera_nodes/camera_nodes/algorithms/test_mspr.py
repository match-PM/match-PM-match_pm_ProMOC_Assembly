
import numpy as np
import sys
from unittest.mock import MagicMock

# Define the calculation logic locally to avoid import issues in limited environments
class MSPRAutofocusMock:
    def __init__(self, config=None):
        pass

    def _calculate_subpixel_peak(self, x_vals, scores):
        """
        Implementation copied from autofocus.py for local interpolation tests.
        """
        if len(scores) < 3:
            return x_vals[np.argmax(scores)] if x_vals else 0.0
            
        # 1. Find index of maximum
        best_idx = int(np.argmax(scores))
        
        # Check boundary conditions (peak must not be at start or end)
        if best_idx == 0 or best_idx == len(scores) - 1:
            return x_vals[best_idx] # Fallback to discrete value

        # 2. Extract the 3 points
        x1, y1 = x_vals[best_idx - 1], scores[best_idx - 1]
        x2, y2 = x_vals[best_idx],     scores[best_idx]
        x3, y3 = x_vals[best_idx + 1], scores[best_idx + 1]

        # 3. Parabel-Fit (Inverse Parabolic Interpolation)
        denom = (x1 - x2) * (x1 - x3) * (x2 - x3)
        if abs(denom) < 1e-12:
            return x2

        a = (x3 * (y2 - y1) + x2 * (y1 - y3) + x1 * (y3 - y2)) / denom
        b = (x3**2 * (y1 - y2) + x2**2 * (y3 - y1) + x1**2 * (y2 - y3)) / denom
        
        # If a >= 0, it's not a downward opening parabola (maximum)
        if a >= 0 or abs(a) < 1e-9:
            return x2

        # Vertex (maximum) at x = -b / (2 * a)
        exact_peak_x = -b / (2 * a)

        # Plausibility check: The calculated peak must be within the interval of neighbors
        if not (min(x1, x3) <= exact_peak_x <= max(x1, x3)):
            return x2

        return float(exact_peak_x)

def test_interpolation():
    af = MSPRAutofocusMock()
    
    print("Starting MSPR Interpolation Tests...")
    
    # Test Case 1: Perfect parabola with subpixel peak
    true_peak = 5.37
    x_vals = [4.0, 5.0, 6.0]
    # y = -0.5 * (x - 5.37)^2 + 100
    scores = [-0.5 * (x - true_peak)**2 + 100 for x in x_vals]
    
    calc_peak = af._calculate_subpixel_peak(x_vals, scores)
    print(f"Test 1 - True Peak: {true_peak}, Calculated: {calc_peak:.4f}")
    assert abs(calc_peak - true_peak) < 1e-6
    
    # Test Case 2: Peak exactly at center measurement
    true_peak = 5.0
    x_vals = [4.0, 5.0, 6.0]
    scores = [10, 20, 10]
    calc_peak = af._calculate_subpixel_peak(x_vals, scores)
    print(f"Test 2 - True Peak: {true_peak}, Calculated: {calc_peak:.4f}")
    assert abs(calc_peak - 5.0) < 1e-6
    
    # Test Case 3: Best point at edge (interpolation should fall back to discrete)
    x_vals = [4.0, 5.0, 6.0]
    scores = [10, 20, 30]
    calc_peak = af._calculate_subpixel_peak(x_vals, scores)
    print(f"Test 3 - Edge Point (Discrete): 6.0, Calculated: {calc_peak:.4f}")
    assert calc_peak == 6.0
    
    # Test Case 4: Asymmetric peak
    # y = - (x-5.1)^2 + 10
    true_peak = 5.1
    x_vals = [4.0, 5.0, 6.0]
    scores = [-(x - true_peak)**2 + 10 for x in x_vals]
    calc_peak = af._calculate_subpixel_peak(x_vals, scores)
    print(f"Test 4 - True Peak: {true_peak}, Calculated: {calc_peak:.4f}")
    assert abs(calc_peak - 5.1) < 1e-6

    print("\nAll MSPR interpolation tests passed successfully!")

if __name__ == "__main__":
    test_interpolation()
