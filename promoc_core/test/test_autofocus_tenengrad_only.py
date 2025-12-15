from promoc_core.algorithms.autofocus import AutofocusConfig, HybridAutofocus, ScanDirection
import os
import sys

import numpy as np

# Ensure we import the in-workspace promoc_core package rather than an older
# install/overlay version from the ROS workspace.
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_local_src_root = os.path.join(_repo_root, 'promoc_core')
sys.path.insert(0, _local_src_root)


def _dummy_image(value: int = 0) -> np.ndarray:
    # small grayscale image is sufficient for algorithm wiring tests
    return np.full((10, 10), value, dtype=np.uint8)


def test_autofocus_config_rejects_non_tenengrad_metric() -> None:
    cfg = AutofocusConfig(metric='variance')
    try:
        cfg.validate()
    except ValueError:
        return
    raise AssertionError('Expected ValueError for non-tenengrad metric')


def test_autofocus_runs_with_tenengrad_metric() -> None:
    cfg = AutofocusConfig(
        z_min_mm=0.0,
        z_max_mm=1.0,
        coarse_step_mm=0.5,
        fine_step_mm=0.25,
        fine_range_mm=0.5,
        metric='tenengrad',
        scan_direction=ScanDirection.FORWARD,
    )
    af = HybridAutofocus(cfg)

    z = af.start()
    # Execute until finished. We don't care about the specific optimum here,
    # only that the state machine completes using the single metric.
    for _ in range(50):
        res = af.process_image(z, _dummy_image(10))
        if res.finished:
            assert res.best_z_mm is not None
            return
        assert res.next_z_mm is not None
        z = res.next_z_mm

    raise AssertionError('autofocus did not finish within expected iterations')
