"""Enhanced plotting utilities for verification results.

Provides comprehensive visualization for:
- Autofocus algorithm comparison with convergence graphs
- MTF curve overlays and field curvature maps
- Statistical analysis with error bars and confidence intervals
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Import statistics functions
try:
    from ..algorithms.statistics import calculate_statistics, detect_outliers, perform_t_test
except ImportError:
    # Fallback for standalone usage
    calculate_statistics = None


class ResultsPlotter:
    """Enhanced plotter for verification results."""
    
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Set style
        plt.style.use('bmh')
        # Color palette
        self.colors = {
            'goldensection': '#1f77b4',
            'hillclimbing': '#ff7f0e', 
            'parabolic': '#2ca02c',
            'fibonacci': '#d62728',
            'exhaustive': '#9467bd',
            'exhaustive (GT)': '#9467bd',
            'exhaustive (periodic)': '#8c564b',
            'baseline': '#1f77b4',
            'strahlteiler': '#d62728',
        }

    def plot_autofocus_verification(self, records: list, filename="af_verification.png"):
        """
        Plots autofocus verification results with enhanced statistics.
        
        records: list of dicts with keys: algorithm, duration_s, deviation_from_ref_mm, measurements, focus_score
        """
        if not records:
            return None

        df = pd.DataFrame(records)
        cols = ['duration_s', 'deviation_from_ref_mm', 'measurements', 'focus_score']
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')

        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Autofocus Algorithm Verification Results', fontsize=16, fontweight='bold')

        algorithms = df['algorithm'].unique()
        colors = [self.colors.get(a, '#333333') for a in algorithms]

        # 1. Boxplot: Deviation (Precision) with outlier markers
        if 'deviation_from_ref_mm' in df.columns:
            boxprops = dict(facecolor='lightblue', alpha=0.7)
            df.boxplot(column='deviation_from_ref_mm', by='algorithm', ax=axes[0, 0],
                      patch_artist=True, boxprops=boxprops)
            axes[0, 0].set_title('Position Accuracy (Deviation from Reference)')
            axes[0, 0].set_ylabel('Deviation (mm)')
            axes[0, 0].set_xlabel('')
            axes[0, 0].axhline(y=0, color='green', linestyle='--', alpha=0.5, label='Reference')
            axes[0, 0].axhline(y=0.02, color='orange', linestyle=':', alpha=0.7, label='±20µm tolerance')
            axes[0, 0].axhline(y=-0.02, color='orange', linestyle=':', alpha=0.7)
            axes[0, 0].legend(loc='upper right', fontsize=8)

        # 2. Bar Chart: Mean Duration with error bars
        if 'duration_s' in df.columns:
            grouped = df.groupby('algorithm')['duration_s']
            means = grouped.mean()
            stds = grouped.std()
            x_pos = range(len(means))
            bars = axes[0, 1].bar(x_pos, means, yerr=stds, capsize=5, 
                                  color=[self.colors.get(a, '#999') for a in means.index],
                                  alpha=0.8, edgecolor='black')
            axes[0, 1].set_title('Execution Time (Mean ± Std)')
            axes[0, 1].set_ylabel('Time (s)')
            axes[0, 1].set_xticks(x_pos)
            axes[0, 1].set_xticklabels(means.index, rotation=45, ha='right')
            
            # Add value labels on bars
            for bar, mean, std in zip(bars, means, stds):
                axes[0, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + std + 0.1,
                               f'{mean:.2f}s', ha='center', va='bottom', fontsize=8)

        # 3. Bar Chart: Measurements Count (Efficiency)
        if 'measurements' in df.columns:
            grouped = df.groupby('algorithm')['measurements']
            means = grouped.mean()
            stds = grouped.std()
            x_pos = range(len(means))
            bars = axes[1, 0].bar(x_pos, means, yerr=stds, capsize=5,
                                  color=[self.colors.get(a, '#999') for a in means.index],
                                  alpha=0.8, edgecolor='black')
            axes[1, 0].set_title('Measurement Count (Efficiency)')
            axes[1, 0].set_ylabel('Number of Measurements')
            axes[1, 0].set_xticks(x_pos)
            axes[1, 0].set_xticklabels(means.index, rotation=45, ha='right')

        # 4. Success Rate or Focus Score Distribution
        if 'success' in df.columns:
            success_rate = df.groupby('algorithm')['success'].mean() * 100
            x_pos = range(len(success_rate))
            bars = axes[1, 1].bar(x_pos, success_rate, 
                                  color=[self.colors.get(a, '#999') for a in success_rate.index],
                                  alpha=0.8, edgecolor='black')
            axes[1, 1].set_title('Success Rate (±20µm tolerance)')
            axes[1, 1].set_ylabel('Success Rate (%)')
            axes[1, 1].set_ylim(0, 105)
            axes[1, 1].set_xticks(x_pos)
            axes[1, 1].set_xticklabels(success_rate.index, rotation=45, ha='right')
            axes[1, 1].axhline(y=95, color='green', linestyle='--', alpha=0.5, label='95% target')
            axes[1, 1].legend()
        elif 'focus_score' in df.columns:
            df.boxplot(column='focus_score', by='algorithm', ax=axes[1, 1])
            axes[1, 1].set_title('Focus Score Distribution')
            axes[1, 1].set_ylabel('Tenengrad Score')

        plt.tight_layout()
        plt.subplots_adjust(top=0.90)
        
        save_path = self.output_dir / filename
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return save_path

    def plot_convergence_curves(self, convergence_data: List[Dict], 
                                filename="af_convergence.png") -> Optional[Path]:
        """
        Plot autofocus convergence curves (Score vs Position).
        
        Args:
            convergence_data: List of dicts with keys:
                - algorithm: str
                - positions: List[float] (mm)
                - scores: List[float]
                - best_position: float (optional)
            filename: Output filename
            
        Returns:
            Path to saved figure or None
        """
        if not convergence_data:
            return None
            
        n_runs = len(convergence_data)
        n_cols = min(3, n_runs)
        n_rows = (n_runs + n_cols - 1) // n_cols
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(5*n_cols, 4*n_rows))
        if n_runs == 1:
            axes = np.array([axes])
        axes = axes.flatten()
        
        fig.suptitle('Autofocus Convergence Analysis', fontsize=14, fontweight='bold')
        
        for idx, data in enumerate(convergence_data):
            ax = axes[idx]
            algo = data.get('algorithm', 'Unknown')
            positions = data.get('positions', [])
            scores = data.get('scores', [])
            best_pos = data.get('best_position')
            
            color = self.colors.get(algo, '#1f77b4')
            
            # Plot trajectory
            ax.plot(positions, scores, 'o-', color=color, markersize=4, 
                   linewidth=1.5, alpha=0.8, label='Search path')
            
            # Mark best position
            if best_pos is not None and scores:
                best_idx = None
                for i, p in enumerate(positions):
                    if abs(p - best_pos) < 0.001:
                        best_idx = i
                        break
                if best_idx is not None:
                    ax.axvline(x=best_pos, color='green', linestyle='--', alpha=0.6)
                    ax.scatter([best_pos], [scores[best_idx]], s=100, c='green', 
                              marker='*', zorder=5, label=f'Best: {best_pos:.3f}mm')
            
            # Mark start and end
            if positions:
                ax.scatter([positions[0]], [scores[0]], s=60, c='blue', 
                          marker='s', zorder=4, label='Start')
                ax.scatter([positions[-1]], [scores[-1]], s=60, c='red',
                          marker='D', zorder=4, label='End')
            
            ax.set_xlabel('Position (mm)')
            ax.set_ylabel('Focus Score (Tenengrad)')
            ax.set_title(f'{algo}', fontsize=11)
            ax.legend(loc='best', fontsize=7)
            ax.grid(True, alpha=0.3)
        
        # Hide unused subplots
        for idx in range(n_runs, len(axes)):
            axes[idx].set_visible(False)
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.92)
        
        save_path = self.output_dir / filename
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return save_path

    def plot_mtf_verification(self, baseline_data: dict, st_data: dict, 
                              filename="mtf_impact.png") -> Optional[Path]:
        """
        Plots MTF comparison with error bars and statistical test.
        
        Args:
            baseline_data: dict with mtf50, mtf50_std, raw_data (optional)
            st_data: dict with mtf50, mtf50_std, raw_data (optional)
        """
        if not baseline_data or not st_data:
            return None

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle('MTF Verification: Optical Degradation Analysis', fontsize=14, fontweight='bold')

        # Left: Bar comparison with error bars
        ax1 = axes[0]
        labels = ['MTF50']
        
        baseline_mean = baseline_data.get('mtf50', baseline_data.get('mtf50_mean', 0))
        st_mean = st_data.get('mtf50', st_data.get('mtf50_mean', 0))
        baseline_std = baseline_data.get('mtf50_std', 0)
        st_std = st_data.get('mtf50_std', 0)
        
        x = np.arange(len(labels))
        width = 0.35

        rects1 = ax1.bar(x - width/2, [baseline_mean], width, yerr=[baseline_std], 
                        capsize=8, label='Baseline', color=self.colors['baseline'], 
                        alpha=0.8, edgecolor='black')
        rects2 = ax1.bar(x + width/2, [st_mean], width, yerr=[st_std], 
                        capsize=8, label='With Strahlteiler', color=self.colors['strahlteiler'],
                        alpha=0.8, edgecolor='black')

        ax1.set_ylabel('Frequency (lp/mm)', fontsize=11)
        ax1.set_title('MTF50 Comparison')
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels)
        ax1.legend()
        ax1.grid(axis='y', alpha=0.3)

        # Add value labels
        ax1.bar_label(rects1, labels=[f'{baseline_mean:.2f}'], padding=3, fontsize=10)
        ax1.bar_label(rects2, labels=[f'{st_mean:.2f}'], padding=3, fontsize=10)

        # Statistical annotation
        if baseline_mean > 0:
            deg = (baseline_mean - st_mean) / baseline_mean * 100
            text = f"Degradation: {deg:.1f}%\n"
            
            # T-test if raw data available
            bl_raw = baseline_data.get('raw_data', [])
            st_raw = st_data.get('raw_data', [])
            
            if bl_raw and st_raw and perform_t_test is not None:
                bl_vals = [r['mtf50'] for r in bl_raw if 'mtf50' in r]
                st_vals = [r['mtf50'] for r in st_raw if 'mtf50' in r]
                
                if bl_vals and st_vals:
                    t_result = perform_t_test(bl_vals, st_vals)
                    text += f"t-test: p={t_result.p_value:.4f}\n"
                    text += f"{'Significant' if t_result.significant else 'Not significant'} (α=0.05)"
            elif baseline_std > 0:
                sigma_diff = (baseline_mean - st_mean) / baseline_std
                text += f"Difference: {sigma_diff:.1f}σ"
                
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.7)
            ax1.text(0.5, 0.95, text, transform=ax1.transAxes, fontsize=10,
                    verticalalignment='top', bbox=props, ha='center')

        # Right: Distribution comparison (if raw data available)
        ax2 = axes[1]
        bl_raw = baseline_data.get('raw_data', [])
        st_raw = st_data.get('raw_data', [])
        
        if bl_raw and st_raw:
            bl_vals = [r['mtf50'] for r in bl_raw if 'mtf50' in r]
            st_vals = [r['mtf50'] for r in st_raw if 'mtf50' in r]
            
            if bl_vals and st_vals:
                # Create violin plot
                data = [bl_vals, st_vals]
                parts = ax2.violinplot(data, positions=[0, 1], showmeans=True, showmedians=True)
                
                # Color the violins
                for i, pc in enumerate(parts['bodies']):
                    color = self.colors['baseline'] if i == 0 else self.colors['strahlteiler']
                    pc.set_facecolor(color)
                    pc.set_alpha(0.6)
                
                # Overlay scatter points
                for i, vals in enumerate(data):
                    x_jitter = np.random.normal(i, 0.04, len(vals))
                    ax2.scatter(x_jitter, vals, alpha=0.5, s=20, 
                               color=self.colors['baseline'] if i == 0 else self.colors['strahlteiler'])
                
                ax2.set_xticks([0, 1])
                ax2.set_xticklabels(['Baseline', 'Strahlteiler'])
                ax2.set_ylabel('MTF50 (lp/mm)')
                ax2.set_title('Distribution Comparison')
                ax2.grid(axis='y', alpha=0.3)
        else:
            ax2.text(0.5, 0.5, 'Raw data not available\nfor distribution plot',
                    ha='center', va='center', transform=ax2.transAxes, fontsize=12)
            ax2.set_axis_off()

        plt.tight_layout()
        plt.subplots_adjust(top=0.88)
        
        save_path = self.output_dir / filename
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return save_path

    def plot_mtf_curves(self, mtf_results: List[Dict], 
                        filename="mtf_curves.png") -> Optional[Path]:
        """
        Plot overlaid MTF curves from multiple measurements.
        
        Args:
            mtf_results: List of dicts with keys:
                - frequencies: np.ndarray (lp/mm)
                - mtf_values: np.ndarray (0-1)
                - label: str (optional)
                - color: str (optional)
        """
        if not mtf_results:
            return None
            
        fig, ax = plt.subplots(figsize=(10, 7))
        
        for i, result in enumerate(mtf_results):
            freqs = result.get('frequencies', np.array([]))
            mtf = result.get('mtf_values', np.array([]))
            label = result.get('label', f'Measurement {i+1}')
            color = result.get('color', None)
            
            if len(freqs) == 0 or len(mtf) == 0:
                continue
                
            # Only positive frequencies
            mask = freqs >= 0
            ax.plot(freqs[mask], mtf[mask], label=label, color=color, 
                   linewidth=1.5, alpha=0.8)
        
        # Add reference lines
        ax.axhline(y=0.5, color='red', linestyle='--', alpha=0.5, label='MTF50')
        ax.axhline(y=0.2, color='orange', linestyle='--', alpha=0.5, label='MTF20')
        ax.axhline(y=0.1, color='yellow', linestyle='--', alpha=0.5, label='MTF10')
        
        ax.set_xlabel('Spatial Frequency (lp/mm)', fontsize=11)
        ax.set_ylabel('MTF', fontsize=11)
        ax.set_title('MTF Curves Comparison', fontsize=14, fontweight='bold')
        ax.set_xlim(left=0)
        ax.set_ylim(0, 1.05)
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        save_path = self.output_dir / filename
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return save_path

    def plot_field_curvature_map(self, field_data: Dict[str, float],
                                  filename="field_curvature.png") -> Optional[Path]:
        """
        Plot MTF50 values across the image field as a heatmap.
        
        Args:
            field_data: Dict mapping position names to MTF50 values
                e.g., {'center': 45.2, 'top_left': 38.1, 'top_right': 39.5, ...}
        """
        if not field_data:
            return None
            
        fig, ax = plt.subplots(figsize=(8, 8))
        
        # Define positions on unit square
        positions = {
            'top_left': (0.15, 0.85),
            'top_right': (0.85, 0.85),
            'center': (0.5, 0.5),
            'bottom_left': (0.15, 0.15),
            'bottom_right': (0.85, 0.15),
        }
        
        # Get min/max for color scaling
        values = list(field_data.values())
        vmin, vmax = min(values), max(values)
        
        # Create colormap
        cmap = plt.cm.RdYlGn  # Red=bad, Green=good
        
        for name, (x, y) in positions.items():
            if name in field_data:
                value = field_data[name]
                # Normalize for color
                norm_val = (value - vmin) / (vmax - vmin) if vmax > vmin else 0.5
                color = cmap(norm_val)
                
                # Draw circle
                circle = plt.Circle((x, y), 0.12, color=color, alpha=0.8)
                ax.add_patch(circle)
                
                # Add text
                ax.text(x, y, f'{value:.1f}', ha='center', va='center',
                       fontsize=14, fontweight='bold')
                ax.text(x, y - 0.17, name.replace('_', ' ').title(), 
                       ha='center', va='top', fontsize=9)
        
        # Draw image boundary
        rect = plt.Rectangle((0, 0), 1, 1, fill=False, edgecolor='black', linewidth=2)
        ax.add_patch(rect)
        
        ax.set_xlim(-0.1, 1.1)
        ax.set_ylim(-0.1, 1.1)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title('Field Curvature Map (MTF50 in lp/mm)', fontsize=14, fontweight='bold')
        
        # Add colorbar
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin, vmax))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, shrink=0.6, label='MTF50 (lp/mm)')
        
        plt.tight_layout()
        
        save_path = self.output_dir / filename
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return save_path

    def plot_correlation(self, x_data: List[float], y_data: List[float],
                         x_label: str = "Focus Score", y_label: str = "MTF50 (lp/mm)",
                         filename="correlation.png") -> Optional[Path]:
        """
        Plot correlation between two variables (e.g., focus score vs MTF).
        
        Args:
            x_data: X-axis values
            y_data: Y-axis values  
            x_label: X-axis label
            y_label: Y-axis label
        """
        if not x_data or not y_data or len(x_data) != len(y_data):
            return None
            
        fig, ax = plt.subplots(figsize=(8, 6))
        
        x = np.array(x_data)
        y = np.array(y_data)
        
        # Scatter plot
        ax.scatter(x, y, alpha=0.7, s=50, edgecolors='black', linewidth=0.5)
        
        # Fit linear regression
        if len(x) > 2:
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            x_line = np.linspace(x.min(), x.max(), 100)
            ax.plot(x_line, p(x_line), 'r--', alpha=0.7, label=f'Linear fit: y={z[0]:.4f}x + {z[1]:.2f}')
            
            # Calculate R²
            y_pred = p(x)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            ax.text(0.05, 0.95, f'R² = {r_squared:.3f}', transform=ax.transAxes,
                   fontsize=11, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        ax.set_xlabel(x_label, fontsize=11)
        ax.set_ylabel(y_label, fontsize=11)
        ax.set_title(f'{y_label} vs {x_label}', fontsize=14, fontweight='bold')
        ax.legend(loc='lower right')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        save_path = self.output_dir / filename
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return save_path

    def create_summary_table(self, af_records: List[Dict], 
                             filename="algorithm_summary.png") -> Optional[Path]:
        """
        Create a summary table comparing algorithm performance.
        """
        if not af_records:
            return None
            
        df = pd.DataFrame(af_records)
        
        # Calculate summary statistics per algorithm
        summary = df.groupby('algorithm').agg({
            'duration_s': ['mean', 'std'],
            'measurements': ['mean', 'std'],
            'deviation_from_ref_mm': lambda x: np.abs(x).mean(),
            'success': 'mean'
        }).round(3)
        
        summary.columns = ['Time (s)', 'Time σ', 'Measurements', 'Meas σ', 
                          'Mean |Deviation| (mm)', 'Success Rate']
        summary['Success Rate'] = (summary['Success Rate'] * 100).round(1).astype(str) + '%'
        
        fig, ax = plt.subplots(figsize=(12, len(summary) * 0.5 + 2))
        ax.axis('off')
        
        table = ax.table(cellText=summary.values,
                        colLabels=summary.columns,
                        rowLabels=summary.index,
                        cellLoc='center',
                        loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.5)
        
        ax.set_title('Algorithm Performance Summary', fontsize=14, fontweight='bold', 
                    pad=20)
        
        plt.tight_layout()
        
        save_path = self.output_dir / filename
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return save_path

    def plot_correlation_verification(self, result_data: Dict, filename: str = 'correlation.png'):
        """Plots the correlation between Autofocus (Tenengrad) and MTF Proxy curves."""
        data = result_data.get('data', [])
        if not data:
            return None
            
        df = pd.DataFrame(data)
        
        fig, ax1 = plt.subplots(figsize=(10, 6))
        
        color1 = 'tab:blue'
        ax1.set_xlabel('Position (mm)')
        ax1.set_ylabel('Focus Metric (Tenengrad)', color=color1)
        l1 = ax1.plot(df['pos'], df['tenengrad'], color=color1, marker='o', label='Tenengrad (Focus)')
        ax1.tick_params(axis='y', labelcolor=color1)
        
        ax2 = ax1.twinx()
        color2 = 'tab:orange'
        ax2.set_ylabel('Quality Metric (MTF Proxy)', color=color2)
        l2 = ax2.plot(df['pos'], df['mtf'], color=color2, marker='x', linestyle='--', label='MTF Proxy 90%')
        ax2.tick_params(axis='y', labelcolor=color2)
        
        # Peaks
        peak_af = result_data.get('max_af_pos')
        peak_mtf = result_data.get('max_mtf_pos')
        shift = result_data.get('peak_shift', 0)
        
        if peak_af:
             l3 = ax1.axvline(peak_af, color=color1, linestyle=':', alpha=0.5, label=f'AF Peak {peak_af:.3f}')
        if peak_mtf:
             l4 = ax2.axvline(peak_mtf, color=color2, linestyle=':', alpha=0.5, label=f'MTF Peak {peak_mtf:.3f}')
             
        plt.title(f'AF vs MTF Correlation (Shift: {shift:.3f} mm)')
        
        # Legend
        lns = l1 + l2
        labs = [l.get_label() for l in lns]
        ax1.legend(lns, labs, loc='upper center', bbox_to_anchor=(0.5, -0.15),
                 ncol=2)
                 
        plt.tight_layout()
        save_path = self.output_dir / filename
        plt.savefig(save_path, dpi=150)
        plt.close(fig)
        return save_path


