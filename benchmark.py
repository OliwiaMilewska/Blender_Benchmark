import subprocess
import time
import json
import os
import sys
import csv
import argparse
import matplotlib.pyplot as plt
from datetime import datetime
import psutil

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from blender_benchmark.monitor_system import SystemMonitor
from blender_benchmark.monitor_vram import VRAMMonitor
from blender_benchmark.quality_metrics import compute_psnr, compute_ssim

REF_DIR = "data/references/ref"


def ensure_dirs():
    os.makedirs("output/results", exist_ok=True)
    os.makedirs("output/plots", exist_ok=True)
    os.makedirs("output/renders", exist_ok=True)


def resolve_reference_path(scene_path, engine, device="CPU", ref_dir=REF_DIR):
    """Resolve a reference PNG path for a scene using strict naming conventions.

    Expected names (PNG):
    - Cycles: {scene}_Cycles_{device}_ref.png or {scene}_Cycles_ref.png
    - Eevee:  {scene}_Eevee_ref.png or {scene}_Eevee.png
    Returns full path or None.
    """
    scene_name = os.path.splitext(os.path.basename(scene_path))[0]
    if engine == "CYCLES":
        candidates = [
            f"{scene_name}_Cycles_{device}_ref.png",
            f"{scene_name}_Cycles_ref.png",
        ]
    elif engine == "BLENDER_EEVEE":
        candidates = [
            f"{scene_name}_Eevee_ref.png",
            f"{scene_name}_Eevee.png",
        ]
    else:
        return None

    for fname in candidates:
        p = os.path.join(ref_dir, fname)
        if os.path.isfile(p):
            return p
    return None


def append_csv(row, engine, device, samples, date_str):
    """
    Append row to CSV file matching JSON base name: output/results/{date}_{engine}_{device}_{samples}.csv.
    """
    filename = f"output/results/{date_str}_{engine}_{device}_{samples}.csv"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    file_exists = os.path.isfile(filename)

    with open(filename, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def plot_metric(values, name, ylabel):
    plt.figure(figsize=(7, 5))
    plt.plot(values, marker="o")
    plt.title(ylabel)
    plt.xlabel("Test index")
    plt.ylabel(ylabel)
    plt.grid(True)
    plt.savefig(f"output/plots/{name}.png")
    plt.close()


def _run_benchmark_base(
    blender_path,
    engine,
    device,
    samples,
    scene_path,
    reference_image,
    iteration,
    extra_cmd_args=None,
    output_device=None,
    store_results=True,
):
    """Base benchmark function. """
    if extra_cmd_args is None:
        extra_cmd_args = []
    if output_device is None:
        output_device = device

    ensure_dirs()

    # Generate output filename based on parameters
    scene_name = os.path.splitext(os.path.basename(scene_path))[0]
    output_filename = f"{scene_name}_{engine}_{output_device}_{samples}_{iteration}.png"
    output_path = os.path.join("output/renders", output_filename)
    output_path = os.path.abspath(output_path)

    print(f"\n=== {engine} Benchmark start ===")
    print(f"Engine: {engine}")
    if engine == "CYCLES":
        print(f"Device: {device}")
    print(f"Samples: {samples}")
    print(f"Scene: {scene_path}")
    print(f"Reference: {reference_image}")
    print(f"Output: {output_path}")

    cmd = [
        blender_path,
        "-b", scene_path
    ]

    script_name = "blender_cycles_render.py" if engine == "CYCLES" else "blender_eevee_render.py"
    script_path = os.path.join(os.path.dirname(__file__), "src", "blender_benchmark", "blender_scripts", script_name)
    full_cmd = cmd + ["--python", script_path, "--", str(samples), output_path] + extra_cmd_args

    print(f"Running command: {' '.join(full_cmd)}")
    print("\n--- Blender Output ---")

    blender_proc = subprocess.Popen(full_cmd)
    sys_monitor = SystemMonitor(pid=blender_proc.pid)
    vram_monitor = VRAMMonitor()

    sys_monitor.start()
    vram_monitor.start()

    start_time = time.time()
    blender_proc.wait()
    end_time = time.time()
    print("--- End Blender Output ---\n")

    # --- Stop monitors ---
    sys_monitor.stop()
    vram_monitor.stop()

    # --- Metrics ---
    render_time = end_time - start_time
    sys_metrics = sys_monitor.get_metrics()
    vram_max = vram_monitor.get_max_vram()
    
    # Path to rendered image
    rendered_image = output_path

    # --- Quality metrics ---
    psnr_value = None
    ssim_value = None

    if not reference_image:
        device_ref = device
        if(device_ref != "CPU"):
            device_ref = "GPU"

        reference_image = resolve_reference_path(scene_path, engine, device_ref)

    if reference_image:
        if not os.path.isfile(reference_image):
            print(f"Warning: reference image not found: {reference_image}")
        else:
            psnr_value = compute_psnr(rendered_image, reference_image)
            ssim_value = compute_ssim(rendered_image, reference_image)

    # --- Metrics collection ---
    # Compute cpu_intensity using actual wall-clock render_time (per thesis definition)
    cpu_time_sec = sys_metrics.get("cpu_time_sec", 0)
    cpu_intensity = (cpu_time_sec / render_time) if render_time > 0 else 0

    # System overhead (normalized per logical CPU):
    # Use CPU-seconds per logical CPU: TCPU_per_core = TCPU / cpu_count
    # Then system_overhead = Treal - TCPU_per_core
    try:
        cpu_count = psutil.cpu_count(logical=True) or 1
    except Exception:
        cpu_count = 1

    tcpu_per_core = (cpu_time_sec / cpu_count) if cpu_count > 0 else cpu_time_sec
    system_overhead_sec = max(0.0, render_time - tcpu_per_core)
    system_overhead_percent = (system_overhead_sec / render_time * 100) if render_time > 0 else 0

    results = {
        "iteration": iteration,
        "render_engine": engine,
        "device": device,
        "samples": samples if samples else "default",
        "scene": os.path.basename(scene_path),
        "render_time_sec": round(render_time, 2),
        "cpu_intensity": round(cpu_intensity, 3),
        "system_overhead_sec": round(system_overhead_sec, 3),
        "system_overhead_percent": round(system_overhead_percent, 2),
        "gpu_avg_percent": round(sys_metrics.get("gpu_avg_percent", 0), 2),
        "vram_max_mb": round(vram_max, 2),
        "ram_max_mb": round(sys_metrics.get("ram_max_mb", 0), 2),
        "psnr": round(psnr_value, 4) if psnr_value is not None else None,
        "ssim": round(ssim_value, 4) if ssim_value is not None else None,
    }

    print(json.dumps(results, indent=4))

    if store_results:
        # --- JSON save ---
        current_date = datetime.now().strftime("%Y%m%d")

        results_filename = f"output/results/{current_date}_{engine}_{output_device}_{samples}_{iteration}.json"
        os.makedirs(os.path.dirname(results_filename), exist_ok=True)
        with open(results_filename, "w") as f:
            json.dump(results, f, indent=4)

        # --- CSV save (per-config file, no iteration suffix)
        append_csv(results, engine=engine, device=output_device, samples=samples, date_str=current_date)
    else:
        print("Warmup run: skipping persistence of benchmark results.")

    print(f"=== {engine} Benchmark finished ===")
    return results


def run_cycles_benchmark(
    blender_path,
    scene_path,
    device="CPU",
    samples=32,
    reference_image=None,
    iteration=1,
    store_results=True,
):
    extra_cmd_args = ["--cycles-device", device]
    return _run_benchmark_base(
        blender_path=blender_path,
        engine="CYCLES",
        device=device,
        samples=samples,
        scene_path=scene_path,
        reference_image=reference_image,
        iteration=iteration,
        extra_cmd_args=extra_cmd_args,
        store_results=store_results,
    )


def run_eevee_benchmark(
    blender_path,
    scene_path,
    samples=32,
    reference_image=None,
    iteration=1,
    profile="MEDIUM",
    store_results=True,
):
    extra_cmd_args = [
        "--profile", profile
    ]

    return _run_benchmark_base(
        blender_path=blender_path,
        engine="BLENDER_EEVEE",
        device="GPU",
        samples=samples,
        scene_path=scene_path,
        reference_image=reference_image,
        iteration=iteration,
        extra_cmd_args=extra_cmd_args,
        store_results=store_results,
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Blender Benchmark Tool")
    
    parser.add_argument("--blender-path", 
                        default="/home/User/Blender/blender-5.0.0-linux-x64/blender",
                        help="Path to Blender executable")
    
    parser.add_argument("--scene", required=True,
                        help="Path to .blend file")
    
    parser.add_argument("--engine", 
                        choices=["CYCLES", "BLENDER_EEVEE"],
                        default="CYCLES",
                        help="Render engine (CYCLES or BLENDER_EEVEE)")
    
    parser.add_argument("--device",
                        choices=["CPU", "CUDA", "OPTIX", "OPENCL"],
                        default="CPU",
                        help="Render device (only for Cycles)")
    
    parser.add_argument("--samples", type=int,
                        help="Number of samples (e.g. 64, 256, 512)")
    
    parser.add_argument("--reference",
                        help="Path to reference PNG image for quality comparison")
    
    parser.add_argument("--profile",
                        choices=["LOW", "MEDIUM", "HIGH"],
                        default="MEDIUM",
                        help="Eevee quality profile")
    
    args = parser.parse_args()
    
    if args.engine == "CYCLES":
        run_cycles_benchmark(
            blender_path=args.blender_path,
            scene_path=args.scene,
            device=args.device,
            samples=args.samples,
            reference_image=args.reference
        )
    elif args.engine == "BLENDER_EEVEE":
        run_eevee_benchmark(
            blender_path=args.blender_path,
            scene_path=args.scene,
            samples=args.samples,
            reference_image=args.reference,
            profile=args.profile
        )