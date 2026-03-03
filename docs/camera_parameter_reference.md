# Camera Parameter Reference

Generated from `camera_nodes/camera_nodes/config.py`.

Regenerate:

```bash
python promoc_bringup/scripts/generate_param_docs.py
```

## Minimal Required / Frequently Used

| Parameter | Default |
|---|---|
| `use_simulator` | `False` |
| `pixel_size_um` | `2.4` |
| `x_axis_node_name` | `lts300_x_axis` |
| `measurement.username` | `` |
| `measurement.base_path` | `` |
| `autofocus.refinement_samples` | `51` |
| `autofocus.min_step_mm` | `0.01` |
| `autofocus.refinement_shrink_factor` | `0.35` |
| `mtf.profile` | `default` |
| `mtf.use_full_frame` | `False` |
| `exposure.settle_frames_after_set` | `2` |
| `exposure.frame_timeout_s` | `1.0` |

## Advanced Tuning

See `promoc_bringup/scripts/generate_param_docs.py` for the full generated advanced table.

## Deprecated (Release N compatibility)

| Parameter | Replacement |
|---|---|
| `mtf_csv_path` | `mtf.debug_export_dir` |
| `autofocus.fly_over.step_size_fine` | `autofocus.min_step_mm` |
| `autofocus.fly_over.coarse_scan_range_mm` | `AutoFocus.srv request range` |
| `autofocus.fly_over.fine_scan_range_mm` | `autofocus.refinement_shrink_factor` |
| `autofocus.fly_over.coarse_drop_ratio` | `autofocus.fly_over.peak_window_ratio` |
| `autofocus.fly_over.fine_drop_ratio` | `autofocus.fly_over.peak_window_ratio` |
| `autofocus.fly_over.settle_coarse_s` | `autofocus.fly_over.settle_fine_s` |
