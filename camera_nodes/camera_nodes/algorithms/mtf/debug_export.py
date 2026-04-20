"""Debug export helpers for MTF analysis."""

import csv
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

from .config import MTFConfig


def _safe_label(debug_label: Optional[str]) -> str:
    """Convert one logical edge label into a filesystem-safe file stem."""
    text = str(debug_label or "").strip()
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in text).strip("._-")
    return safe or "edge"


def _write_csv(path: Path, header: list[str], rows: np.ndarray) -> None:
    """Write one small numeric CSV with a stable header."""
    np.savetxt(
        path,
        rows,
        delimiter=",",
        header=",".join(header),
        comments="",
    )


def write_curve_csv_artifacts(
    *,
    out_dir: Path,
    debug_label: Optional[str],
    esf: np.ndarray,
    lsf: np.ndarray,
    lsf_windowed: np.ndarray,
    frequencies: np.ndarray,
    mtf_raw: np.ndarray,
    mtf_used: np.ndarray,
    mtf_ideal: np.ndarray,
    esf_raw: Optional[np.ndarray] = None,
    mtf_raw_alt: Optional[np.ndarray] = None,
    mtf_used_alt: Optional[np.ndarray] = None,
    frequencies_alt: Optional[np.ndarray] = None,
    group_curves: Optional[dict[str, dict]] = None,
) -> None:
    """Write the canonical ESF/LSF/MTF CSV files for one logical edge label."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_label(debug_label)

    esf_len = int(esf.size)
    if esf_len > 0:
        columns = [np.arange(esf_len, dtype=int), esf]
        headers = ["sample_index", "esf"]
        if esf_raw is not None and esf_raw.size > 0:
            raw_pad = np.full(esf_len, np.nan)
            raw_pad[: min(esf_len, esf_raw.size)] = esf_raw[: min(esf_len, esf_raw.size)]
            columns.append(raw_pad)
            headers.append("esf_raw")
        _write_csv(
            out_dir / f"{stem}_esf.csv",
            headers,
            np.column_stack(columns),
        )

    lsf_len = int(max(lsf.size, lsf_windowed.size))
    if lsf_len > 0:
        lsf_pad = np.full(lsf_len, np.nan)
        lsf_window_pad = np.full(lsf_len, np.nan)
        lsf_pad[: lsf.size] = lsf
        lsf_window_pad[: lsf_windowed.size] = lsf_windowed
        _write_csv(
            out_dir / f"{stem}_lsf.csv",
            ["sample_index", "lsf", "lsf_windowed"],
            np.column_stack(
                [
                    np.arange(lsf_len, dtype=int),
                    lsf_pad,
                    lsf_window_pad,
                ]
            ),
        )

    if frequencies.size > 0:
        mtf_columns = [
            frequencies,
            mtf_raw[: frequencies.size],
            mtf_used[: frequencies.size],
        ]
        mtf_headers = ["frequency_lpmm", "mtf_raw", "mtf_used"]
        if mtf_ideal.size > 0:
            mtf_columns.append(mtf_ideal[: frequencies.size])
            mtf_headers.append("mtf_ideal")
        if (
            mtf_raw_alt is not None
            and mtf_used_alt is not None
            and frequencies_alt is not None
        ):
            max_len = max(frequencies.size, frequencies_alt.size)

            def _pad(arr: np.ndarray) -> np.ndarray:
                padded = np.full(max_len, np.nan)
                padded[: min(max_len, arr.size)] = arr[: min(max_len, arr.size)]
                return padded

            mtf_columns = [
                _pad(frequencies),
                _pad(mtf_raw),
                _pad(mtf_used),
                _pad(mtf_ideal[: frequencies.size]) if mtf_ideal.size > 0 else np.full(max_len, np.nan),
                _pad(frequencies_alt),
                _pad(mtf_raw_alt),
                _pad(mtf_used_alt),
            ]
            mtf_headers = [
                "frequency_lpmm",
                "mtf_raw",
                "mtf_used",
                "mtf_ideal",
                "frequency_alt_lpmm",
                "mtf_raw_alt",
                "mtf_used_alt",
            ]
        _write_csv(
            out_dir / f"{stem}_mtf.csv",
            mtf_headers,
            np.column_stack(mtf_columns),
        )

    if group_curves:
        max_len = max(
            int(curve["frequencies"].size)
            for curve in group_curves.values()
            if curve.get("frequencies") is not None
        )
        columns = [np.arange(max_len, dtype=int)]
        headers = ["sample_index"]
        for group_name, curve in sorted(group_curves.items()):
            def _pad_group(arr: np.ndarray) -> np.ndarray:
                padded = np.full(max_len, np.nan)
                padded[: min(max_len, arr.size)] = arr[: min(max_len, arr.size)]
                return padded

            columns.extend(
                [
                    _pad_group(curve["frequencies"]),
                    _pad_group(curve["mtf_raw"]),
                    _pad_group(curve["mtf_used"]),
                    _pad_group(curve["esf"]),
                ]
            )
            headers.extend(
                [
                    f"{group_name}_frequency_lpmm",
                    f"{group_name}_mtf_raw",
                    f"{group_name}_mtf_used",
                    f"{group_name}_esf",
                ]
            )
        _write_csv(
            out_dir / f"{stem}_groups.csv",
            headers,
            np.column_stack(columns),
        )


def _overlay_edge_line(
    roi_vis: np.ndarray,
    edge_line: Tuple[float, float, float, float],
) -> None:
    """Draw the fitted edge centerline across the ROI image."""
    x0, y0, vx, vy = edge_line
    height, width = roi_vis.shape[:2]
    eps = 1e-6
    points = []
    if abs(vx) > eps:
        t = (0 - x0) / vx
        y = y0 + t * vy
        if 0 <= y <= height - 1:
            points.append((0, int(round(y))))
        t = ((width - 1) - x0) / vx
        y = y0 + t * vy
        if 0 <= y <= height - 1:
            points.append((width - 1, int(round(y))))
    if abs(vy) > eps:
        t = (0 - y0) / vy
        x = x0 + t * vx
        if 0 <= x <= width - 1:
            points.append((int(round(x)), 0))
        t = ((height - 1) - y0) / vy
        x = x0 + t * vx
        if 0 <= x <= width - 1:
            points.append((int(round(x)), height - 1))

    if len(points) >= 2:
        cv2.line(roi_vis, points[0], points[1], (0, 255, 255), 1, cv2.LINE_AA)
    for point in points:
        cv2.circle(roi_vis, point, 3, (0, 0, 255), -1, cv2.LINE_AA)


def _overlay_analysis_strip(roi_vis: np.ndarray, metadata: dict[str, object]) -> None:
    """Draw the internal analysis strip relative to the manually/automatically chosen ROI."""
    analysis_bounds = metadata.get("analysis_roi_bounds")
    if not analysis_bounds or not isinstance(analysis_bounds, (tuple, list)) or len(analysis_bounds) != 4:
        return
    roi_x = int(metadata.get("roi_bbox_x", 0) or 0)
    roi_y = int(metadata.get("roi_bbox_y", 0) or 0)
    x1 = max(0, int(analysis_bounds[0]) - roi_x)
    y1 = max(0, int(analysis_bounds[1]) - roi_y)
    x2 = max(x1, int(analysis_bounds[2]) - roi_x)
    y2 = max(y1, int(analysis_bounds[3]) - roi_y)
    cv2.rectangle(roi_vis, (x1, y1), (x2, y2), (0, 200, 0), 1, cv2.LINE_AA)


def _overlay_diagnostics(roi_vis: np.ndarray, metadata: dict[str, object]) -> None:
    """Render the most useful angle-diagnosis values directly into the ROI export."""
    lines = [
        f"method: {metadata.get('edge_angle_method', '-')}",
        f"angle: {float(metadata.get('edge_angle_deg', 0.0) or 0.0):.2f} deg",
        f"geometric: {float(metadata.get('edge_angle_geometric', 0.0) or 0.0):.2f} deg",
        f"phase: {float(metadata.get('edge_angle_phase', 0.0) or 0.0):.2f} deg",
        f"consistency: {float(metadata.get('edge_angle_consistency_deg', 0.0) or 0.0):.2f} deg",
        f"support: {int(metadata.get('edge_support_points', 0) or 0)}",
    ]
    for index, line in enumerate(lines):
        y = 18 + index * 16
        cv2.putText(
            roi_vis,
            line,
            (8, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            roi_vis,
            line,
            (8, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (20, 20, 20),
            1,
            cv2.LINE_AA,
        )


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
    metadata: Optional[dict[str, object]] = None,
    group_curves: Optional[dict[str, dict]] = None,
) -> None:
    """Export one clean per-edge artifact set for CSV and PNG review."""
    try:
        out_dir = Path(config.debug_export_dir or "")
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = _safe_label(debug_label)
        metadata = dict(metadata or {})
        if edge_validation_ok is not None:
            metadata["edge_validation_ok"] = int(bool(edge_validation_ok))
        if edge_hits is not None:
            metadata["edge_hits"] = edge_hits

        if config.debug_export_csv:
            write_curve_csv_artifacts(
                out_dir=out_dir,
                debug_label=debug_label,
                esf=esf,
                lsf=lsf,
                lsf_windowed=lsf_windowed,
                frequencies=frequencies,
                mtf_raw=mtf_raw,
                mtf_used=mtf_used,
                mtf_ideal=mtf_ideal,
                esf_raw=esf_raw,
                mtf_raw_alt=mtf_raw_alt,
                mtf_used_alt=mtf_used_alt,
                frequencies_alt=frequencies_alt,
                group_curves=group_curves,
            )

            if metadata:
                with open(
                    out_dir / f"{stem}_metadata.csv",
                    "w",
                    newline="",
                    encoding="utf-8",
                ) as handle:
                    writer = csv.writer(handle)
                    writer.writerow(["key", "value"])
                    for key, value in metadata.items():
                        writer.writerow([key, value])

        if config.debug_export_png:
            try:
                import matplotlib.pyplot as plt

                figure, axes = plt.subplots(3, 1, figsize=(8, 8), constrained_layout=True)
                axes[0].plot(esf, color="tab:blue")
                axes[0].set_title("ESF")
                axes[0].set_ylabel("Intensity")

                axes[1].plot(lsf, color="tab:orange", label="LSF")
                axes[1].plot(
                    lsf_windowed,
                    color="tab:green",
                    alpha=0.7,
                    label="LSF windowed",
                )
                axes[1].set_title("LSF")
                axes[1].set_ylabel("dI/dx")
                axes[1].legend(loc="best", fontsize=8)

                axes[2].plot(frequencies, mtf_raw[: frequencies.size], label="MTF raw")
                if mtf_used is not mtf_raw:
                    axes[2].plot(frequencies, mtf_used[: frequencies.size], label="MTF used")
                if mtf_ideal.size > 0:
                    axes[2].plot(
                        frequencies,
                        mtf_ideal[: frequencies.size],
                        "--",
                        label="MTF ideal",
                    )
                axes[2].set_title("MTF")
                axes[2].set_xlabel("Frequency (lp/mm)")
                axes[2].set_ylabel("MTF")
                axes[2].set_ylim(
                    0,
                    max(1.1, float(np.nanmax(mtf_raw)) if mtf_raw.size > 0 else 1.1),
                )
                axes[2].legend(loc="best", fontsize=8)

                figure.savefig(out_dir / f"{stem}_plot.png", dpi=150)
                plt.close(figure)
            except Exception:
                pass

            try:
                if roi_img is not None:
                    roi_vis = (
                        cv2.cvtColor(roi_img, cv2.COLOR_GRAY2BGR)
                        if len(roi_img.shape) == 2
                        else roi_img.copy()
                    )
                    if edge_line is not None:
                        _overlay_edge_line(roi_vis, edge_line)
                    if metadata:
                        _overlay_analysis_strip(roi_vis, metadata)
                        _overlay_diagnostics(roi_vis, metadata)
                    cv2.imwrite(str(out_dir / f"{stem}_roi.png"), roi_vis)
            except Exception:
                pass
    except Exception:
        return
