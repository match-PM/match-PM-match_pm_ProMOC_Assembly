"""Deterministic synthetic IO for workflow tests; NEVER hardware validation."""
from dataclasses import replace
import time

import numpy as np

from .measurement_engine import MeasurementEngine


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
        samples = [im[condition.roi_y:condition.roi_y+condition.roi_height,
                      condition.roi_x:condition.roi_x+condition.roi_width] for im in images]
        return {"bright_fraction": float(np.median([np.percentile(s,95)/4095 for s in samples])),
                "dark_fraction": float(np.median([np.percentile(s,5)/4095 for s in samples])),
                "saturated_fraction": float(np.median([np.mean(s>=0.98*4095) for s in samples])),
                "native_max": 4095.0}

    def focus_score(self, image, condition):
        crop = image[condition.roi_y:condition.roi_y+condition.roi_height,
                     condition.roi_x:condition.roi_x+condition.roi_width].astype(float)
        return float(np.mean(np.diff(crop,axis=1)**2))

    def analysis_config(self):
        from .algorithms.mtf import MTFConfig
        from dataclasses import asdict
        return asdict(MTFConfig(input_mode="dense_gray", capture_pixel_format="Mono12", source_encoding="mono16"))


def run_simulation(condition, source):
    condition = replace(condition, campaign_id=condition.campaign_id+"-simulation")
    if not condition.roi_width:
        condition.roi_x,condition.roi_y,condition.roi_width,condition.roi_height = 16,16,96,96
    io = SimulatedIO(condition)
    engine = MeasurementEngine(condition, io, feedback=lambda phase,index,done: print(f"SIM {phase}: {done}/{condition.measurement_count}"))
    return engine.run(source)
