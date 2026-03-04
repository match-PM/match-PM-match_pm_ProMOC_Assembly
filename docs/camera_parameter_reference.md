# Camera Parameter Reference

Generated from `camera_nodes/camera_nodes/config.py`.

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
| `autofocus.refinement_mode` | `0` |
| `mtf.profile` | `default` |
| `mtf.use_full_frame` | `False` |
| `exposure.settle_frames_after_set` | `2` |
| `exposure.frame_timeout_s` | `1.0` |

## Advanced Tuning

| Parameter | Default |
|---|---|
| `default_roi_width` | `200` |
| `default_roi_height` | `200` |
| `enable_debug_overlay` | `False` |
| `autofocus.profile_table_json` | `` |
| `autofocus.fly_over.scan_speed_fast` | `10.0` |
| `autofocus.fly_over.step_size_coarse` | `0.5` |
| `autofocus.fly_over.step_size_fine` | `0.01` |
| `autofocus.fly_over.detection_stddev_threshold` | `15.0` |
| `autofocus.fly_over.roi_size` | `512` |
| `autofocus.fly_over.backtrack_mm` | `2.0` |
| `autofocus.fly_over.coarse_scan_range_mm` | `10.0` |
| `autofocus.fly_over.fine_scan_range_mm` | `0.3` |
| `autofocus.fly_over.coarse_drop_ratio` | `0.6` |
| `autofocus.fly_over.fine_drop_ratio` | `0.8` |
| `autofocus.fly_over.settle_coarse_s` | `0.2` |
| `autofocus.fly_over.settle_fine_s` | `0.3` |
| `autofocus.fly_over.use_sift_weighting` | `False` |
| `autofocus.fly_over.detection_poll_s` | `0.05` |
| `autofocus.fly_over.max_sample_step_mm` | `0.1` |
| `autofocus.fly_over.axis_speed_scale_default` | `1.0` |
| `autofocus.fly_over.smooth_window_samples` | `5` |
| `autofocus.fly_over.baseline_percentile` | `20.0` |
| `autofocus.fly_over.snr_threshold` | `3.0` |
| `autofocus.fly_over.full_scan_for_peak` | `True` |
| `autofocus.fly_over.peak_window_ratio` | `0.9` |
| `autofocus.fly_over.peak_window_margin_mm` | `1.0` |
| `autofocus.fly_over.peak_window_guard_mm` | `1.5` |
| `autofocus.fly_over.min_peak_window_width_mm` | `6.0` |
| `autofocus.fly_over.high_mag_threshold_x` | `4.0` |
| `autofocus.fly_over.very_high_mag_threshold_x` | `6.0` |
| `autofocus.fly_over.scan_speed_high_mag` | `2.0` |
| `autofocus.fly_over.scan_speed_very_high_mag` | `1.0` |
| `autofocus.fly_over.coarse_step_high_mag_mm` | `0.1` |
| `autofocus.fly_over.coarse_step_very_high_mag_mm` | `0.05` |
| `autofocus.fly_over.min_step_high_mag_mm` | `0.005` |
| `autofocus.fly_over.settle_high_mag_s` | `0.2` |
| `autofocus.fly_over.settle_very_high_mag_s` | `0.25` |
| `autofocus.fly_over.refinement_strategy` | `linear` |
| `autofocus.fly_over.refinement_mode` | `0` |
| `measurement_conditions.coaxial_light_voltage` | `0.0` |
| `measurement_conditions.coaxial_light_current` | `0.0` |
| `measurement_conditions.camera_objective` | `unknown` |
| `measurement_conditions.notes` | `` |
| `mtf.debug_export_dir` | `` |
| `mtf.debug_export_prefix` | `mtf` |
| `mtf.debug_export_csv` | `True` |
| `mtf.debug_export_png` | `False` |
| `mtf.lsf_window_mode` | `full` |
| `mtf.lsf_peak_window_size` | `0` |
| `mtf.derivative_mode` | `iso` |
| `mtf.apply_derivative_correction` | `True` |
| `mtf.derivative_correction_max` | `0.0` |
| `mtf.apply_angle_correction` | `True` |
| `mtf.esf_smooth_mode` | `none` |
| `mtf.esf_sg_window` | `11` |
| `mtf.esf_sg_poly` | `2` |
| `mtf.edge_validation_mode` | `warn` |
| `mtf.edge_validation_percentile` | `90.0` |
| `mtf.edge_validation_min_points` | `50` |
| `mtf.edge_validation_only_auto` | `False` |
| `mtf.clip_to_nyquist` | `True` |
| `mtf.export_dual_curves` | `False` |
| `mtf.clip_max` | `0.0` |
| `mtf.warn_threshold` | `1.05` |
| `mtf.full_frame_width` | `5536` |
| `mtf.full_frame_height` | `3692` |
| `mtf.full_frame_offset_x` | `0` |
| `mtf.full_frame_offset_y` | `0` |
| `mtf.full_frame_binning` | `1` |
| `mtf.full_frame_settle_s` | `0.25` |
| `mtf.full_frame_image_timeout_s` | `2.0` |
| `mtf.restore_after_measurement` | `True` |
| `mtf.restore_settle_s` | `0.15` |
| `mtf.log_format_switch` | `True` |
