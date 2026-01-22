# ProMOC User Configuration Setup

## Quick Start for Students

1. **Copy the template:**
   ```bash
   cd promoc_bringup/config
   cp user_config.example.yaml user_config.yaml
   ```

2. **Edit with your name:**
   ```bash
   nano user_config.yaml
   ```
   
   Change `'YourName'` to your actual name (e.g., `'M.Mustermann'`)

3. **Done!** Your measurement logs will now be saved to:
   ```
   ~/Dokumente/Messungen/{YourName}/autofocus_logs/
   ```

## Configuration Options

The `user_config.yaml` file supports these settings:

### Required
- **`user.name`**: Your name for measurement logs

### Optional
- **`autofocus.refinement_samples`**: Samples per refinement level (default: 51)
- **`autofocus.min_step_mm`**: Minimum step size in mm (default: 0.010)
- **`autofocus.refinement_shrink_factor`**: Range reduction factor (default: 0.25)
- **`camera.pixel_size_um`**: Sensor pixel size in µm (default: 3.45)
- **`camera.mtf_csv_path`**: Path for MTF results (default: /tmp/mtf_results.csv)

## Note

⚠️ The `user_config.yaml` file is **not tracked by Git** - your personal settings stay local!
