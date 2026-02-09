"""Debug export helpers for MTF analysis."""

import csv
import re
import time
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

from .config import MTFConfig


def export_debug(
    config: MTFConfig,
    esf: np.ndarray,
    lsf: np.ndarray,
    lsf_windowed: np.ndarray,
    frequencies: np.ndarray,
    mtf_raw: np.ndarray,
    mtf_used: np.ndarray,
    mtf_ideal: np.ndarray,
    debug_label: Optional[str],
    esf_raw: Optional[np.ndarray] = None,
    roi_img: Optional[np.ndarray] = None,
    edge_line: Optional[Tuple[float, float, float, float]] = None,
    mtf_raw_alt: Optional[np.ndarray] = None,
    mtf_used_alt: Optional[np.ndarray] = None,
    frequencies_alt: Optional[np.ndarray] = None,
    edge_hits: Optional[str] = None,
    edge_validation_ok: Optional[bool] = None,
) -> None:
    """Export ESF/LSF/MTF debug data to CSV/PNG (best-effort)."""
    try:
        out_dir = Path(config.debug_export_dir or "")
        out_dir.mkdir(parents=True, exist_ok=True)

        label = debug_label or "edge"
        safe_label = re.sub(r'[^A-Za-z0-9._-]+', '_', label).strip('_') or "edge"
        stem = f"{config.debug_export_prefix}_{safe_label}_{time.time_ns()}"

        if config.debug_export_csv:
            max_len = max(esf.size, lsf.size, lsf_windowed.size)
            esf_pad = np.full(max_len, np.nan)
            lsf_pad = np.full(max_len, np.nan)
            lsfw_pad = np.full(max_len, np.nan)
            esf_pad[:esf.size] = esf
            lsf_pad[:lsf.size] = lsf
            lsfw_pad[:lsf_windowed.size] = lsf_windowed

            if esf_raw is not None and esf_raw.size > 0:
                esf_raw_pad = np.full(max_len, np.nan)
                esf_raw_pad[:esf_raw.size] = esf_raw
                if max_len > esf_pad.size:
                    esf_pad = np.pad(esf_pad, (0, max_len - esf_pad.size), constant_values=np.nan)
                    lsf_pad = np.pad(lsf_pad, (0, max_len - lsf_pad.size), constant_values=np.nan)
                    lsfw_pad = np.pad(lsfw_pad, (0, max_len - lsfw_pad.size), constant_values=np.nan)
                cols = [
                    np.arange(max_len),
                    esf_raw_pad,
                    esf_pad,
                    lsf_pad,
                    lsfw_pad,
                ]
                headers = ["index", "esf_raw", "esf_used", "lsf", "lsf_windowed"]
            else:
                cols = [
                    np.arange(max_len),
                    esf_pad,
                    lsf_pad,
                    lsfw_pad,
                ]
                headers = ["index", "esf", "lsf", "lsf_windowed"]

            if edge_line is not None:
                x0, y0, vx, vy = edge_line
                cols.extend([
                    np.full(max_len, x0),
                    np.full(max_len, y0),
                    np.full(max_len, vx),
                    np.full(max_len, vy),
                ])
                headers.extend(["edge_x0", "edge_y0", "edge_vx", "edge_vy"])

            data_esf = np.column_stack(cols)
            headers_out = headers[:]
            edge_ok_val = "" if edge_validation_ok is None else str(int(edge_validation_ok))
            edge_hits_val = edge_hits if edge_hits is not None else ""
            if edge_validation_ok is not None:
                headers_out.append("edge_validation_ok")
            if edge_hits is not None:
                headers_out.append("edge_hits")

            with open(out_dir / f"{stem}_esf_lsf.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers_out)
                for i in range(data_esf.shape[0]):
                    row = list(data_esf[i, :])
                    if edge_validation_ok is not None:
                        row.append(edge_ok_val)
                    if edge_hits is not None:
                        row.append(edge_hits_val)
                    writer.writerow(row)

            # MTF CSV
            freq = frequencies
            mtf_ideal_pad = mtf_ideal[:freq.size] if mtf_ideal.size > 0 else np.full(freq.size, np.nan)
            cols = [freq, mtf_raw[:freq.size], mtf_used[:freq.size], mtf_ideal_pad]
            headers = ["frequency_lpmm", "mtf_raw", "mtf_used", "mtf_ideal"]

            if mtf_raw_alt is not None and mtf_used_alt is not None and frequencies_alt is not None:
                freq_alt = frequencies_alt
                max_len = max(freq.size, freq_alt.size)

                def _pad(arr, n):
                    out = np.full(n, np.nan)
                    out[:min(n, arr.size)] = arr[:min(n, arr.size)]
                    return out

                cols = [
                    _pad(freq, max_len),
                    _pad(mtf_raw, max_len),
                    _pad(mtf_used, max_len),
                    _pad(mtf_ideal_pad, max_len),
                    _pad(freq_alt, max_len),
                    _pad(mtf_raw_alt, max_len),
                    _pad(mtf_used_alt, max_len),
                ]
                headers = [
                    "frequency_lpmm",
                    "mtf_raw",
                    "mtf_used",
                    "mtf_ideal",
                    "frequency_alt_lpmm",
                    "mtf_raw_alt",
                    "mtf_used_alt",
                ]

            data_mtf = np.column_stack(cols)
            np.savetxt(
                out_dir / f"{stem}_mtf.csv",
                data_mtf,
                delimiter=",",
                header=",".join(headers),
                comments=""
            )

        if config.debug_export_png:
            try:
                import matplotlib.pyplot as plt
                fig, axes = plt.subplots(3, 1, figsize=(8, 8), constrained_layout=True)
                axes[0].plot(esf, color='tab:blue')
                axes[0].set_title("ESF")
                axes[0].set_ylabel("Intensity")

                axes[1].plot(lsf, color='tab:orange', label='LSF')
                axes[1].plot(lsf_windowed, color='tab:green', alpha=0.7, label='LSF windowed')
                axes[1].set_title("LSF")
                axes[1].set_ylabel("dI/dx")
                axes[1].legend(loc="best", fontsize=8)

                axes[2].plot(frequencies, mtf_raw[:frequencies.size], label='MTF raw')
                if mtf_used is not mtf_raw:
                    axes[2].plot(frequencies, mtf_used[:frequencies.size], label='MTF used')
                if mtf_ideal.size > 0:
                    axes[2].plot(frequencies, mtf_ideal[:frequencies.size], '--', label='MTF ideal')
                if mtf_raw_alt is not None and mtf_used_alt is not None and frequencies_alt is not None:
                    axes[2].plot(
                        frequencies_alt, mtf_raw_alt[:frequencies_alt.size],
                        linestyle=':', color='tab:purple', label='MTF raw (unsmoothed)'
                    )
                    axes[2].plot(
                        frequencies_alt, mtf_used_alt[:frequencies_alt.size],
                        linestyle='--', color='tab:brown', label='MTF used (unsmoothed)'
                    )
                axes[2].set_title("MTF")
                axes[2].set_xlabel("Frequency (lp/mm)")
                axes[2].set_ylabel("MTF")
                axes[2].set_ylim(0, max(1.1, float(np.nanmax(mtf_raw)) if mtf_raw.size > 0 else 1.1))
                axes[2].legend(loc="best", fontsize=8)

                fig.savefig(out_dir / f"{stem}_debug.png", dpi=150)
                plt.close(fig)
            except Exception:
                pass

            # ROI overlay with fitted edge line
            try:
                if roi_img is not None and edge_line is not None:
                    if len(roi_img.shape) == 2:
                        roi_vis = cv2.cvtColor(roi_img, cv2.COLOR_GRAY2BGR)
                    else:
                        roi_vis = roi_img.copy()

                    x0, y0, vx, vy = edge_line
                    h, w = roi_vis.shape[:2]
                    eps = 1e-6
                    pts = []
                    if abs(vx) > eps:
                        t = (0 - x0) / vx
                        y = y0 + t * vy
                        if 0 <= y <= h - 1:
                            pts.append((0, int(round(y))))
                        t = ((w - 1) - x0) / vx
                        y = y0 + t * vy
                        if 0 <= y <= h - 1:
                            pts.append((w - 1, int(round(y))))
                    if abs(vy) > eps:
                        t = (0 - y0) / vy
                        x = x0 + t * vx
                        if 0 <= x <= w - 1:
                            pts.append((int(round(x)), 0))
                        t = ((h - 1) - y0) / vy
                        x = x0 + t * vx
                        if 0 <= x <= w - 1:
                            pts.append((int(round(x)), h - 1))

                    if len(pts) >= 2:
                        p1, p2 = pts[0], pts[1]
                        cv2.line(roi_vis, p1, p2, (0, 255, 255), 1, cv2.LINE_AA)
                    for p in pts:
                        cv2.circle(roi_vis, p, 3, (0, 0, 255), -1, cv2.LINE_AA)

                    cv2.imwrite(str(out_dir / f"{stem}_roi_edge.png"), roi_vis)
            except Exception:
                pass
    except Exception:
        return
