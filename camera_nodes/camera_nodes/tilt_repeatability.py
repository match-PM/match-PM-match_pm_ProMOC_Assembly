"""Aggregate multiple evaluation directories into repeatability statistics."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import statistics

import numpy as np


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="directory containing run_*/summary.json")
    parser.add_argument("--output", default="repeatability")
    parser.add_argument("--reference-output", default="", help="write the mean fitted surface as a guarded reference JSON")
    args=parser.parse_args(argv); root=Path(args.input); output=Path(args.output); output.mkdir(parents=True,exist_ok=True)
    summaries=[]
    for path in sorted(root.glob("run_*/summary.json")):
        data=json.loads(path.read_text(encoding="utf-8")); data["run_directory"]=str(path.parent); summaries.append(data)
    if not summaries: raise SystemExit(f"no run_*/summary.json below {root}")
    names=("tilt_x_deg","tilt_y_deg","center_focus_z_mm","surface_rms_um","roi_valid","selected_roi_count","surface_inlier_count")
    with (output/"runs_summary.csv").open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=("run_directory",)+names); writer.writeheader()
        for data in summaries: writer.writerow({name:data.get(name) for name in ("run_directory",)+names})
    stats={"run_count":len(summaries)}
    for name in names:
        values=[float(d[name]) for d in summaries if d.get(name) is not None]
        stats[name]={"mean":statistics.fmean(values),"std":statistics.stdev(values) if len(values)>1 else 0.,"min":min(values),"max":max(values)} if values else None
    (output/"repeatability.json").write_text(json.dumps(stats,indent=2,sort_keys=True),encoding="utf-8")
    per_roi={}
    for data in summaries:
        path=Path(data["run_directory"])/"roi_data.csv"
        if not path.exists(): continue
        with path.open(encoding="utf-8",newline="") as handle:
            for row in csv.DictReader(handle):
                index=int(row["index"]); item=per_roi.setdefault(index,{"focus_z_mm":[],"surface_residual_um":[]})
                for name in item:
                    try:
                        value=float(row[name])
                        if np.isfinite(value): item[name].append(value)
                    except (KeyError,ValueError): pass
    roi_rows=[]
    for index,item in sorted(per_roi.items()):
        row={"roi_index":index}
        for name,values in item.items():
            row[f"{name}_mean"]=statistics.fmean(values) if values else None
            row[f"{name}_std"]=statistics.stdev(values) if len(values)>1 else 0. if values else None
        roi_rows.append(row)
    fields=("roi_index","focus_z_mm_mean","focus_z_mm_std","surface_residual_um_mean","surface_residual_um_std")
    with (output/"roi_repeatability.csv").open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields); writer.writeheader(); writer.writerows(roi_rows)
    _write_heatmaps(output,roi_rows)
    if args.reference_output:
        _write_reference(Path(args.reference_output),summaries)
    print(output)


def _write_heatmaps(output,rows):
    if not rows: return
    count=max(row["roi_index"] for row in rows)+1; side=int(round(np.sqrt(count)))
    if side*side!=count: return
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError: return
    for name,title in (("focus_z_mm_std","Peak-Z repeatability [mm]"),("surface_residual_um_std","Residual repeatability [um]")):
        data=np.full(count,np.nan)
        for row in rows: data[row["roi_index"]]=row[name]
        fig,ax=plt.subplots(figsize=(6,5)); image=ax.imshow(data.reshape(side,side),cmap="viridis"); fig.colorbar(image,ax=ax); ax.set_title(title)
        fig.tight_layout(); fig.savefig(output/f"{name}_heatmap.png",dpi=160); plt.close(fig)


def _write_reference(path,summaries):
    usable=[data for data in summaries if data.get("surface_coefficients") and not data.get("reference_applied")]
    if not usable: raise SystemExit("no uncorrected valid surface coefficients available for reference")
    model=usable[0]["surface_model"]; metadata=usable[0].get("metadata",{}); shape=metadata.get("image_shape"); scale=metadata.get("object_um_per_pixel")
    if not shape or scale is None: raise SystemExit("evaluation metadata lacks image shape or object scale")
    for data in usable:
        candidate=data.get("metadata",{})
        if data["surface_model"]!=model or candidate.get("image_shape")!=shape or candidate.get("object_um_per_pixel")!=scale:
            raise SystemExit("runs use incompatible surface models or imaging profiles")
    coefficients=np.mean(np.asarray([data["surface_coefficients"] for data in usable],dtype=float),axis=0)
    payload={"schema_version":1,"model":model,"coefficients":coefficients.tolist(),"object_um_per_pixel":scale,"image_shape":shape,"metadata":{"source_run_count":len(usable),"purpose":"camera-fixed focus reference"}}
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")
