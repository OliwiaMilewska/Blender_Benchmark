"""
Command-line interface for blender_benchmark.
"""
import argparse
import sys
import os
import shutil
import yaml
from pathlib import Path


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
  python benchmark.py --scene data/references/scene.blend --engine CYCLES --device CPU --samples 64
  python benchmark.py --config config/example.yaml
  python benchmark.py --delete-results
  python benchmark.py --scene scene.blend --repeat 5
  python benchmark.py --create-example-config
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


if __name__ == "__main__":
    main()
