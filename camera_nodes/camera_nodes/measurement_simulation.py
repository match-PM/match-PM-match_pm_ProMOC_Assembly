"""Deterministic synthetic IO for workflow tests; NEVER hardware validation."""
from dataclasses import replace
import time

import numpy as np

from .measurement_engine import MeasurementEngine
from .intensity import aggregate_intensity, measure_intensity


class SimulatedIO:
    simulated = True

    def __init__(self, condition):
        self.c = condition
        self.pos = (condition.axis_max_mm+condition.park_position_mm)/2
        self.best = self.pos
        self.exposure = 7999.0
        self.timestamp = 0
        self.moves = []
        self.rng = np.random.default_rng(42)

    def check(self):
        pass

    def acquire(self, token):
        self.token = token

    def release(self):
        pass

    def position(self):
        return self.pos

    def move(self, position, timeout, tolerance):
        self.pos = float(position)
        self.moves.append(self.pos)
        return self.pos

    def latest_timestamp(self):
        return self.timestamp

    def frame(self, last_timestamp, timeout):
        self.timestamp = max(self.timestamp, last_timestamp)+100000000
        y,x = np.mgrid[:self.c.roi_y+self.c.roi_height+16, :self.c.roi_x+self.c.roi_width+16]
        sigma = 0.7 + 15*abs(self.pos-self.best)/self.c.fine_focus_half_range_mm
        edge = 1/(1+np.exp(np.clip(-(x-(self.c.roi_x+self.c.roi_width/2)-0.08*(y-self.c.roi_y))/sigma,-100,100)))
        image = np.clip((0.02+0.5*edge)*self.exposure/7999*4095 + self.rng.normal(0,0.5,x.shape),0,4095).astype(np.uint16)
        return {"image": image, "source_timestamp_ns": self.timestamp,
                "received_utc_ns": time.time_ns(), "received_monotonic_ns": time.monotonic_ns(),
                "source_clock": "synthetic", "encoding": "mono16"}

    def state(self):
        return {"values": {"exposure_time": self.exposure, "gain": 0.0, "pixel_format": "Mono12"},
                "identity": {"axis_epoch": "synthetic", "camera_node_epoch": "synthetic"}}

    def preflight(self, condition):
        return {"simulated": True, "warning": "SYNTHETIC DATA, not a hardware measurement"}

    def set_exposure(self, exposure):
        self.exposure = exposure

    def levels(self, images, condition):
        roi = (condition.roi_x, condition.roi_y, condition.roi_width, condition.roi_height)
        result = aggregate_intensity([
            measure_intensity(image, roi, pixel_format="Mono12",
                              max_saturated_fraction=condition.max_saturated_fraction)
            for image in images
        ])
        result["bright_fraction"] = result["white_level_norm"]
        result["dark_fraction"] = result["black_level_norm"]
        result["saturated_fraction"] = result["saturation_fraction"]
        return result

    def focus_score(self, image, condition):
        crop = image[condition.roi_y:condition.roi_y+condition.roi_height,
                     condition.roi_x:condition.roi_x+condition.roi_width].astype(float)
        return float(np.mean(np.diff(crop,axis=1)**2))

    def analysis_config(self):
        from .algorithms.mtf import MTFConfig
        from dataclasses import asdict
        return asdict(MTFConfig(input_mode="dense_gray", capture_pixel_format="Mono12", source_encoding="mono16"))

    def analyze_mtf_roi_frame(self, image, condition, analysis_config, edge_geometry=None):
        """Synthetic four-edge bundle matching the hardware action contract."""
        from .algorithms.mtf import MTFAnalyzer, MTFConfig

        x, y, width, height = (
            condition.roi_x, condition.roi_y,
            condition.roi_width, condition.roi_height,
        )
        config = MTFConfig(**analysis_config)
        config.debug_export_dir = None
        config.debug_export_csv = False
        config.debug_export_png = False
        result = MTFAnalyzer(config).compute_mtf(
            image[y:y+height, x:x+width], roi_origin=(x, y)
        )
        edges = []
        for index, name in enumerate(("top", "right", "bottom", "left"), start=1):
            cloned = replace(result)
            cloned.edge_name = name
            cloned.edge_direction = "horizontal" if name in {"top", "bottom"} else "vertical"
            cloned.roi_bounds = (x, y, width, height)
            edges.append({
                "edge_label": f"{index:02d}_{name}",
                "edge_name": name,
                "edge_direction": cloned.edge_direction,
                "bbox": (x, y, width, height),
                "contrast": float(cloned.contrast),
                "result": cloned,
            })
        return {
            "mode": "roi_search_square4",
            "search_roi": (x, y, width, height),
            "edges": edges,
        }


def run_simulation(condition, source):
    condition = replace(condition, campaign_id=condition.campaign_id+"-simulation")
    if not condition.roi_width:
        condition.roi_x,condition.roi_y,condition.roi_width,condition.roi_height = 16,16,96,96
    io = SimulatedIO(condition)
    engine = MeasurementEngine(condition, io, feedback=lambda phase,index,done: print(f"SIM {phase}: {done}/{condition.measurement_count}"))
    return engine.run(source)
