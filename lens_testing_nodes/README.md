# Lens Testing Nodes

ROS2 package for autofocus and MTF measurement in the ProMOC Assembly System.

## 📦 Contents

- **hybrid_focus_node**: Hybrid autofocus with coarse/fine search
- **mtf_node**: MTF analysis using Slanted Edge Method (ISO 12233)

## 🚀 Quick Start

### 1. Build Package

```bash
cd ~/Documents/Development/Ros2/promoc_assembly
colcon build --packages-select lens_testing_nodes
source install/setup.bash
```

### 2. Start Autofocus

```bash
# Start autofocus node only
ros2 launch lens_testing_nodes autofocus.launch.py

# Trigger autofocus via service
ros2 service call /autofocus/start std_srvs/srv/Trigger
```

### 3. MTF Measurement

```bash
# Start MTF node
ros2 launch lens_testing_nodes mtf_measurement.launch.py

# Trigger measurement
ros2 service call /mtf/measure std_srvs/srv/Trigger
```

### 4. Full Measurement (Camera + Autofocus + MTF)

```bash
ros2 launch lens_testing_nodes full_measurement.launch.py
```

## 🔧 Configuration

### Autofocus Parameters (`config/autofocus_params.yaml`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `scan_start` | 0.0 | Start position [mm] |
| `scan_end` | 50.0 | End position [mm] |
| `coarse_step` | 1.0 | Coarse step size [mm] |
| `fine_tolerance` | 0.005 | Fine tolerance [mm] = 5µm |
| `settle_time` | 0.5 | Wait time after move [s] |

### MTF Parameters (`config/mtf_params.yaml`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `pixel_size_um` | 3.45 | Pixel size [µm] |
| `roi_width` | 200 | ROI width [px] |
| `roi_height` | 400 | ROI height [px] |
| `oversample_factor` | 4 | Oversampling factor |

## 📊 Topics

### Autofocus

| Topic | Type | Description |
|-------|------|-------------|
| `/autofocus/status` | String | Current status |
| `/autofocus/best_position` | Float32 | Best focus position [mm] |
| `/autofocus/current_score` | Float32 | Current sharpness score |
| `/autofocus/complete` | Bool | True when finished |

### MTF

| Topic | Type | Description |
|-------|------|-------------|
| `/mtf/status` | String | Measurement status |
| `/mtf/mtf50` | Float32 | MTF50 value [lp/mm] |
| `/mtf/curve` | Float32MultiArray | Complete MTF curve |

## 🛠️ Services

| Service | Description |
|---------|-------------|
| `/autofocus/start` | Start autofocus |
| `/autofocus/stop` | Stop autofocus |
| `/autofocus/get_result` | Get result |
| `/mtf/measure` | Perform MTF measurement |
| `/mtf/get_result` | Get MTF result |

## 📐 Algorithms

### Hybrid Autofocus

1. **Coarse Search (Linear Scan)**
   - Uses Variance metric for fast evaluation
   - Scans the entire range with large steps
   - Identifies approximate focus region

2. **Fine Search (Golden Section)**
   - Uses Tenengrad metric for high accuracy
   - Applies Golden Section Search optimization
   - Converges to sub-micrometer precision

### MTF Analysis (Slanted Edge Method)

1. **Edge Detection**: Automatic edge localization in ROI
2. **ESF Calculation**: Edge Spread Function from perpendicular profiles
3. **LSF Derivation**: Numerical differentiation
4. **FFT**: Fourier transform for MTF curve
5. **Normalization**: DC component normalization
6. **Metric Extraction**: MTF50, MTF20, MTF10 values

## 🔗 Dependencies

- `promoc_assembly_interfaces` - Custom message types
- `linear_axis_nodes` - LTS300 axis control
- `camera_nodes` - Camera interface
- `cv_bridge` - OpenCV ROS bridge
- `numpy` - Numerical computations
- `scipy` - Signal processing (FFT)

## 📝 License

MIT License - See main repository
