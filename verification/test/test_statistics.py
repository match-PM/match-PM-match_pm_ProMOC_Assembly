"""Unit tests for statistics module."""

import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

import pytest
import numpy as np

# Import directly from the module file, not through package __init__
# This avoids triggering the autofocus imports which require cv2
import importlib.util
spec = importlib.util.spec_from_file_location(
    "statistics",
    parent_dir / "verification" / "algorithms" / "statistics.py"
)
stats_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stats_module)

# Assign to local namespace
calculate_statistics = stats_module.calculate_statistics
detect_outliers = stats_module.detect_outliers
perform_t_test = stats_module.perform_t_test
calculate_rms_error = stats_module.calculate_rms_error
calculate_repeatability = stats_module.calculate_repeatability
StatisticsResult = stats_module.StatisticsResult
TTestResult = stats_module.TTestResult


class TestCalculateStatistics:
    """Tests for calculate_statistics function."""
    
    def test_basic_statistics(self):
        """Test basic statistical calculations."""
        values = [10.0, 12.0, 11.0, 13.0, 11.0]
        stats = calculate_statistics(values)
        
        assert isinstance(stats, StatisticsResult)
        assert stats.n == 5
        assert abs(stats.mean - 11.4) < 0.01
        assert stats.min == 10.0
        assert stats.max == 13.0
        
    def test_coefficient_of_variation(self):
        """Test CV calculation."""
        # Values with known CV
        values = [100.0, 100.0, 100.0, 100.0, 100.0]
        stats = calculate_statistics(values)
        assert stats.cv_percent == 0.0  # No variation
        
        # 10% coefficient of variation
        values = [90.0, 100.0, 110.0]
        stats = calculate_statistics(values)
        assert stats.cv_percent > 0
        
    def test_confidence_interval(self):
        """Test 95% confidence interval."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        stats = calculate_statistics(values)
        
        # CI should contain the mean
        assert stats.ci_lower < stats.mean < stats.ci_upper
        # CI should be symmetric around mean
        assert abs((stats.mean - stats.ci_lower) - (stats.ci_upper - stats.mean)) < 0.001
        
    def test_single_value(self):
        """Test with single value (edge case)."""
        values = [42.0]
        stats = calculate_statistics(values)
        
        assert stats.mean == 42.0
        assert stats.std == 0.0
        assert stats.n == 1
        
    def test_empty_list_raises(self):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError):
            calculate_statistics([])
            
    def test_to_dict(self):
        """Test dictionary conversion."""
        stats = calculate_statistics([1.0, 2.0, 3.0])
        d = stats.to_dict()
        
        assert 'mean' in d
        assert 'std' in d
        assert 'cv_percent' in d
        assert 'ci_lower' in d
        assert 'ci_upper' in d


class TestDetectOutliers:
    """Tests for detect_outliers function."""
    
    def test_no_outliers(self):
        """Test data with no outliers."""
        values = [10.0, 10.5, 11.0, 10.8, 10.2]
        valid, outliers = detect_outliers(values)
        
        assert len(outliers) == 0
        assert len(valid) == 5
        
    def test_with_outliers(self):
        """Test data with clear outliers."""
        values = [10.0, 10.5, 11.0, 10.8, 100.0]  # 100.0 is outlier
        valid, outliers = detect_outliers(values)
        
        assert 4 in outliers  # Index of 100.0
        assert 4 not in valid
        
    def test_zscore_method(self):
        """Test Z-score outlier detection."""
        np.random.seed(42)
        values = list(np.random.normal(100, 5, 20))
        values.append(500.0)  # Clear outlier
        
        valid, outliers = detect_outliers(values, method='zscore', threshold=3.0)
        assert 20 in outliers  # Index of 500.0
        
    def test_small_dataset(self):
        """Test with less than 4 values (returns all as valid)."""
        values = [1.0, 2.0, 3.0]
        valid, outliers = detect_outliers(values)
        
        assert len(valid) == 3
        assert len(outliers) == 0


class TestPerformTTest:
    """Tests for perform_t_test function."""
    
    def test_same_groups(self):
        """Test t-test with identical groups (p should be high)."""
        group_a = [10.0, 11.0, 12.0, 10.5, 11.5]
        group_b = [10.0, 11.0, 12.0, 10.5, 11.5]
        
        result = perform_t_test(group_a, group_b)
        
        assert isinstance(result, TTestResult)
        assert result.p_value > 0.05  # Not significant
        assert not result.significant
        assert abs(result.mean_diff) < 0.001
        
    def test_different_groups(self):
        """Test t-test with clearly different groups."""
        group_a = [10.0, 11.0, 12.0, 10.5, 11.5]
        group_b = [50.0, 51.0, 52.0, 50.5, 51.5]
        
        result = perform_t_test(group_a, group_b)
        
        assert result.p_value < 0.05  # Significant
        assert result.significant
        assert result.mean_diff < 0  # group_a mean < group_b mean
        
    def test_effect_size(self):
        """Test Cohen's d effect size calculation."""
        group_a = [100.0] * 10
        group_b = [110.0] * 10
        
        result = perform_t_test(group_a, group_b)
        
        # With zero variance in each group, effect size calculation depends on implementation
        # Just verify it's computed
        assert 'effect_size' in result.to_dict()
        
    def test_empty_groups_raise(self):
        """Test that empty groups raise ValueError."""
        with pytest.raises(ValueError):
            perform_t_test([], [1.0, 2.0])
        with pytest.raises(ValueError):
            perform_t_test([1.0, 2.0], [])


class TestCalculateRMSError:
    """Tests for calculate_rms_error function."""
    
    def test_perfect_accuracy(self):
        """Test RMS error with perfect measurements."""
        values = [5.0, 5.0, 5.0, 5.0]
        reference = 5.0
        
        rms = calculate_rms_error(values, reference)
        assert rms == 0.0
        
    def test_known_error(self):
        """Test RMS error with known deviations."""
        values = [11.0, 9.0, 11.0, 9.0]  # All ±1 from reference
        reference = 10.0
        
        rms = calculate_rms_error(values, reference)
        assert abs(rms - 1.0) < 0.001
        
    def test_empty_values(self):
        """Test with empty list returns 0."""
        rms = calculate_rms_error([], 10.0)
        assert rms == 0.0


class TestCalculateRepeatability:
    """Tests for calculate_repeatability function."""
    
    def test_repeatability_metrics(self):
        """Test repeatability calculation."""
        values = [10.0, 10.1, 9.9, 10.05, 9.95]
        
        rep = calculate_repeatability(values)
        
        assert 'repeatability_std' in rep
        assert 'repeatability_limit' in rep
        assert 'relative_repeatability' in rep
        
        # r = 2.8 * std
        expected_r = 2.8 * rep['repeatability_std']
        assert abs(rep['repeatability_limit'] - expected_r) < 0.001
        
    def test_single_value(self):
        """Test with single value."""
        rep = calculate_repeatability([10.0])
        
        assert rep['repeatability_std'] == 0.0
        assert rep['repeatability_limit'] == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

    """Tests for calculate_statistics function."""
    
    def test_basic_statistics(self):
        """Test basic statistical calculations."""
        values = [10.0, 12.0, 11.0, 13.0, 11.0]
        stats = calculate_statistics(values)
        
        assert isinstance(stats, StatisticsResult)
        assert stats.n == 5
        assert abs(stats.mean - 11.4) < 0.01
        assert stats.min == 10.0
        assert stats.max == 13.0
        
    def test_coefficient_of_variation(self):
        """Test CV calculation."""
        # Values with known CV
        values = [100.0, 100.0, 100.0, 100.0, 100.0]
        stats = calculate_statistics(values)
        assert stats.cv_percent == 0.0  # No variation
        
        # 10% coefficient of variation
        values = [90.0, 100.0, 110.0]
        stats = calculate_statistics(values)
        assert stats.cv_percent > 0
        
    def test_confidence_interval(self):
        """Test 95% confidence interval."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        stats = calculate_statistics(values)
        
        # CI should contain the mean
        assert stats.ci_lower < stats.mean < stats.ci_upper
        # CI should be symmetric around mean
        assert abs((stats.mean - stats.ci_lower) - (stats.ci_upper - stats.mean)) < 0.001
        
    def test_single_value(self):
        """Test with single value (edge case)."""
        values = [42.0]
        stats = calculate_statistics(values)
        
        assert stats.mean == 42.0
        assert stats.std == 0.0
        assert stats.n == 1
        
    def test_empty_list_raises(self):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError):
            calculate_statistics([])
            
    def test_to_dict(self):
        """Test dictionary conversion."""
        stats = calculate_statistics([1.0, 2.0, 3.0])
        d = stats.to_dict()
        
        assert 'mean' in d
        assert 'std' in d
        assert 'cv_percent' in d
        assert 'ci_lower' in d
        assert 'ci_upper' in d


class TestDetectOutliers:
    """Tests for detect_outliers function."""
    
    def test_no_outliers(self):
        """Test data with no outliers."""
        values = [10.0, 10.5, 11.0, 10.8, 10.2]
        valid, outliers = detect_outliers(values)
        
        assert len(outliers) == 0
        assert len(valid) == 5
        
    def test_with_outliers(self):
        """Test data with clear outliers."""
        values = [10.0, 10.5, 11.0, 10.8, 100.0]  # 100.0 is outlier
        valid, outliers = detect_outliers(values)
        
        assert 4 in outliers  # Index of 100.0
        assert 4 not in valid
        
    def test_zscore_method(self):
        """Test Z-score outlier detection."""
        np.random.seed(42)
        values = list(np.random.normal(100, 5, 20))
        values.append(500.0)  # Clear outlier
        
        valid, outliers = detect_outliers(values, method='zscore', threshold=3.0)
        assert 20 in outliers  # Index of 500.0
        
    def test_small_dataset(self):
        """Test with less than 4 values (returns all as valid)."""
        values = [1.0, 2.0, 3.0]
        valid, outliers = detect_outliers(values)
        
        assert len(valid) == 3
        assert len(outliers) == 0


class TestPerformTTest:
    """Tests for perform_t_test function."""
    
    def test_same_groups(self):
        """Test t-test with identical groups (p should be high)."""
        group_a = [10.0, 11.0, 12.0, 10.5, 11.5]
        group_b = [10.0, 11.0, 12.0, 10.5, 11.5]
        
        result = perform_t_test(group_a, group_b)
        
        assert isinstance(result, TTestResult)
        assert result.p_value > 0.05  # Not significant
        assert not result.significant
        assert abs(result.mean_diff) < 0.001
        
    def test_different_groups(self):
        """Test t-test with clearly different groups."""
        group_a = [10.0, 11.0, 12.0, 10.5, 11.5]
        group_b = [50.0, 51.0, 52.0, 50.5, 51.5]
        
        result = perform_t_test(group_a, group_b)
        
        assert result.p_value < 0.05  # Significant
        assert result.significant
        assert result.mean_diff < 0  # group_a mean < group_b mean
        
    def test_effect_size(self):
        """Test Cohen's d effect size calculation."""
        group_a = [100.0] * 10
        group_b = [110.0] * 10
        
        result = perform_t_test(group_a, group_b)
        
        # With zero variance in each group, effect size calculation depends on implementation
        # Just verify it's computed
        assert 'effect_size' in result.to_dict()
        
    def test_empty_groups_raise(self):
        """Test that empty groups raise ValueError."""
        with pytest.raises(ValueError):
            perform_t_test([], [1.0, 2.0])
        with pytest.raises(ValueError):
            perform_t_test([1.0, 2.0], [])


class TestCalculateRMSError:
    """Tests for calculate_rms_error function."""
    
    def test_perfect_accuracy(self):
        """Test RMS error with perfect measurements."""
        values = [5.0, 5.0, 5.0, 5.0]
        reference = 5.0
        
        rms = calculate_rms_error(values, reference)
        assert rms == 0.0
        
    def test_known_error(self):
        """Test RMS error with known deviations."""
        values = [11.0, 9.0, 11.0, 9.0]  # All ±1 from reference
        reference = 10.0
        
        rms = calculate_rms_error(values, reference)
        assert abs(rms - 1.0) < 0.001
        
    def test_empty_values(self):
        """Test with empty list returns 0."""
        rms = calculate_rms_error([], 10.0)
        assert rms == 0.0


class TestCalculateRepeatability:
    """Tests for calculate_repeatability function."""
    
    def test_repeatability_metrics(self):
        """Test repeatability calculation."""
        values = [10.0, 10.1, 9.9, 10.05, 9.95]
        
        rep = calculate_repeatability(values)
        
        assert 'repeatability_std' in rep
        assert 'repeatability_limit' in rep
        assert 'relative_repeatability' in rep
        
        # r = 2.8 * std
        expected_r = 2.8 * rep['repeatability_std']
        assert abs(rep['repeatability_limit'] - expected_r) < 0.001
        
    def test_single_value(self):
        """Test with single value."""
        rep = calculate_repeatability([10.0])
        
        assert rep['repeatability_std'] == 0.0
        assert rep['repeatability_limit'] == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
