"""Optional, lazy-loaded diagnostic export for tilt-estimation runs."""
from __future__ import annotations

from dataclasses import asdict
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path

import numpy as np


def export_evaluation(output_root, estimate, *, metric_results=None, roi_rows=0,
                      roi_cols=0, metadata=None) -> str:
    """Write machine-readable diagnostics and plots; return the run directory."""
    stamp = datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%S_%fZ")
    run_dir = Path(output_root).expanduser() / stamp
    run_dir.mkdir(parents=True, exist_ok=False)
    summary = _json_safe(asdict(estimate))
    summary.pop("roi_fits", None)
    summary["status"] = int(estimate.status)
    summary["status_name"] = estimate.status.name
    summary["created_utc"] = datetime.now(timezone.utc).isoformat()
    summary["metadata"] = metadata or {}
    summary["metric_comparison"] = {
        name: _compact_result(value) for name, value in (metric_results or {}).items()
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")

    fields = [name for name in asdict(estimate.roi_fits[0]).keys()
              if name not in {"curve_z_mm", "curve_values", "local_fit_z_mm", "local_fit_values"}] if estimate.roi_fits else []
    with (run_dir / "roi_data.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if fields: writer.writeheader()
        for fit in estimate.roi_fits:
            row = asdict(fit)
            writer.writerow({name: row[name] for name in fields})
    with (run_dir / "focus_curves.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle); writer.writerow(["roi_index", "z_mm", "focus_value"])
        for fit in estimate.roi_fits:
            writer.writerows((fit.index, z, value) for z, value in zip(fit.curve_z_mm, fit.curve_values))

    try:
        _write_plots(run_dir, estimate, roi_rows, roi_cols)
    except ImportError as exc:
        summary["plot_warning"] = f"plots omitted: {exc}"
        (run_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    return str(run_dir)


def _write_plots(run_dir, estimate, rows, cols):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    curve_dir = run_dir / "focus_curves"
    curve_dir.mkdir()
    for fit in estimate.roi_fits:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(fit.curve_z_mm, fit.curve_values, "o-", label="measured")
        if fit.local_fit_z_mm:
            ax.plot(fit.local_fit_z_mm, fit.local_fit_values, "-", label=fit.peak_fit_method)
        if math.isfinite(fit.focus_z_mm): ax.axvline(fit.focus_z_mm, color="C3", linestyle="--")
        ax.set(xlabel="Z [mm]", ylabel="focus score", title=f"ROI {fit.index}: {fit.reason}")
        ax.legend(); fig.tight_layout(); fig.savefig(curve_dir / f"roi_{fit.index:03d}.png", dpi=140); plt.close(fig)
    if rows*cols != len(estimate.roi_fits): return
    for attribute, filename, title in (("focus_z_mm", "z_peak_heatmap.png", "Peak Z [mm]"),
                                       ("surface_residual_um", "residual_heatmap.png", "Surface residual [um]")):
        data=np.asarray([getattr(f,attribute) for f in estimate.roi_fits]).reshape(rows,cols)
        fig,ax=plt.subplots(figsize=(7,5)); image=ax.imshow(data,cmap="coolwarm"); fig.colorbar(image,ax=ax); ax.set_title(title)
        fig.tight_layout(); fig.savefig(run_dir/filename,dpi=160); plt.close(fig)
    valid=[f for f in estimate.roi_fits if f.valid and math.isfinite(f.surface_z_mm)]
    if valid:
        fig=plt.figure(figsize=(8,6)); ax=fig.add_subplot(111,projection="3d")
        ax.scatter([f.x_mm for f in valid],[f.y_mm for f in valid],[f.focus_z_mm for f in valid],label="ROI peaks")
        ax.scatter([f.x_mm for f in valid],[f.y_mm for f in valid],[f.surface_z_mm for f in valid],label="surface")
        ax.set(xlabel="object x [mm]",ylabel="object y [mm]",zlabel="Z [mm]"); ax.legend(); fig.tight_layout()
        fig.savefig(run_dir/"surface_3d.png",dpi=160); plt.close(fig)


def _compact_result(value):
    names=("status","status_message","tilt_x_deg","tilt_y_deg","uncertainty_x_deg",
           "uncertainty_y_deg","center_focus_z_mm","surface_rms_um","roi_valid",
           "decision_x","decision_y")
    return _json_safe({name: int(value.status) if name=="status" else getattr(value,name) for name in names})


def _json_safe(value):
    if isinstance(value, dict): return {str(k):_json_safe(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)): return [_json_safe(v) for v in value]
    if isinstance(value, (float,np.floating)) and not math.isfinite(float(value)): return None
    if isinstance(value, np.integer): return int(value)
    return value
