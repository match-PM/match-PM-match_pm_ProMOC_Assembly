"""Plotting utilities for verification reports."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

import numpy as np

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover - optional dependency
    plt = None


class VerificationPlotter:
    """Lightweight plotting helper for verification callbacks."""

    def __init__(self, logger=None):
        self._logger = logger

    def _warn(self, msg: str) -> None:
        if self._logger:
            self._logger.warn(msg)

    @staticmethod
    def _safe_float(value) -> float | None:
        try:
            if value is None:
                return None
            if isinstance(value, str) and value.strip().lower() in {'n/a', 'nan', ''}:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def plot_autofocus_verification(self, results: Iterable[dict], filename: str) -> bool:
        if plt is None:
            self._warn('matplotlib not available - skipping autofocus plot')
            return False

        deviations = defaultdict(list)
        durations = defaultdict(list)
        measurements = defaultdict(list)
        scores = defaultdict(list)

        for row in results:
            alg = row.get('algorithm', 'unknown')
            dev = self._safe_float(row.get('deviation_from_ref_mm'))
            dur = self._safe_float(row.get('duration_s'))
            meas = self._safe_float(row.get('measurements'))
            score = self._safe_float(row.get('focus_score'))
            is_exhaustive = 'exhaustive' in str(alg).lower()

            if dev is not None:
                deviations[alg].append(dev)
            if dur is not None and not is_exhaustive:
                durations[alg].append(dur)
            if meas is not None and not is_exhaustive:
                measurements[alg].append(meas)
            if score is not None:
                scores[alg].append(score)

        if not deviations and not durations and not measurements and not scores:
            self._warn('No valid data for autofocus plot')
            return False

        algs = sorted({*deviations.keys(), *durations.keys(), *measurements.keys(), *scores.keys()})
        if not algs:
            self._warn('No algorithms found for autofocus plot')
            return False

        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle('Autofocus Verification Summary')

        # Deviations
        dev_algs = sorted(deviations.keys())
        if dev_algs:
            dev_data = [deviations.get(a, []) for a in dev_algs]
            axes[0, 0].boxplot(dev_data, labels=dev_algs, showfliers=False)
            axes[0, 0].set_title('Deviation from Reference (mm)')
            axes[0, 0].set_ylabel('Deviation (mm)')
            axes[0, 0].tick_params(axis='x', rotation=30)
        else:
            axes[0, 0].set_title('Deviation from Reference (mm)')
            axes[0, 0].text(0.5, 0.5, 'No data', ha='center', va='center')
            axes[0, 0].set_axis_off()

        # Durations (exclude exhaustive)
        dur_algs = sorted(durations.keys())
        if dur_algs:
            dur_means = [np.mean(durations[a]) if durations.get(a) else 0.0 for a in dur_algs]
            axes[0, 1].bar(dur_algs, dur_means)
            axes[0, 1].set_title('Execution Time (s)')
            axes[0, 1].set_ylabel('Seconds')
            axes[0, 1].tick_params(axis='x', rotation=30)
        else:
            axes[0, 1].set_title('Execution Time (s)')
            axes[0, 1].text(0.5, 0.5, 'No data', ha='center', va='center')
            axes[0, 1].set_axis_off()

        # Measurements (exclude exhaustive)
        meas_algs = sorted(measurements.keys())
        if meas_algs:
            meas_means = [np.mean(measurements[a]) if measurements.get(a) else 0.0 for a in meas_algs]
            axes[1, 0].bar(meas_algs, meas_means)
            axes[1, 0].set_title('Measurements Count')
            axes[1, 0].set_ylabel('Count')
            axes[1, 0].tick_params(axis='x', rotation=30)
        else:
            axes[1, 0].set_title('Measurements Count')
            axes[1, 0].text(0.5, 0.5, 'No data', ha='center', va='center')
            axes[1, 0].set_axis_off()

        # Focus Scores
        score_algs = sorted(scores.keys())
        if score_algs:
            for idx, alg in enumerate(score_algs):
                data = scores.get(alg, [])
                if not data:
                    continue
                x = np.full(len(data), idx + 1)
                axes[1, 1].scatter(x, data, alpha=0.7)
            axes[1, 1].set_xticks(range(1, len(score_algs) + 1))
            axes[1, 1].set_xticklabels(score_algs, rotation=30)
            axes[1, 1].set_title('Focus Scores')
            axes[1, 1].set_ylabel('Score')
        else:
            axes[1, 1].set_title('Focus Scores')
            axes[1, 1].text(0.5, 0.5, 'No data', ha='center', va='center')
            axes[1, 1].set_axis_off()

        fig.tight_layout(rect=[0, 0.03, 1, 0.95])
        fig.savefig(filename, dpi=150)
        plt.close(fig)
        return True

    def plot_mtf_verification(self, results: Iterable[dict], filename: str, curves: Iterable[dict] | None = None) -> bool:
        if plt is None:
            self._warn('matplotlib not available - skipping MTF plot')
            return False

        if curves:
            fig, ax = plt.subplots(1, 1, figsize=(10, 6))
            max_nyquist = None
            plotted_ideal = False
            for curve in curves:
                freqs = np.asarray(curve.get('frequencies', []), dtype=float)
                mtf_vals = np.asarray(curve.get('mtf_values', []), dtype=float)
                if freqs.size == 0 or mtf_vals.size == 0:
                    continue
                label = curve.get('label', 'mtf')

                # Sort by frequency
                sort_idx = np.argsort(freqs)
                freqs = freqs[sort_idx]
                mtf_vals = mtf_vals[sort_idx]

                # Clip to valid range
                mtf_vals = np.clip(mtf_vals, 0.0, 1.0)

                ax.plot(freqs, mtf_vals * 100.0, label=label)

                # Plot Ideal Curve (only once)
                ideals = curve.get('mtf_ideal')
                if ideals is not None and not plotted_ideal:
                    if len(ideals) == len(freqs):
                         # Sort using same index
                         ideals = np.asarray(ideals, dtype=float)[sort_idx]
                         ax.plot(freqs, ideals * 100.0, 'k--', linewidth=1.5, alpha=0.7, label='Diffraction Limit (F/2.8)')
                         plotted_ideal = True

                nyq = curve.get('nyquist_lpmm')
                if nyq:
                    max_nyquist = nyq if max_nyquist is None else min(max_nyquist, nyq)

            ax.set_title('MTF Curve')
            ax.set_xlabel('Frequency (lp/mm)')
            ax.set_ylabel('MTF (%)')
            ax.set_ylim(0, 100)
            if max_nyquist:
                # Clip to Nyquist for cleaner graph (hide high freq noise)
                ax.set_xlim(0, max_nyquist * 1.05)
            ax.grid(True, alpha=0.3)
            if len(list(curves)) <= 8:
                ax.legend(fontsize=8)
            fig.tight_layout()
            fig.savefig(filename, dpi=150)
            plt.close(fig)
            return True

        grouped = defaultdict(list)
        for row in results:
            if str(row.get('valid', '')).lower() != 'true':
                continue
            pos = row.get('position', 'unknown')
            edge = row.get('edge', 'edge')
            key = f'{pos}-{edge}'
            mtf50 = self._safe_float(row.get('mtf50_lpmm'))
            if mtf50 is not None:
                grouped[key].append(mtf50)

        if not grouped:
            self._warn('No valid MTF data for plot')
            return False

        labels = list(grouped.keys())
        means = [float(np.mean(grouped[k])) for k in labels]
        stds = [float(np.std(grouped[k])) if len(grouped[k]) > 1 else 0.0 for k in labels]

        fig, ax = plt.subplots(1, 1, figsize=(12, 5))
        ax.bar(labels, means, yerr=stds, capsize=4)
        ax.set_title('MTF50 Comparison')
        ax.set_ylabel('MTF50 (lp/mm)')
        ax.tick_params(axis='x', rotation=45)
        fig.tight_layout()
        fig.savefig(filename, dpi=150)
        plt.close(fig)
        return True

    def plot_autofocus_curves(self, curves: Iterable[dict], filename: str, normalize: bool = True) -> bool:
        if plt is None:
            self._warn('matplotlib not available - skipping autofocus curve plot')
            return False

        curves_list = list(curves)
        if not curves_list:
            self._warn('No curve data for autofocus plot')
            return False

        fig, ax = plt.subplots(1, 1, figsize=(10, 6))

        for curve in curves_list:
            positions = np.asarray(curve.get('positions', []), dtype=float)
            scores = np.asarray(curve.get('scores', []), dtype=float)
            if positions.size == 0 or scores.size == 0:
                continue

            sort_idx = np.argsort(positions)
            positions = positions[sort_idx]
            scores = scores[sort_idx]

            if normalize and scores.size:
                max_score = float(np.max(scores))
                if max_score > 0:
                    scores = scores / max_score

            label = curve.get('label', 'algorithm')
            ax.plot(positions, scores, marker='o', markersize=2, linewidth=1.2, label=label)

        ax.set_title('Autofocus Score Curves (Normalized)' if normalize else 'Autofocus Score Curves')
        ax.set_xlabel('Position (mm)')
        ax.set_ylabel('Normalized Score' if normalize else 'Score')
        ax.grid(True, alpha=0.3)
        if len(curves_list) <= 8:
            ax.legend(fontsize=8)

        fig.tight_layout()
        fig.savefig(filename, dpi=150)
        plt.close(fig)
        return True
