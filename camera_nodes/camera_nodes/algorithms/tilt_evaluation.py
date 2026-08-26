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
                      roi_cols=0, metadata=None,
                      export_all_focus_curves=False) -> str:
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
        _write_plots(run_dir, estimate, export_all_focus_curves)
    except ImportError as exc:
        summary["plot_warning"] = f"plots omitted: {exc}"
        (run_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    return str(run_dir)


def _write_plots(run_dir, estimate, export_all_focus_curves=False):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _write_selection_overlay(run_dir, estimate, plt)
    _write_spatial_metric(
        run_dir, estimate, plt, "focus_z_mm", "z_peak_heatmap.png", "Peak Z [mm]",
        lambda fit: fit.valid,
    )
    _write_spatial_metric(
        run_dir, estimate, plt, "surface_residual_um", "residual_heatmap.png",
        "Surface residual [um]", lambda fit: fit.selected,
    )

    curve_dir = run_dir / "focus_curves"
    curve_dir.mkdir()
    for fit in _focus_curve_fits(estimate.roi_fits, export_all_focus_curves):
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(fit.curve_z_mm, fit.curve_values, "o-", label="measured")
        if fit.local_fit_z_mm:
            ax.plot(fit.local_fit_z_mm, fit.local_fit_values, "-", label=fit.peak_fit_method)
        if math.isfinite(fit.focus_z_mm): ax.axvline(fit.focus_z_mm, color="C3", linestyle="--")
        ax.set(xlabel="Z [mm]", ylabel="focus score", title=f"ROI {fit.index}: {fit.reason}")
        ax.legend(); fig.tight_layout(); fig.savefig(curve_dir / f"roi_{fit.index:03d}.png", dpi=140); plt.close(fig)
    valid=[f for f in estimate.roi_fits if f.selected and math.isfinite(f.surface_z_mm)]
    fig=plt.figure(figsize=(8,6)); ax=fig.add_subplot(111,projection="3d")
    if valid:
        ax.scatter([f.x_mm for f in valid],[f.y_mm for f in valid],[f.focus_z_mm for f in valid],label="ROI peaks")
        ax.scatter([f.x_mm for f in valid],[f.y_mm for f in valid],[f.surface_z_mm for f in valid],label="surface")
        ax.set(xlabel="object x [mm]",ylabel="object y [mm]",zlabel="Z [mm]"); ax.legend(); fig.tight_layout()
    else:
        ax.text2D(.5,.5,"No fitted surface available",transform=ax.transAxes,ha="center")
    fig.savefig(run_dir/"surface_3d.png",dpi=160); plt.close(fig)


def _focus_curve_fits(fits, export_all):
    if export_all:
        return list(fits)
    chosen={fit.index:fit for fit in fits if fit.selected}
    # Keep one deterministic diagnostic example for each actual rejection cause.
    for fit in sorted(fits,key=lambda item:item.index):
        if fit.selected or fit.reason in {"ok","spatially_redundant"}:
            continue
        if not any(item.reason==fit.reason for item in chosen.values()):
            chosen[fit.index]=fit
    return [chosen[index] for index in sorted(chosen)]


def _write_spatial_metric(run_dir, estimate, plt, attribute, filename, title,
                          predicate):
    values=[fit for fit in estimate.roi_fits if predicate(fit) and math.isfinite(getattr(fit,attribute))]
    fig,ax=plt.subplots(figsize=(9,6))
    if values:
        marker_size=max(12.0,9000.0/max(len(estimate.roi_fits),1))
        image=ax.scatter(
            [fit.x_px for fit in values],[fit.y_px for fit in values],
            c=[getattr(fit,attribute) for fit in values],s=marker_size,
            marker="s",cmap="coolwarm",
        )
        fig.colorbar(image,ax=ax,label=title)
        width=max(1,max(fit.x1_px for fit in estimate.roi_fits))
        height=max(1,max(fit.y1_px for fit in estimate.roi_fits))
        ax.set(xlim=(0,width),ylim=(height,0))
    else:
        ax.text(.5,.5,"No finite values available",transform=ax.transAxes,ha="center")
    ax.set(xlabel="image x [px]",ylabel="image y [px]",title=title)
    ax.set_aspect("equal",adjustable="box"); fig.tight_layout()
    fig.savefig(run_dir/filename,dpi=160); plt.close(fig)


def _write_selection_overlay(run_dir, estimate, plt):
    """Render candidate state without retaining or exporting camera images."""
    if not estimate.roi_fits:
        return
    width=max(1,max(fit.x1_px for fit in estimate.roi_fits))
    height=max(1,max(fit.y1_px for fit in estimate.roi_fits))
    fig,ax=plt.subplots(figsize=(10,7))
    colors={"rejected":"#d62728","focus_valid":"#1f77b4","selected":"#ff8c00","inlier":"#2ca02c"}
    for fit in estimate.roi_fits:
        state="inlier" if fit.surface_inlier else "selected" if fit.selected else "focus_valid" if fit.valid else "rejected"
        rectangle=plt.Rectangle((fit.x0_px,fit.y0_px),fit.x1_px-fit.x0_px,fit.y1_px-fit.y0_px,fill=False,linewidth=1.4 if fit.selected else .5,color=colors[state],alpha=.9)
        ax.add_patch(rectangle)
        if fit.selected:
            residual=f"{fit.surface_residual_um:.1f}" if math.isfinite(fit.surface_residual_um) else "-"
            ax.text(fit.x_px,fit.y_px,f"{fit.index}\n{residual} um",fontsize=6,ha="center",va="center")
    bbox=estimate.target_bbox_normalized
    if len(bbox)==4 and all(value is not None and math.isfinite(value) for value in bbox):
        x0,y0,x1,y1=bbox
        ax.add_patch(plt.Rectangle((x0*width,y0*height),(x1-x0)*width,(y1-y0)*height,fill=False,color="#00a6d6",linewidth=2.5,label="target support"))
    handles=[plt.Line2D([0],[0],color=color,label=state.replace("_"," ")) for state,color in colors.items()]
    ax.legend(handles=handles,loc="upper right",fontsize=8)
    ax.set(xlim=(0,width),ylim=(height,0),xlabel="image x [px]",ylabel="image y [px]",title="Adaptive ROI selection")
    ax.set_aspect("equal"); fig.tight_layout(); fig.savefig(run_dir/"roi_selection.png",dpi=160); plt.close(fig)


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
