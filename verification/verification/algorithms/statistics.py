"""Statistical Analysis Utilities for Verification.

Provides statistical functions for analyzing autofocus and MTF measurements:
- Descriptive statistics (mean, std, CV, confidence intervals)
- Outlier detection (IQR method)
- Statistical tests (t-test for group comparison)

Usage:
    from verification.algorithms.statistics import calculate_statistics, perform_t_test
    
    stats = calculate_statistics([1.2, 1.3, 1.25, 1.28])
    print(f"Mean: {stats['mean']:.3f} ± {stats['std']:.3f}")
    print(f"CV: {stats['cv_percent']:.1f}%")
    print(f"95% CI: [{stats['ci_lower']:.3f}, {stats['ci_upper']:.3f}]")
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np

# Try scipy, fall back to manual implementations
try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


@dataclass
class StatisticsResult:
    """Result container for descriptive statistics."""
    mean: float
    std: float
    variance: float
    cv_percent: float  # Coefficient of Variation in %
    ci_lower: float    # 95% CI lower bound
    ci_upper: float    # 95% CI upper bound
    min: float
    max: float
    median: float
    n: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'mean': self.mean,
            'std': self.std,
            'variance': self.variance,
            'cv_percent': self.cv_percent,
            'ci_lower': self.ci_lower,
            'ci_upper': self.ci_upper,
            'min': self.min,
            'max': self.max,
            'median': self.median,
            'n': self.n
        }


@dataclass
class TTestResult:
    """Result container for t-test."""
    t_statistic: float
    p_value: float
    significant: bool  # True if p < 0.05
    confidence_level: float
    mean_diff: float
    effect_size: float  # Cohen's d
    
    def to_dict(self) -> dict:
        return {
            't_statistic': self.t_statistic,
            'p_value': self.p_value,
            'significant': self.significant,
            'confidence_level': self.confidence_level,
            'mean_diff': self.mean_diff,
            'effect_size': self.effect_size
        }


def calculate_statistics(values: List[float], confidence: float = 0.95) -> StatisticsResult:
    """
    Calculate comprehensive descriptive statistics.
    
    Args:
        values: List of numeric values
        confidence: Confidence level for CI (default: 0.95)
        
    Returns:
        StatisticsResult with all computed statistics
        
    Raises:
        ValueError: If values list is empty
    """
    if not values:
        raise ValueError("Cannot calculate statistics for empty list")
    
    arr = np.array(values, dtype=np.float64)
    n = len(arr)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1)) if n > 1 else 0.0  # Sample std with Bessel's correction
    variance = std ** 2
    
    # Coefficient of Variation (CV)
    cv_percent = (std / mean * 100) if mean != 0 else 0.0
    
    # 95% Confidence Interval
    if n > 1:
        if HAS_SCIPY:
            t_crit = scipy_stats.t.ppf((1 + confidence) / 2, df=n-1)
        else:
            # Approximate t-critical for 95% CI (good enough for n >= 10)
            t_crit = 1.96 if n > 30 else 2.0 + 4.0 / n
        
        margin = t_crit * std / np.sqrt(n)
        ci_lower = mean - margin
        ci_upper = mean + margin
    else:
        ci_lower = mean
        ci_upper = mean
    
    return StatisticsResult(
        mean=mean,
        std=std,
        variance=variance,
        cv_percent=cv_percent,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        min=float(np.min(arr)),
        max=float(np.max(arr)),
        median=float(np.median(arr)),
        n=n
    )


def detect_outliers(values: List[float], method: str = 'iqr', 
                    threshold: float = 1.5) -> Tuple[List[int], List[int]]:
    """
    Detect outliers using IQR or Z-score method.
    
    Args:
        values: List of numeric values
        method: 'iqr' (Interquartile Range) or 'zscore'
        threshold: IQR multiplier (default 1.5) or Z-score threshold (default 3.0)
        
    Returns:
        Tuple of (valid_indices, outlier_indices)
    """
    if len(values) < 4:
        # Not enough data for meaningful outlier detection
        return list(range(len(values))), []
    
    arr = np.array(values, dtype=np.float64)
    
    if method == 'iqr':
        q1, q3 = np.percentile(arr, [25, 75])
        iqr = q3 - q1
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr
        is_outlier = (arr < lower_bound) | (arr > upper_bound)
    elif method == 'zscore':
        z_threshold = threshold if threshold > 1 else 3.0
        mean = np.mean(arr)
        std = np.std(arr)
        if std == 0:
            is_outlier = np.zeros(len(arr), dtype=bool)
        else:
            z_scores = np.abs((arr - mean) / std)
            is_outlier = z_scores > z_threshold
    else:
        raise ValueError(f"Unknown method: {method}. Use 'iqr' or 'zscore'")
    
    valid_indices = [i for i, outlier in enumerate(is_outlier) if not outlier]
    outlier_indices = [i for i, outlier in enumerate(is_outlier) if outlier]
    
    return valid_indices, outlier_indices


def perform_t_test(group_a: List[float], group_b: List[float], 
                   alpha: float = 0.05, paired: bool = False) -> TTestResult:
    """
    Perform independent or paired two-sample t-test.
    
    Args:
        group_a: First group of measurements
        group_b: Second group of measurements
        alpha: Significance level (default: 0.05)
        paired: If True, perform paired t-test (requires equal lengths)
        
    Returns:
        TTestResult with test statistics and significance
    """
    if not group_a or not group_b:
        raise ValueError("Both groups must contain values")
    
    a = np.array(group_a, dtype=np.float64)
    b = np.array(group_b, dtype=np.float64)
    
    mean_a = np.mean(a)
    mean_b = np.mean(b)
    mean_diff = mean_a - mean_b
    
    if HAS_SCIPY:
        if paired:
            if len(a) != len(b):
                raise ValueError("Paired t-test requires equal length groups")
            t_stat, p_val = scipy_stats.ttest_rel(a, b)
        else:
            t_stat, p_val = scipy_stats.ttest_ind(a, b, equal_var=False)  # Welch's t-test
    else:
        # Manual implementation (Welch's t-test)
        n_a, n_b = len(a), len(b)
        var_a = np.var(a, ddof=1)
        var_b = np.var(b, ddof=1)
        
        se = np.sqrt(var_a / n_a + var_b / n_b)
        t_stat = mean_diff / se if se > 0 else 0.0
        
        # Approximate p-value (rough estimation without scipy)
        # This is a simplified approach - use scipy for accurate results
        df = n_a + n_b - 2
        p_val = 2 * (1 - _approx_t_cdf(abs(t_stat), df))
    
    significant = p_val < alpha
    
    # Cohen's d (effect size)
    pooled_std = np.sqrt((np.var(a, ddof=1) + np.var(b, ddof=1)) / 2)
    effect_size = mean_diff / pooled_std if pooled_std > 0 else 0.0
    
    return TTestResult(
        t_statistic=float(t_stat),
        p_value=float(p_val),
        significant=significant,
        confidence_level=1 - alpha,
        mean_diff=float(mean_diff),
        effect_size=float(effect_size)
    )


def _approx_t_cdf(t: float, df: int) -> float:
    """
    Approximate t-distribution CDF (fallback without scipy).
    Uses normal approximation for large df.
    """
    # For large df, t-distribution approaches normal
    if df > 30:
        # Normal approximation using error function
        return 0.5 * (1 + _erf(t / np.sqrt(2)))
    else:
        # Very rough approximation - use scipy for accuracy!
        x = df / (df + t**2)
        return 1 - 0.5 * x ** (df/2)


def _erf(x: float) -> float:
    """Approximation of error function."""
    # Horner form of approximation
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    p = 0.3275911
    sign = 1 if x >= 0 else -1
    x = abs(x)
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * np.exp(-x * x)
    return sign * y


def calculate_rms_error(values: List[float], reference: float) -> float:
    """
    Calculate Root Mean Square Error from reference value.
    
    Args:
        values: List of measurements
        reference: True/reference value
        
    Returns:
        RMS error value
    """
    if not values:
        return 0.0
    arr = np.array(values, dtype=np.float64)
    return float(np.sqrt(np.mean((arr - reference) ** 2)))


def calculate_repeatability(values: List[float]) -> dict:
    """
    Calculate repeatability metrics per ISO 5725.
    
    Returns:
        Dict with repeatability std, limit (r), and relative repeatability
    """
    if len(values) < 2:
        return {'repeatability_std': 0.0, 'repeatability_limit': 0.0, 'relative_repeatability': 0.0}
    
    stats = calculate_statistics(values)
    
    # Repeatability limit r = 2.8 * sr (for 95% confidence, 2 measurements)
    r_limit = 2.8 * stats.std
    
    return {
        'repeatability_std': stats.std,
        'repeatability_limit': r_limit,
        'relative_repeatability': stats.cv_percent
    }
