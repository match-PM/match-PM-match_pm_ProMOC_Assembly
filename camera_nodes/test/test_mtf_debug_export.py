"""Focused tests for clean per-edge MTF debug exports."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
CAMERA_NODES_ROOT = ROOT / "camera_nodes"
if str(CAMERA_NODES_ROOT) not in sys.path:
    sys.path.insert(0, str(CAMERA_NODES_ROOT))

from camera_nodes.algorithms.mtf.config import MTFConfig  # noqa: E402
from camera_nodes.algorithms.mtf import debug_export as debug_export_module  # noqa: E402
from camera_nodes.algorithms.mtf.debug_export import export_debug  # noqa: E402


def test_export_debug_writes_clean_per_edge_artifacts():
    tmp_root = ROOT / "camera_nodes" / "test" / "fixtures" / "_tmp_mtf"
    tmp_root.mkdir(exist_ok=True)
    tmp_path = tmp_root / "debug_export"
    tmp_path.mkdir(exist_ok=True)
    config = MTFConfig()
    config.debug_export_dir = str(tmp_path)
    config.debug_export_csv = True
    config.debug_export_png = True

    if not hasattr(debug_export_module.cv2, "imwrite"):
        sys.modules.pop("cv2", None)
        real_cv2 = importlib.import_module("cv2")
        debug_export_module.cv2 = real_cv2

    roi = np.tile(np.linspace(0, 255, 40, dtype=np.uint8), (30, 1))
    export_debug(
        config=config,
        esf=np.linspace(0.0, 1.0, 32),
        lsf=np.linspace(-0.1, 0.1, 32),
        lsf_windowed=np.linspace(-0.08, 0.08, 32),
        frequencies=np.linspace(0.0, 120.0, 32),
        mtf_raw=np.linspace(1.0, 0.0, 32),
        mtf_used=np.linspace(0.95, 0.0, 32),
        mtf_ideal=np.linspace(1.0, 0.1, 32),
        debug_label="manual",
        roi_img=roi,
        edge_line=(20.0, 15.0, 1.0, 0.2),
        metadata={
            "roi_bbox_x": 100,
            "roi_bbox_y": 200,
            "analysis_roi_bounds": (108, 204, 128, 226),
            "edge_angle_deg": 5.2,
            "edge_angle_method": "geometric",
            "edge_angle_phase": 5.0,
            "edge_angle_consistency_deg": 0.2,
            "edge_support_points": 42,
        },
    )

    expected_files = {
        "manual_esf.csv",
        "manual_lsf.csv",
        "manual_mtf.csv",
        "manual_metadata.csv",
        "manual_plot.png",
        "manual_roi.png",
    }
    assert expected_files.issubset({path.name for path in tmp_path.iterdir()})

    roi_png = debug_export_module.cv2.imread(str(tmp_path / "manual_roi.png"))
    assert roi_png is not None
    assert roi_png.shape[0] == roi.shape[0]
    assert roi_png.shape[1] == roi.shape[1]
