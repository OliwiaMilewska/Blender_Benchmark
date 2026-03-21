# Blender Benchmark

Python script to benchmark and test rendering engines in Blender. Measure performance metrics like render time, CPU/GPU utilization, memory usage, and image quality.

## Features

- 🎨 **Multi-Engine Support**: Test CYCLES and EEVEE rendering engines with engine-specific settings
- 💻 **Device Selection**: CPU, CUDA, OPTIX, OPENCL support for Cycles
- ⚙️ **Engine-Specific Configurations**: Custom settings for Cycles (device, samples) and Eevee (shadow pool size, taa_render_samples)
- 📊 **Performance Metrics**: Track render time, CPU/GPU usage, RAM/VRAM
- 🖼️ **Quality Assessment**: PSNR and SSIM image quality comparison
- 🔄 **Batch Testing**: Run benchmarks multiple times for reliable results
- ⚙️ **Config Management**: YAML configuration files with engine-specific sections
- 📈 **Data Export**: JSON result formats

## Requirements

- Python 3.8+
- Blender 5.0+ (with Python support)
- NVIDIA GPU (for CUDA/OPTIX) - optional, CPU rendering works without

## Installation

### 1. Clone Repository
```bash
cd Blender_Benchmark
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

Required packages:
- psutil (system monitoring)
- pynvml (GPU monitoring)
- scikit-image (image quality metrics)
- Pillow (image processing)
- numpy (numerical operations)
- matplotlib (plotting)
- PyYAML (config parsing)

## Usage

### Option 1: Direct Script

Run benchmarks directly with command-line arguments:

#### For Cycles:
```bash
python benchmarkCli.py --scene data/references/lightsaber.blend \
  --engine CYCLES \
  --device CPU \
  --samples 64 \
  --reference data/references/ref/lightsaber_Cycles_CPU_64.png
```

#### For Eevee:
```bash
python benchmarkCli.py --scene data/references/lightsaber.blend \
  --engine BLENDER_EEVEE \
  --samples 64 \
  --profile HIGH \
  --reference data/references/ref/lightsaber_Eevee_64.png
```

**Arguments:**
- `--blender-path` - Path to Blender executable (default: `/home/User/Blender/blender-5.0.0-linux-x64/blender`)
- `--scene` - Path to .blend file (REQUIRED)
- `--engine` - CYCLES or BLENDER_EEVEE (default: CYCLES)
- `--device` - CPU, CUDA, OPTIX, OPENCL (default: CPU, only for Cycles)
- `--samples` - Number of render samples
- `--reference` - Path to reference image for quality comparison
- `--wait` - Seconds to wait between repeated runs (default: 600)
= `--profile` - Eevee quality profile (default: MEDIUM)

### Option 2: CLI with Configuration

Use the CLI for advanced features and easier configuration:

```bash
python benchmarkCli.py --help
python benchmarkCli.py --commands
```

#### Basic Usage

```bash
python benchmarkCli.py --scene data/references/scene.blend --engine CYCLES --device CPU --samples 64
```

#### Load Configuration from YAML

```bash
python benchmarkCli.py --config config/example.yaml
```

#### Run Multiple Times (For Statistical Accuracy)

```bash
python benchmarkCli.py --scene data/references/scene.blend --repeat 5
```

#### Delete Old Results

```bash
python benchmarkCli.py --delete-results
```

#### Create Example Configuration File

```bash
python benchmarkCli.py --create-example-config
```

#### Create Performance Plots

Generate a 3x3 grid of metric plots from benchmark results:

```bash
python benchmarkCli.py --plot --engine CYCLES --device CPU --samples 64
```

This creates a comprehensive visualization including:
- Render time and CPU time trends
- CPU intensity and noise metrics
- GPU/RAM/VRAM usage
- Quality metrics (PSNR, SSIM)

Plots are saved in `output/plots/` with naming: `{engine}_{device}_{samples}.png`

### Configuration File (YAML)

Create `config/custom.yaml`:

#### For Cycles:
```yaml
blender_path: "/path/to/blender"
scene: "data/references/lightsaber.blend"
engine: "CYCLES"
cycles_settings:
  device: "CPU"
  samples: 64
reference: "data/references/ref/lightsaber_Cycles_CPU_64.png"
repeat: 1
wait: 600
```

#### For Eevee:
```yaml
blender_path: "/path/to/blender"
scene: "data/references/lightsaber.blend"
engine: "BLENDER_EEVEE"
eevee_settings:
  profile: "HIGH"
  samples: 64
reference: "data/references/ref/lightsaber_Eevee_64.png"
repeat: 1
wait: 600
```

Then run:
```bash
python benchmarkCli.py --config config/custom.yaml
```

## Project Structure

```
Blender_Benchmark/
├── benchmarkCli.py                    # Main benchmark script
├── benchmarkCli.py                 # CLI entry point
├── monitor_system.py               # CPU/GPU monitoring
├── monitor_vram.py                 # VRAM monitoring
├── quality_metrics.py              # Image quality metrics (PSNR, SSIM)
│
├── data/
│   ├── references/
│   │   └── ref/                    # Reference images for quality comparison
│   └── renders/                    # Output: rendered images
│
├── output/                         # Generated results
│   ├── results/                    # CSV and JSON data
│   └── plots/                      # Generated plots
│
├── src/
│   └── blender_benchmark/          # Package source
│       ├── __init__.py
│       ├── cli.py
│       ├── monitor_system.py
│       ├── monitor_vram.py
│       ├── quality_metrics.py
│       └── blender_scripts/
│           ├── __init__.py
│           ├── blender_cycles_render.py    # CYCLES render script
│           └── blender_eevee_render.py     # EEVEE render script
│
├── config/
│   └── example.yaml                # Example configuration
│
├── requirements.txt                # Python dependencies
├── LICENSE                         # MIT License
└── README.md                       # This file
```

## Examples

### Example 1: Basic Benchmark (Cycles)
```bash
python benchmarkCli.py --scene data/references/scene.blend \
  --engine CYCLES \
  --device CPU \
  --samples 256 \
  --reference data/references/ref/original.png
```

### Example 2: Eevee Benchmark
```bash
python benchmarkCli.py --scene data/references/scene.blend \
  --engine BLENDER_EEVEE \
  --samples 64 \
  --profile HIGH \
  --reference data/references/ref/eevee_original.png
```

### Example 3: Batch Testing with CLI
```bash
python benchmarkCli.py --config config/test_cycles_cpu.yaml --repeat 3
python benchmarkCli.py --config config/test_eevee.yaml --repeat 3
```

### Example 3: Multiple Configurations
```bash
# Test different configurations
python benchmarkCli.py --config config/cycles_cpu.yaml
python benchmarkCli.py --config config/cycles_cuda.yaml
python benchmarkCli.py --config config/eevee.yaml
```

### Example 4: Generate Performance Plots
```bash
# Run benchmarks multiple times
python benchmarkCli.py --scene data/references/scene.blend --engine CYCLES --device CPU --samples 256 --repeat 10
python benchmarkCli.py --scene data/references/scene.blend --engine BLENDER_EEVEE --samples 64 --repeat 10

# Then create visualization
python benchmarkCli.py --plot --engine CYCLES --device CPU --samples 256
python benchmarkCli.py --plot --engine BLENDER_EEVEE --samples 64
```

## Output

Results are saved in separate locations:

### CSV Results (`output/results/`)
Named as: `{engine}_{device}_{samples}_{N}.csv`

Each file contains metrics:
- render_engine, device, samples
- scene name
- render_time_sec
- cpu_time_sec
- cpu_intensity
- cpu_noise_std
- gpu_avg_percent
- ram_max_mb
- vram_max_mb
- psnr (quality metric)
- ssim (similarity metric)

### Plot Results (`output/plots/`)
Named as: `{engine}_{device}_{samples}.png`

3x3 grid visualization showing:
- **Row 1**: Render time, CPU time, CPU intensity
- **Row 2**: CPU noise, GPU usage, RAM usage
- **Row 3**: VRAM usage, PSNR, SSIM

### JSON Results

- render_engine
- device
- samples
- scene
- render_time_sec
- cpu_time_sec
- cpu_intensity
- cpu_noise_std
- gpu_avg_percent
- ram_max_mb
- vram_max_mb
- psnr
- ssim

### Rendered Images
`output/renders/` - Output PNG images from benchmark

### Plots
`output/plots/` - Performance visualization charts

## Troubleshooting

### GPU Monitoring Disabled
If you see "GPU monitoring: disabled", ensure NVIDIA GPU drivers are installed:
```bash
nvidia-smi  # Should show GPU info
```

### Blender Not Found
Update `--blender-path` to your Blender installation:
```bash
which blender  # Find Blender path on Linux/macOS
where blender  # Find Blender path on Windows
```

### Import Errors
Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### YAML Config Errors
Check YAML syntax at https://www.yamllint.com/

## Tips for Accurate Benchmarks

1. **Run Multiple Times**: Use `--repeat 5` to get statistical averages
2. **Close Other Apps**: Minimize background processes for consistency
3. **Use Reference Images**: Compare output quality with `--reference`
4. **Save Configurations**: Use YAML files for reproducible tests
5. **Monitor Results**: Check `output/results/` for trends

## Author
Oliwia Milewska
Master's Project - University of Gdańsk

## License

MIT License - See LICENSE file
