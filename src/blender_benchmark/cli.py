"""
Command-line interface for blender_benchmark.
"""
import argparse
import sys
import os
import shutil
import yaml
import json
import csv
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


def create_plots(engine, device, samples):
    """
    Create a 3x3 grid of metric plots from CSV/JSON result files.
    Saves to output/plots/{engine}_{device}_{samples}.png
    """
    results_dir = Path("output/results")
    plots_dir = Path("output/plots")
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    # Match both <engine>_<device>_<samples>_*.csv and with iter prefix
    pattern = f"{engine}_{device}_{samples}_*.csv"
    csv_files = sorted(results_dir.glob(pattern))
    
    if not csv_files:
        print(f"❌ No CSV files found for {engine}_{device}_{samples}")
        return
    
    # Prepare containers
    data = {
        "iteration": [],
        "render_time_sec": [],
        "cpu_time_sec": [],
        "cpu_intensity": [],
        "cpu_noise_std": [],
        "gpu_avg_percent": [],
        "ram_max_mb": [],
        "vram_max_mb": [],
        "psnr": [],
        "ssim": []
    }
    
    for csv_file in csv_files:
        try:
            text = csv_file.read_text().strip()
            # treat whole file as JSON
            result = json.loads(text)
            # clean keys by stripping whitespace
            clean = {k.strip(): v for k, v in result.items()}

            # determine iteration from filename
            stem = csv_file.stem
            if "_iter" in stem:
                iter_num = int(stem.split("_iter")[-1])
            else:
                # fallback: take last underscore-separated token
                try:
                    iter_num = int(stem.split("_")[-1])
                except ValueError:
                    iter_num = len(data["iteration"]) + 1

            data["iteration"].append(iter_num)
            data["render_time_sec"].append(float(clean.get("render_time_sec", 0)))
            data["cpu_time_sec"].append(float(clean.get("cpu_time_sec", 0)))
            data["cpu_intensity"].append(float(clean.get("cpu_intensity", 0)))
            data["cpu_noise_std"].append(float(clean.get("cpu_noise_std", 0)))
            data["gpu_avg_percent"].append(float(clean.get("gpu_avg_percent", 0)))
            data["ram_max_mb"].append(float(clean.get("ram_max_mb", 0)))
            data["vram_max_mb"].append(float(clean.get("vram_max_mb", 0)))
            psnr = clean.get("psnr")
            data["psnr"].append(float(psnr) if psnr is not None else 0)
            ssim = clean.get("ssim")
            data["ssim"].append(float(ssim) if ssim is not None else 0)
        except Exception as e:
            print(f"⚠️  Error reading {csv_file}: {e}")
            continue
    
    if not data["iteration"]:
        print(f"❌ Could not read any valid data from CSV files")
        return
    
    # Create 3x3 grid of plots
    fig = plt.figure(figsize=(15, 12))
    fig.suptitle(f"{engine} - {device} - {samples} samples", fontsize=16, fontweight="bold")
    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)
    
    metrics = [
        ("render_time_sec", "Render Time (s)", "Time"),
        ("cpu_time_sec", "CPU Time (s)", "Time"),
        ("cpu_intensity", "CPU Intensity", "Ratio"),
        ("cpu_noise_std", "CPU Noise Std Dev", "Value"),
        ("gpu_avg_percent", "GPU Avg Usage (%)", "Percent"),
        ("ram_max_mb", "RAM Max (MB)", "Memory"),
        ("vram_max_mb", "VRAM Max (MB)", "Memory"),
        ("psnr", "PSNR", "dB"),
        ("ssim", "SSIM", "Similarity")
    ]
    
    # ensure data sorted by iteration
    sorted_pairs = sorted(zip(data["iteration"], *[data[k] for k,_,_ in metrics]))
    # unzip sorted
    iters, *metric_lists = zip(*sorted_pairs)
    
    for idx, (metric_key, title, ylabel) in enumerate(metrics):
        row = idx // 3
        col = idx % 3
        ax = fig.add_subplot(gs[row, col])
        values = metric_lists[idx]
        
        ax.plot(iters, values, marker="o", linewidth=2, markersize=6)
        ax.set_title(title, fontweight="bold")
        ax.set_xlabel("Iteration")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        ax.set_xticks(iters)
    
    # Save plot
    output_filename = f"{engine}_{device}_{samples}.png"
    output_path = plots_dir / output_filename
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"✓ Plot saved: {output_path}")
    plt.close()


def delete_results():
    """Delete old results, plots, and renders."""
    output_path = Path("output")
    data_path = Path("data/renders")
    
    deleted_items = []
    
    # Delete output directory
    if output_path.exists():
        shutil.rmtree(output_path)
        deleted_items.append("✓ Deleted output/ directory")
    
    # Delete renders
    if data_path.exists():
        shutil.rmtree(data_path)
        deleted_items.append("✓ Deleted data/renders/ directory")
    
    if deleted_items:
        print("Results deleted successfully:")
        for item in deleted_items:
            print(f"  {item}")
    else:
        print("No results to delete.")


def load_config(config_file):
    """Load configuration from YAML file."""
    config_path = Path(config_file)
    
    if not config_path.exists():
        print(f"❌ Config file not found: {config_file}")
        return None
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        print(f"✓ Config loaded from {config_file}")
        return config
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None


def create_example_config():
    """Create example configuration file."""
    example_yaml = """# Blender Benchmark Configuration
blender_path: "/path/to/blender"
scene: "data/references/lightsaber.blend"
engine: "CYCLES"
device: "CPU"
samples: 64
reference: "data/references/ref/lightsaber_Cycles_CPU_64.png"
repeat: 1
"""
    
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    with open(config_dir / "example.yaml", 'w') as f:
        f.write(example_yaml)
    
    print("✓ Example config file created: config/example.yaml")


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Blender Benchmark - Test Blender rendering engines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python benchmarkCli.py --scene data/references/scene.blend --engine CYCLES --device CPU --samples 64
  python benchmarkCli.py --config config/example.yaml
  python benchmarkCli.py --delete-results
  python benchmarkCli.py --scene scene.blend --repeat 5
  python benchmarkCli.py --create-example-config
  python benchmarkCli.py --plot --engine CYCLES --device CPU --samples 64
""")
    
    # Configuration
    parser.add_argument("--config", 
                        help="Load configuration from YAML file")
    parser.add_argument("--create-example-config", 
                        action="store_true",
                        help="Create example configuration files")
    
    # Delete results
    parser.add_argument("--delete-results", 
                        action="store_true",
                        help="Delete old results, plots, and renders")
    
    # Plot creation
    parser.add_argument("--plot", 
                        action="store_true",
                        help="Create plots from benchmark results")
    
    # Benchmark parameters
    parser.add_argument("--blender-path", 
                        default="/home/intel/Blender/blender-5.0.0-linux-x64/blender",
                        help="Path to Blender executable")
    
    parser.add_argument("--scene", 
                        help="Path to .blend file")
    
    parser.add_argument("--engine", 
                        choices=["CYCLES", "BLENDER_EEVEE"],
                        default="CYCLES",
                        help="Render engine (default: CYCLES)")
    
    parser.add_argument("--device",
                        choices=["CPU", "CUDA", "OPTIX", "OPENCL"],
                        default="CPU",
                        help="Render device (default: CPU)")
    
    parser.add_argument("--samples", 
                        type=int,
                        help="Number of samples (e.g. 64, 256, 512)")
    
    parser.add_argument("--reference",
                        help="Path to reference PNG image for quality comparison")
    
    parser.add_argument("--frame", 
                        type=int, 
                        default=1,
                        help="Frame number to render (default: 1)")
    
    # Repeat option
    parser.add_argument("--repeat", 
                        type=int, 
                        default=1,
                        help="Run benchmark N times (default: 1)")
    
    # Show help
    parser.add_argument("--commands", 
                        action="store_true",
                        help="Show all available commands")
    
    args = parser.parse_args()
    
    # Handle --commands
    if args.commands:
        print_commands()
        return
    
    # Handle --plot
    if args.plot:
        # Require engine, device, and samples for plot creation
        if args.engine is None or args.device is None or args.samples is None:
            print("❌ Error: --plot requires --engine, --device, and --samples")
            print("Example: python benchmarkCli.py --plot --engine CYCLES --device CPU --samples 64")
            return
        create_plots(args.engine, args.device, args.samples)
        return
    
    # Handle --create-example-config
    if args.create_example_config:
        create_example_config()
        return
    
    # Handle --delete-results
    if args.delete_results:
        delete_results()
        return
    
    # Load config if provided
    if args.config:
        config = load_config(args.config)
        if config:
            # Override arguments with config values
            args.blender_path = config.get("blender_path", args.blender_path)
            args.scene = config.get("scene", args.scene)
            args.engine = config.get("engine", args.engine)
            args.device = config.get("device", args.device)
            args.samples = config.get("samples", args.samples)
            args.reference = config.get("reference", args.reference)
            args.frame = config.get("frame", args.frame)
            args.repeat = config.get("repeat", args.repeat)
        else:
            return
    
    # Validate scene argument
    if not args.scene:
        print("❌ Error: --scene argument is required")
        print("Use: python benchmarkCli.py --scene <path> or --config <file>")
        parser.print_help()
        return
    
    # Import benchmark function
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(__file__))
    
    # Load the root directory module
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    _sys.path.insert(0, root_dir)
    
    try:
        from benchmark import run_benchmark
    except ImportError as e:
        print(f"❌ Error importing benchmark: {e}")
        print("Make sure benchmark.py exists in the root directory")
        return
    
    # Run benchmark with repeat option
    print(f"\n🔄 Running benchmark {args.repeat} time(s)...\n")
    
    for i in range(args.repeat):
        if args.repeat > 1:
            print(f"\n{'='*60}")
            print(f"Run {i}/{args.repeat}")
            print(f"{'='*60}\n")
        
        run_benchmark(
            blender_path=args.blender_path,
            scene_path=args.scene,
            engine=args.engine,
            device=args.device,
            samples=args.samples,
            frame=args.frame,
            reference_image=args.reference,
            iteration=i
        )
    
    if args.repeat > 1:
        print(f"\n✓ All {args.repeat} runs completed!")


def print_commands():
    """Print all available commands."""
    commands = {
        "CONFIG & MANAGEMENT": [
            ("--config FILE", "Load configuration from YAML/JSON file"),
            ("--create-example-config", "Create example configuration files"),
            ("--delete-results", "Delete old results, plots, and renders"),
            ("--plot", "Create 3x3 metric plots from benchmark results*"),
        ],
        "BENCHMARK PARAMETERS": [
            ("--scene FILE", "Path to .blend file (REQUIRED)"),
            ("--engine [CYCLES|BLENDER_EEVEE]", "Render engine (default: CYCLES)"),
            ("--device [CPU|CUDA|OPTIX|OPENCL]", "Render device (default: CPU)"),
            ("--samples NUM", "Number of samples (e.g. 64, 256, 512)"),
            ("--reference FILE", "Path to reference image for quality comparison"),
            ("--frame NUM", "Frame number to render (default: 1)"),
        ],
        "EXECUTION": [
            ("--repeat NUM", "Run benchmark N times (default: 1)"),
            ("--blender-path PATH", "Path to Blender executable"),
        ],
        "HELP": [
            ("--help", "Show this help message"),
            ("--commands", "Show all available commands"),
        ]
    }
    
    print("\n" + "="*70)
    print("BLENDER BENCHMARK - Available Commands")
    print("="*70)
    
    for category, items in commands.items():
        print(f"\n📌 {category}")
        print("-" * 70)
        for cmd, description in items:
            print(f"  {cmd:<40} {description}")
    
    print("\n" + "="*70 + "\n")
    print("* --plot requires: --engine, --device, --samples")


if __name__ == "__main__":
    main()
