import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path

class ResultsPlotter:
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Set style
        plt.style.use('bmh')

    def plot_autofocus_verification(self, records: list, filename="af_verification.png"):
        """
        Plots autofocus verification results.
        records: list of dicts with keys: algorithm, duration_s, deviation_from_ref_mm, measurements
        """
        if not records:
            return

        df = pd.DataFrame(records)
        # Convert numeric columns
        cols = ['duration_s', 'deviation_from_ref_mm', 'measurements', 'focus_score']
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c])

        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Autofocus Algorithm Verification Results', fontsize=16)

        # 1. Boxplot: Deviation (Precision)
        if 'deviation_from_ref_mm' in df.columns:
            df.boxplot(column='deviation_from_ref_mm', by='algorithm', ax=axes[0, 0])
            axes[0, 0].set_title('Accuracy Deviation from Reference')
            axes[0, 0].set_ylabel('Deviation (mm)')
            axes[0, 0].set_xlabel('')

        # 2. Bar Chart: Mean Duration (Speed)
        avg_time = df.groupby('algorithm')['duration_s'].mean()
        avg_time.plot(kind='bar', ax=axes[0, 1], color='orange', alpha=0.7)
        axes[0, 1].set_title('Average Execution Time')
        axes[0, 1].set_ylabel('Time (s)')

        # 3. Bar Chart: Measurements Count (Efficiency)
        avg_meas = df.groupby('algorithm')['measurements'].mean()
        avg_meas.plot(kind='bar', ax=axes[1, 0], color='green', alpha=0.7)
        axes[1, 0].set_title('Average No. of Measurements')
        axes[1, 0].set_ylabel('Count')

        # 4. Success Rate (if we had a success/fail column, otherwise Score variance)
        if 'focus_score' in df.columns:
            df.boxplot(column='focus_score', by='algorithm', ax=axes[1, 1])
            axes[1, 1].set_title('Focus Score Distribution')
            axes[1, 1].set_ylabel('Tenengrad Score')

        plt.tight_layout()
        plt.subplots_adjust(top=0.90) # Adjust for suptitle
        
        save_path = self.output_dir / filename
        plt.savefig(save_path, dpi=150)
        plt.close(fig)
        return save_path

    def plot_mtf_verification(self, baseline_data, st_data, filename="mtf_impact.png"):
        """
        Plots MTF comparison (Baseline vs Strahlteiler) with optional error bars.
        Data should be dicts with keys: mtf50 (mean), mtf50_std (optional)
        """
        if not baseline_data or not st_data:
            return

        labels = ['MTF50']
        
        # Extract means
        baseline_mean = baseline_data.get('mtf50', 0)
        st_mean = st_data.get('mtf50', 0)
        
        # Extract std devs (if available)
        baseline_std = baseline_data.get('mtf50_std', 0)
        st_std = st_data.get('mtf50_std', 0)
        
        x = np.arange(len(labels))
        width = 0.35

        fig, ax = plt.subplots(figsize=(8, 6))
        
        # Plot bars with error bars
        rects1 = ax.bar(x - width/2, [baseline_mean], width, yerr=[baseline_std], 
                        capsize=5, label='Baseline', color='skyblue')
        rects2 = ax.bar(x + width/2, [st_mean], width, yerr=[st_std], 
                        capsize=5, label='With Strahlteiler', color='lightcoral')

        ax.set_ylabel('Frequency (lp/mm)')
        ax.set_title('Optical Degradation Analysis (MTF50)')
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)

        # Add labels logic
        # ax.bar_label(rects1, padding=3, fmt='%.2f') 
        # ax.bar_label(rects2, padding=3, fmt='%.2f')

        # Calculate Degradation Text
        if baseline_mean > 0:
            deg_50 = (baseline_mean - st_mean) / baseline_mean * 100
        else:
            deg_50 = 0.0
            
        text = f"Degradation: {deg_50:.1f}%\n"
        if baseline_std > 0:
            sigma_diff = (baseline_mean - st_mean) / baseline_std
            text += f"Significance: {sigma_diff:.1f}σ"
            
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.5, 0.95, text, transform=ax.transAxes, fontsize=12,
                verticalalignment='top', bbox=props, ha='center')

        plt.tight_layout()
        save_path = self.output_dir / filename
        plt.savefig(save_path, dpi=150)
        plt.close(fig)
        return save_path
