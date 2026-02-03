import pytest
import numpy as np
from verification.algorithms.statistics import (
    check_normality, 
    independent_t_test_robust, 
    calculate_uncertainty_budget
)

class TestRobustStatistics:
    def test_normality_check_normal(self):
        # Generate normal data
        np.random.seed(42)
        data = np.random.normal(loc=50, scale=2, size=50)
        result = check_normality(data)
        
        # Should be identified as normal (high p-value)
        assert result['is_normal'] is True
        assert result['p_value'] > 0.05
    
    def test_normality_check_non_normal(self):
        # Generate uniform data (non-normal)
        np.random.seed(42)
        data = np.random.uniform(low=0, high=100, size=50)
        # Or even better, data with outlier
        data = np.concatenate([np.random.normal(50, 1, 10), [1000.0]])
        
        result = check_normality(data)
        # Should be rejected (low p-value) or at least detected
        # With N=11, Shapiro should detect the outlier
        assert result['is_normal'] is False
        assert result['p_value'] < 0.05

    def test_robust_ttest_parametric(self):
        # Two normal groups with different means
        g1 = np.random.normal(50, 1, 20)
        g2 = np.random.normal(55, 1, 20)
        
        res = independent_t_test_robust(g1, g2)
        assert 'Welch' in res['test_type']
        assert res['significant'] is True

    def test_robust_ttest_nonparametric(self):
        # Two groups with clear outliers making them non-normal
        g1 = np.concatenate([np.random.normal(50, 1, 10), [200.0]])
        g2 = np.concatenate([np.random.normal(50, 1, 10), [-100.0]])
        
        res = independent_t_test_robust(g1, g2)
        assert 'Mann-Whitney' in res['test_type']
        # Depending on outlier, might or might not be significant, but check type switch

    def test_uncertainty_budget_calculation(self):
        # Test calculation with known values
        mtf = 50.0
        budget = calculate_uncertainty_budget(
            mtf_value=mtf,
            pixel_size_um=2.4,
            pixel_size_uncertainty_um=0.05,
            distortion_correction_applied=False, # 5% error
            distortion_max_percent=5.0,
            algorithm_uncertainty_percent=1.5,
            statistical_uncertainty=1.0
        )
        
        # Expected components:
        # Pixel: (0.05/2.4)*50 = 1.041
        # Dist: 0.05*50 = 2.5
        # Algo: 0.015*50 = 0.75
        # Stat: 1.0
        # Combined = sqrt(1.041^2 + 2.5^2 + 0.75^2 + 1.0^2)
        #          = sqrt(1.08 + 6.25 + 0.5625 + 1)
        #          = sqrt(8.89...) approx 2.98
        
        assert budget['u_pixel'] == pytest.approx(1.0416, 0.001)
        assert budget['u_distortion'] == 2.5
        assert budget['u_combined'] > 2.9
        assert budget['u_combined'] < 3.0
        assert budget['U95'] == 2 * budget['u_combined']

    def test_uncertainty_budget_corrected(self):
        # Test with distortion correction applied
        mtf = 50.0
        budget = calculate_uncertainty_budget(
            mtf_value=mtf,
            distortion_correction_applied=True,
            statistical_uncertainty=1.0
        )
        # Distortion should be 20% of original 5% = 1%
        # u_dist = 0.01 * 50 = 0.5
        assert budget['u_distortion'] == 0.5
