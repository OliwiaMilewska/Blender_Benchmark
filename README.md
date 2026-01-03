# Blender Benchmark

Python script to benchmark and test rendering engines in Blender. Measure performance metrics like render time, CPU/GPU utilization, memory usage, and image quality.

## Features

- 🎨 **Multi-Engine Support**: Test CYCLES and EEVEE rendering engines
- 💻 **Device Selection**: CPU, CUDA, OPTIX, OPENCL support
- 📊 **Performance Metrics**: Track render time, CPU/GPU usage, RAM/VRAM
- 🖼️ **Quality Assessment**: PSNR and SSIM image quality comparison
- 🔄 **Batch Testing**: Run benchmarks multiple times for reliable results
- ⚙️ **Config Management**: YAML configuration files
- 📈 **Data Export**: CSV and JSON result formats

## Requirements

- Python 3.8+
- Blender 4.0+ (with Python support)
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

```bash
python benchmark.py --scene data/references/lightsaber.blend \
  --engine CYCLES \
  --device CPU \
  --samples 64 \
  --reference data/references/ref/lightsaber_Cycles_CPU_64.png
```

**Arguments:**
- `--blender-path` - Path to Blender executable (default: `/home/User/Blender/blender-5.0.0-linux-x64/blender`)
- `--scene` ⭐ - Path to .blend file (REQUIRED)
- `--engine` - CYCLES or BLENDER_EEVEE (default: CYCLES)
- `--device` - CPU, CUDA, OPTIX, OPENCL (default: CPU)
- `--samples` - Number of render samples
- `--reference` - Path to reference image for quality comparison
- `--frame` - Frame number to render (default: 1)

### Option 2: CLI with Configuration

Use the CLI for advanced features and easier configuration:

```bash
python run.py --help
python run.py --commands
```

#### Basic Usage

```bash
python run.py --scene data/references/scene.blend --engine CYCLES --device CPU --samples 64
```

#### Load Configuration from YAML

```bash
python run.py --config config/example.yaml
```

#### Run Multiple Times (For Statistical Accuracy)

```bash
python run.py --scene data/references/scene.blend --repeat 5
```

#### Delete Old Results

```bash
python run.py --delete-results
```

#### Create Example Configuration File

```bash
python run.py --create-example-config
```

### Configuration File (YAML)

Create `config/custom.yaml`:

```yaml
# Blender Benchmark Configuration
blender_path: "/path/to/blender"
scene: "data/references/lightsaber.blend"
engine: "CYCLES"
device: "CPU"
samples: 64
reference: "data/references/ref/lightsaber_Cycles_CPU_64.png"
frame: 1
repeat: 1
```

Then run:
```bash
python run.py --config config/custom.yaml
```

## Project Structure

```
Blender_Benchmark/
├── benchmark.py                    # Main benchmark script
├── run.py                          # CLI entry point
├── monitor_system.py               # CPU/GPU monitoring
├── monitor_vram.py                 # VRAM monitoring
├── quality_metrics.py              # Image quality metrics (PSNR, SSIM)
│
├── data/
│   ├── references/                 # Input: .blend files & reference images
│   └── renders/                    # Output: rendered images
│
├── output/                         # Generated results (git-ignored)
│   ├── results/                    # CSV and JSON data
│   └── plots/                      # Generated plots
│
├── blender_scripts/
│   ├── blender_cycles_render.py    # CYCLES render script
│   └── blender_eevee_render.py     # EEVEE render script
│
├── config/
│   ├── example.yaml                # Example configuration
│   └── [custom configs]
│
├── src/blender_benchmark/          # Package source (optional for imports)
├── tests/                          # Unit tests
├── requirements.txt                # Python dependencies
├── setup.py                        # Package setup
└── README.md                       # This file
```

## Examples

### Example 1: Basic Benchmark
```bash
python benchmark.py --scene data/references/scene.blend \
  --engine CYCLES \
  --device CPU \
  --samples 100
```

### Example 2: Compare Quality
```bash
python benchmark.py --scene data/references/scene.blend \
  --engine CYCLES \
  --device CPU \
  --samples 256 \
  --reference data/references/ref/original.png
```

### Example 3: Batch Testing with CLI
```bash
python run.py --config config/test_cycles_cpu.yaml --repeat 3
```

### Example 4: Multiple Configurations
```bash
# Test different configurations
python run.py --config config/cycles_cpu.yaml
python run.py --config config/cycles_cuda.yaml
python run.py --config config/eevee.yaml
```

## Output

Results are saved in `output/results/`:

### CSV Results
`output/results/results.csv` - Cumulative benchmark results

Columns:
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

### JSON Results
`output/results/last_results.json` - Latest benchmark results

### Rendered Images
`data/renders/` - Output PNG images from benchmark

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
5. **Monitor Results**: Check `output/results/results.csv` for trends

## Author
Oliwia Milewska
Master's Project - University of Gdańsk

## License

MIT License - See LICENSE file
