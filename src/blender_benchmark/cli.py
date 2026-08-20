"""
Command-line interface for blender_benchmark.
"""
import argparse
import csv
import os
import shutil
import time
import yaml
import json
import sys as _sys
from tqdm.auto import tqdm
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


def build_iteration_plan(repeat=1):
    """Return execution plan for benchmark runs, with one warmup run plus the requested number of measurements."""
    if repeat <= 0:
        return []
    return ["warmup"] + ["measurement"] * repeat


def create_plots(engine, device, samples, results_source=None):
    """
    Create a 3x3 grid of metric plots from JSON result files or a CSV result file.
    Saves to output/plots/{engine}_{device}_{samples}.png
    """
    default_results_dir = Path("output/results")
    plots_dir = Path("output/plots")
    plots_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "iteration": [],
        "render_time_sec": [],
        "cpu_intensity": [],
        "system_overhead_sec": [],
        "system_overhead_percent": [],
        "gpu_avg_percent": [],
        "ram_max_mb": [],
        "vram_max_mb": [],
        "psnr": [],
        "ssim": []
    }

    results_path = Path(results_source) if results_source else default_results_dir
    csv_files = []
    json_files = []
    scene_name = ""

    if not results_path.exists():
        print(f"❌ Results path not found: {results_path}")
        return

    if results_path.is_file():
        suffix = results_path.suffix.lower()
        if suffix == ".csv":
            csv_files = [results_path]
        elif suffix == ".json":
            json_files = [results_path]
        else:
            print(f"❌ Unsupported results file type: {results_path}")
            return
    else:
        csv_pattern = f"*_{engine}_{device}_{samples}.csv"
        json_pattern = f"*_{engine}_{device}_{samples}_*.json"
        csv_files = sorted(results_path.glob(csv_pattern))
        if not csv_files:
            json_files = sorted(results_path.glob(json_pattern))
            if not json_files:
                print(f"❌ No CSV or JSON files found for {engine}_{device}_{samples} in {results_path}")
                return

    if csv_files:
        try:
            for csv_file in csv_files:
                with open(csv_file, "r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        data["iteration"].append(int(row.get("iteration", 0)))
                        data["render_time_sec"].append(float(row.get("render_time_sec", 0)))
                        data["cpu_intensity"].append(float(row.get("cpu_intensity", 0)))
                        data["system_overhead_sec"].append(float(row.get("system_overhead_sec", 0)))
                        data["system_overhead_percent"].append(float(row.get("system_overhead_percent", 0)))
                        data["gpu_avg_percent"].append(float(row.get("gpu_avg_percent", 0)))
                        data["ram_max_mb"].append(float(row.get("ram_max_mb", 0)))
                        data["vram_max_mb"].append(float(row.get("vram_max_mb", 0)))
                        data["psnr"].append(float(row.get("psnr", 0)) if row.get("psnr") not in (None, "") else 0)
                        data["ssim"].append(float(row.get("ssim", 0)) if row.get("ssim") not in (None, "") else 0)
        except Exception as e:
            print(f"⚠️  Error reading CSV file: {e}")
            return
    else:
        for json_file in json_files:
            try:
                text = json_file.read_text().strip()
                result = json.loads(text)
                clean = {k.strip(): v for k, v in result.items()}
                scene_name = clean.get("scene", scene_name) or scene_name

                data["iteration"].append(int(clean["iteration"]))
                data["render_time_sec"].append(float(clean.get("render_time_sec", 0)))
                data["cpu_intensity"].append(float(clean.get("cpu_intensity", 0)))
                data["system_overhead_sec"].append(float(clean.get("system_overhead_sec", 0)))
                data["system_overhead_percent"].append(float(clean.get("system_overhead_percent", 0)))
                data["gpu_avg_percent"].append(float(clean.get("gpu_avg_percent", 0)))
                data["ram_max_mb"].append(float(clean.get("ram_max_mb", 0)))
                data["vram_max_mb"].append(float(clean.get("vram_max_mb", 0)))
                psnr = clean.get("psnr")
                data["psnr"].append(float(psnr) if psnr is not None else 0)
                ssim = clean.get("ssim")
                data["ssim"].append(float(ssim) if ssim is not None else 0)
            except Exception as e:
                print(f"⚠️  Error reading {json_file}: {e}")
                continue

    if not data["iteration"]:
        source_type = "CSV" if csv_files else "JSON"
        print(f"❌ Could not read any valid data from {source_type} files")
        return

    # Create 3x3 grid of plots
    fig = plt.figure(figsize=(15, 12))
    fig.suptitle(f"{engine}-{device}-{samples} samples - {scene_name}", fontsize=16, fontweight="bold")
    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)

    metrics = [
        ("render_time_sec", "Render Time (s)", "Time"),
        ("cpu_intensity", "CPU Intensity", "Ratio"),
        ("system_overhead_sec", "System Overhead (s)", "Time"),
        ("system_overhead_percent", "System Overhead (%)", "Percent"),
        ("gpu_avg_percent", "GPU Avg Usage (%)", "Percent"),
        ("vram_max_mb", "VRAM Max (MB)", "Memory"),
        ("ram_max_mb", "RAM Max (MB)", "Memory"),
        ("psnr", "PSNR", "dB"),
        ("ssim", "SSIM", "Similarity")
    ]

    # ensure data sorted by iteration
    sorted_pairs = sorted(zip(data["iteration"], *[data[k] for k,_,_ in metrics]))
    # unzip sorted
    iters, *metric_lists = zip(*sorted_pairs)
    metric_lists = [list(m) for m in metric_lists]

    # Map metric key to its values for easier processing
    metric_map = {metrics[i][0]: metric_lists[i] for i in range(len(metrics))}

    # Apply explicit y-axis rules requested by user:
    # - For time metrics and CPU/GPU noise/intensity: lower = max(0, min-5), upper = max+5
    # - For RAM/VRAM: lower = max(0, min-0.5), upper = max+0.5
    # We'll compute these on the fly below.
    for idx, (metric_key, title, ylabel) in enumerate(metrics):
        row = idx // 3
        col = idx % 3
        ax = fig.add_subplot(gs[row, col])

        # PSNR / SSIM
        if metric_key in ("psnr", "ssim"):
            values = metric_map.get(metric_key, [])
            latest = values[-1] if values else 0
            mean_orig = sum(values) / len(values) if values else 0
            ax.text(0.5, 0.55, title, ha="center", va="center", fontsize=14, fontweight="bold")
            ax.text(0.5, 0.40, f"Value: {latest:.4f}", ha="center", va="center", fontsize=14)
            ax.axis("off")
            continue

        # Plotting rules for specific metric groups
        values = metric_map.get(metric_key, [])
        ax.plot(iters, values, marker="o", linewidth=2, markersize=6)
        ax.set_title(title, fontweight="bold")
        ax.set_xlabel("Iteration")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        ax.set_xticks(iters)

        # Apply user-requested axis rules
        if metric_key in ("render_time_sec", "cpu_intensity", "system_overhead_sec", "system_overhead_percent", "gpu_avg_percent"):
            if values:
                vmin = min(values)
                vmax = max(values)
                if metric_key == "system_overhead_percent":
                    y_lower = max(0, vmin - 15)
                    y_upper = vmax + 15
                else:
                    y_lower = max(0, vmin - 5)
                    y_upper = vmax + 5
                ax.set_ylim(y_lower, y_upper)
            else:
                ax.set_ylim(0, 1)
            # show mean in corner
            if values:
                mean_orig = sum(values) / len(values)
                ax.text(0.02, 0.95, f"mean={mean_orig:.3g}", transform=ax.transAxes, fontsize=9, va="top")
            continue

        if metric_key in ("ram_max_mb"):
            if values:
                vmin = min(values)
                vmax = max(values)
                y_lower = max(0, vmin - 5)
                y_upper = vmax + 5
                ax.set_ylim(y_lower, y_upper)
                mean_orig = sum(values) / len(values)
                ax.text(0.02, 0.95, f"mean={mean_orig:.2f}", transform=ax.transAxes, fontsize=9, va="top")
            else:
                ax.set_ylim(0, 1)
            continue

        if metric_key in ("vram_max_mb"):
            if values:
                vmin = min(values)
                vmax = max(values)
                y_lower = max(0, vmin - 0.5)
                y_upper = vmax + 0.5
                ax.set_ylim(y_lower, y_upper)
                mean_orig = sum(values) / len(values)
                ax.text(0.02, 0.95, f"mean={mean_orig:.2f}", transform=ax.transAxes, fontsize=9, va="top")
            else:
                ax.set_ylim(0, 1)
            continue

        # Default plotting for other metrics (tighter margins)
        values = metric_map.get(metric_key, [])
        ax.plot(iters, values, marker="o", linewidth=2, markersize=6)
        ax.set_title(title, fontweight="bold")
        ax.set_xlabel("Iteration")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        ax.set_xticks(iters)

        if values:
            y_min = min(values)
            y_max = max(values)
            y_range = y_max - y_min
            if metric_key == "gpu_avg_percent":
                y_lower = max(0, y_min - 5)
                y_upper = min(100, y_max + 5)
            else:
                if y_range == 0:
                    y_margin = abs(y_max) * 0.05 if y_max != 0 else 1
                else:
                    y_margin = max(y_range * 0.08, abs(y_max) * 0.01, 0.01)
                y_lower = y_min - y_margin
                y_upper = y_max + y_margin
                if y_lower >= 0:
                    y_lower = max(0, y_lower)
            ax.set_ylim(y_lower, y_upper)
        else:
            ax.set_ylim(0, 1)

    # Save plot
    output_filename = f"{engine}_{device}_{samples}.png"
    output_path = plots_dir / output_filename
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"✓ Plot saved: {output_path}")
    plt.close()


def delete_results():
    """Delete old results, plots, and renders."""
    output_path = Path("output")
    data_path = Path("output/renders")

    deleted_items = []

    # Delete output directory
    if output_path.exists():
        shutil.rmtree(output_path)
        deleted_items.append("✓ Deleted output/ directory")

    # Delete renders
    if data_path.exists():
        shutil.rmtree(data_path)
        deleted_items.append("✓ Deleted output/renders/ directory")

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
# reference auto-resolved: data/references/ref/lightsaber_Cycles_CPU_ref.png
repeat: 1
wait: 300
"""

    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)

    with open(config_dir / "example.yaml", 'w') as f:
        f.write(example_yaml)

    print("✓ Example config file created: config/example.yaml")


def parse_config_settings(config):
    """Extract normalized benchmark settings from a loaded YAML config."""
    if not config:
        raise ValueError("Config is empty")

    engine = config.get("engine", "CYCLES")
    settings = {
        "blender_path": config.get("blender_path"),
        "scene": config.get("scene"),
        "engine": engine,
        "device": config.get("device", "CPU"),
        "samples": config.get("samples"),
        "reference": config.get("reference"),
        "repeat": config.get("repeat", 1),
        "wait": config.get("wait", 600),
        "profile": "MEDIUM",
    }

    if engine == "CYCLES":
        cycles = config.get("cycles_settings", {})
        settings["device"] = cycles.get("device", settings["device"])
        settings["samples"] = cycles.get("samples", settings["samples"] or 64)
    elif engine == "BLENDER_EEVEE":
        eevee = config.get("eevee_settings", {})
        settings["profile"] = eevee.get("profile", "LOW")
        settings["samples"] = eevee.get("samples", settings["samples"] or 64)

    return settings


def run_config_file(config_file, repeat_override=None, wait_override=None):
    """
    Run a single benchmark from a YAML config file.

    Returns True on success, False on failure.
    """
    config = load_config(config_file)
    if not config:
        return False

    try:
        settings = parse_config_settings(config)
    except ValueError as e:
        print(f"❌ {e}")
        return False

    if repeat_override is not None:
        settings["repeat"] = repeat_override
    if wait_override is not None:
        settings["wait"] = wait_override

    if not settings["scene"]:
        print("❌ Config is missing required field: scene")
        return False

    _sys.path.insert(0, os.path.dirname(__file__))
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    _sys.path.insert(0, root_dir)

    try:
        from benchmark import run_cycles_benchmark, run_eevee_benchmark, resolve_reference_path
    except ImportError as e:
        print(f"❌ Error importing benchmark functions: {e}")
        print("Make sure benchmark.py exists in the root directory")
        return False

    reference = settings["reference"]
    if not reference:
        ref_device = settings["device"]
        if settings["engine"] == "BLENDER_EEVEE":
            ref_device = "GPU"
        reference = resolve_reference_path(settings["scene"], settings["engine"], ref_device)
        print(f"Reference (auto): {reference}")

    iteration_plan = build_iteration_plan(settings["repeat"])
    print(
        f"\n🔄 Running benchmark {settings['repeat']} time(s), "
        f"with the first run treated as warmup...\n"
    )

    measurement_iteration = 0
    for index, stage in enumerate(iteration_plan, start=1):
        if len(iteration_plan) > 1:
            print(f"\n{'='*60}")
            print(f"{stage.capitalize()} run {index}/{len(iteration_plan)}")
            print(f"{'='*60}\n")

        if stage == "warmup":
            print("🔥 Warmup run: this iteration will not be included in the reported measurements.")
            iteration_value = 0
            store_results = False
        else:
            measurement_iteration += 1
            iteration_value = measurement_iteration
            store_results = True
            print("📏 Measurement run: this iteration will be included in the reported results.")

        try:
            if settings["engine"] == "CYCLES":
                run_cycles_benchmark(
                    blender_path=settings["blender_path"],
                    scene_path=settings["scene"],
                    device=settings["device"],
                    samples=settings["samples"],
                    reference_image=reference,
                    iteration=iteration_value,
                    store_results=store_results,
                )
            elif settings["engine"] == "BLENDER_EEVEE":
                run_eevee_benchmark(
                    blender_path=settings["blender_path"],
                    scene_path=settings["scene"],
                    samples=settings["samples"],
                    reference_image=reference,
                    iteration=iteration_value,
                    store_results=store_results,
                    profile=settings["profile"],
                )
        except Exception as e:
            print(f"❌ Benchmark failed: {e}")
            return False

        if len(iteration_plan) > 1 and index < len(iteration_plan):
            wait_seconds = max(0, settings["wait"])
            print(f"⏳ Waiting {wait_seconds} seconds before next iteration...")
            for _ in tqdm(range(wait_seconds), desc="Idle time", unit="s", leave=False):
                time.sleep(1)

    if len(iteration_plan) > 1:
        print(
            f"\n✓ All {len(iteration_plan)} runs completed, "
            "with the warmup excluded from measurements."
        )

    return True


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

    parser.add_argument("--results-file",
                        help="Path to a results CSV file or a directory containing JSON result files")

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

    # Repeat option
    parser.add_argument("--repeat", 
                        type=int, 
                        default=1,
                        help="Run benchmark N times (default: 1)")

    # Wait interval between iterations (seconds)
    parser.add_argument("--wait", 
                        type=int,
                        default=600,
                        help="Delay in seconds between benchmark iterations (default: 600)")

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
        if args.engine == "BLENDER_EEVEE":
            args.device = "GPU"
        create_plots(args.engine, args.device, args.samples, results_source=args.results_file)
        return

    # Handle --create-example-config
    if args.create_example_config:
        create_example_config()
        return

    # Handle --delete-results
    if args.delete_results:
        delete_results()
        return

    if args.config:
        repeat_override = args.repeat if args.repeat != 1 else None
        wait_override = args.wait if args.wait != 600 else None
        run_config_file(args.config, repeat_override=repeat_override, wait_override=wait_override)
        return

    _sys.path.insert(0, os.path.dirname(__file__))
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    _sys.path.insert(0, root_dir)

    try:
        from benchmark import run_cycles_benchmark, run_eevee_benchmark, resolve_reference_path
    except ImportError as e:
        print(f"❌ Error importing benchmark functions: {e}")
        print("Make sure benchmark.py exists in the root directory")
        return

    if not args.scene:
        print("❌ Error: --scene is required when not using --config")
        return

    if not args.reference:
        ref_device = args.device
        if args.engine == "BLENDER_EEVEE":
            ref_device = "GPU"
        args.reference = resolve_reference_path(args.scene, args.engine, ref_device)
        print(f"Reference (auto): {args.reference}")

    profile = getattr(args, "profile", "MEDIUM")
    iteration_plan = build_iteration_plan(args.repeat)

    print(f"\n🔄 Running benchmark {args.repeat} time(s), with the first run treated as warmup...\n")

    measurement_iteration = 0
    for index, stage in enumerate(iteration_plan, start=1):
        if len(iteration_plan) > 1:
            print(f"\n{'='*60}")
            print(f"{stage.capitalize()} run {index}/{len(iteration_plan)}")
            print(f"{'='*60}\n")

        if stage == "warmup":
            print("🔥 Warmup run: this iteration will not be included in the reported measurements.")
            iteration_value = 0
            store_results = False
        else:
            measurement_iteration += 1
            iteration_value = measurement_iteration
            store_results = True
            print("📏 Measurement run: this iteration will be included in the reported results.")

        if args.engine == "CYCLES":
            run_cycles_benchmark(
                blender_path=args.blender_path,
                scene_path=args.scene,
                device=args.device,
                samples=args.samples,
                reference_image=args.reference,
                iteration=iteration_value,
                store_results=store_results
            )
        elif args.engine == "BLENDER_EEVEE":
            run_eevee_benchmark(
                blender_path=args.blender_path,
                scene_path=args.scene,
                samples=args.samples,
                reference_image=args.reference,
                iteration=iteration_value,
                store_results=store_results,
                profile=profile
            )

        if len(iteration_plan) > 1 and index < len(iteration_plan):
            wait_seconds = max(0, args.wait)
            print(f"⏳ Waiting {wait_seconds} seconds before next iteration...")

            for _ in tqdm(range(wait_seconds), desc="Idle time", unit="s", leave=False):
                time.sleep(1)

    if len(iteration_plan) > 1:
        print(f"\n✓ All {len(iteration_plan)} runs completed, with the warmup excluded from measurements.")


def print_commands():
    """Print all available commands."""
    commands = {
        "CONFIG & MANAGEMENT": [
            ("--config FILE", "Load configuration from YAML/JSON file"),
            ("--create-example-config", "Create example configuration files"),
            ("--delete-results", "Delete old results, plots, and renders"),
            ("--plot", "Create 3x3 metric plots from benchmark results*"),
            ("--results-file FILE", "Path to a CSV file or JSON results directory for plot creation"),
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
