# Camera Configuration Directory

This directory contains the small camera configuration files used by the CS runtime.

## Runtime Focus

The maintained runtime only needs a few camera facts:

- camera identity and driver type
- pixel size and native resolution
- active pixel format and binning default
- exposure and frame-rate defaults
- camera calibration info
- dynamic GenICam parameters that the driver should expose

This directory is intentionally not an MTF or optical-analysis configuration area.

## Files

- `ids_u3_3800cp_hq.yaml`: default runtime camera
- `camera_template.yaml`: starting point for a new camera profile
- `README.md`: this overview

## Typical Workflow

1. Copy `camera_template.yaml` to a new `<camera_name>.yaml`
2. Fill in GUID, driver, camera name, pixel size, and resolution
3. Add calibration data to `camera_info`
4. List the dynamic camera parameters your hardware supports
5. Launch with:
   `ros2 launch promoc_bringup camera.launch.py runtime_mode:=hardware camera_type:=<camera_name>`

## Keep It Simple

When adding a new camera config, prefer only the keys the runtime actually uses:

<<<<<<< HEAD
- `camera_params`
- `exposure_time`
- `frame_rate`
- `camera_info`
- `dynamic_parameters`
=======
The system will automatically load: `config/cameras/basler_ace_2500.yaml`

### Simulation Mode

```bash
ros2 launch promoc_bringup camera.launch.py runtime_mode:=sim
```

## ➕ Adding a New Camera

### Step 1: Create Camera Configuration

1. Copy the template:
   ```bash
   cd promoc_bringup/config/cameras/
   cp camera_template.yaml <your_camera_model>.yaml
   ```

2. Edit `<your_camera_model>.yaml` and fill in all specifications:
   - Find your camera GUID: `arv-tool-0.8 -l`
   - Update sensor specifications from datasheet
   - Configure pixel format: `arv-tool-0.8 -n "<camera>" features | grep PixelFormat`
   - Set exposure limits: `arv-tool-0.8 -n "<camera>" features | grep ExposureTime`

### Step 2: Calibrate Your Camera

Use ROS camera calibration tools:

```bash
ros2 run camera_calibration cameracalibrator \
    --size 8x6 \
    --square 0.025 \
    --ros-args -r image:=/promoc/assembly_camera/stream0/image_raw
```

Follow the calibration process and save the results.

### Step 3: Update MTF Parameters

Calculate MTF-relevant parameters:

```python
# Nyquist frequency (lp/mm)
nyquist = 1 / (2 * pixel_size_mm)

# Example: If pixel_size = 2.4 µm = 0.0024 mm
# nyquist = 1 / (2 * 0.0024) = 208.33 lp/mm
```

### Step 4: Test Your Configuration

```bash
# Launch with your new camera
ros2 launch promoc_bringup camera.launch.py camera_type:=<your_camera_model>

# Verify image topics
ros2 topic hz /promoc/assembly_camera/stream0/image_raw
ros2 topic echo /promoc/assembly_camera/stream0/image_raw --field height,width

# View images
ros2 run rqt_image_view rqt_image_view
```

## 📊 Camera Properties Required

### Essential Parameters
- **GUID**: Unique camera identifier
- **Driver**: `usb3vision` or `gigevision`
- **Pixel size**: Physical sensor pixel dimension (µm)
- **Resolution**: Native sensor resolution (pixels)
- **Pixel format**: Image format (RGB8, BayerRG8, Mono8, etc.)

### Calibration Parameters
- **Camera matrix**: Intrinsic parameters (fx, fy, cx, cy)
- **Distortion coefficients**: Lens distortion model
- **Image dimensions**: Actual resolution used

### MTF Parameters
- **Nyquist frequency**: Theoretical resolution limit
- **Pixel size (mm)**: For spatial calculations
- **Recommended exposure**: Starting point for MTF tests
- **Binning modes**: Supported binning configurations

## 🔧 Finding Camera Information

### List All Connected Cameras
```bash
arv-tool-0.8 -l
```

### View All Camera Features
```bash
arv-tool-0.8 -n "<camera_name>" features
```

### Check Specific Feature
```bash
arv-tool-0.8 -n "<camera_name>" features <FeatureName>
```

**Useful features to check:**
- `PixelFormat` - Available image formats
- `ExposureTime` - Exposure limits
- `AcquisitionFrameRate` - Frame rate capabilities
- `Gain` - Gain control range
- `Width`, `Height` - Resolution settings

### Test Camera Stream
```bash
arv-camera-test-0.8 -n "<camera_name>"
```

## 📝 Configuration Tips

### Pixel Format Selection
- **Raw Bayer** (BayerRG8/10/12): Best quality, software debayering
- **RGB8/BGR8**: Fast, hardware debayering
- **Mono8/16**: Monochrome cameras or best MTF accuracy

### Exposure Settings
- Start with moderate exposure (50-200 ms)
- Avoid saturation (clipping at max pixel value)
- Check histogram to ensure good dynamic range
- For MTF: Target 50-70% of sensor range

### Frame Rate vs Exposure
```
max_frame_rate ≤ 1 / exposure_time
```

If exposure = 100 ms, max FPS ≈ 10

### Binning Trade-offs
- **1x1**: Full resolution, standard sensitivity
- **2x2**: Half resolution, 4x sensitivity, 4x speed
- **4x4**: Quarter resolution, 16x sensitivity, 16x speed

Note: Binning reduces spatial resolution and affects MTF!

## 🎓 Best Practices

### 1. **Naming Convention**
Use descriptive, lowercase names with underscores:
- ✅ `ids_u3_3800cp_hq.yaml`
- ✅ `basler_ace_2500_14gm.yaml`
- ❌ `camera1.yaml`
- ❌ `NewCamera.yaml`

### 2. **Documentation**
Always document:
- Camera purchase date
- Calibration date and conditions
- Lens type and settings
- Working distance
- Lighting setup

### 3. **Version Control**
Commit camera configurations:
```bash
git add promoc_bringup/config/cameras/<your_camera>.yaml
git commit -m "Add configuration for <camera model>"
```

### 4. **Validation**
Before production use:
- ✅ Test image acquisition
- ✅ Verify calibration accuracy
- ✅ Measure actual MTF
- ✅ Check frame rate stability
- ✅ Verify stable recovery path via pre-launch reset + restart flow

### 5. **Backup Calibration**
Save calibration files separately:
```
calibration_data/
├── camera_name_YYYY-MM-DD.yaml
└── calibration_images/
```

## 🐛 Troubleshooting

### Camera Not Detected
```bash
# Check USB connection
lsusb | grep IDS  # or grep Basler, etc.

# Check Aravis can see camera
arv-tool-0.8 -l

# Check permissions
sudo chmod 666 /dev/bus/usb/XXX/YYY
```

### No Images Published
```bash
# Check camera driver logs
ros2 node info /promoc/assembly_camera

# Monitor topics
ros2 topic list | grep camera
ros2 topic hz /promoc/assembly_camera/stream0/image_raw
```

### Wrong Resolution/Format
```bash
# Verify configuration loaded correctly
ros2 param get /promoc/assembly_camera ImageFormatControl

# Check camera hardware capabilities
arv-tool-0.8 -n "<camera>" features Width
arv-tool-0.8 -n "<camera>" features PixelFormat
```

### Performance Issues
- Reduce resolution (use ROI)
- Increase binning
- Reduce frame rate
- Check USB3 connection (not USB2)
- Disable unnecessary image processing

## 📚 Additional Resources

- [IDS Camera Documentation](https://www.ids-imaging.com/)
- [Aravis Camera Driver](https://github.com/AravisProject/aravis)
- [camera_aravis2 ROS2 Package](https://github.com/FraunhoferIOSB/camera_aravis2)
- [ROS Camera Calibration](https://wiki.ros.org/camera_calibration/Tutorials)
- [GenICam Standard](https://www.emva.org/standards-technology/genicam/)

## 💡 Support

For camera configuration assistance:
1. Check `camera_template.yaml` for detailed instructions
2. Review existing camera configs for examples
3. Consult camera manufacturer documentation
4. Test with `arv-tool-0.8` command-line utilities

---

**Last Updated**: 2026-01-29  
**Default Camera**: IDS U3-3800CP-c-HQ Rev.2.2

>>>>>>> d07c2ebef4de684c5999a52116404a2727fe38b0
