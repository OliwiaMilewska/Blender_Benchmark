# benchmark.py
import subprocess
import time
import json
import os
import csv
import argparse
import matplotlib.pyplot as plt
from datetime import datetime

from monitor_system import SystemMonitor
from monitor_vram import VRAMMonitor
from quality_metrics import compute_psnr, compute_ssim


def ensure_dirs():
    os.makedirs("output/results", exist_ok=True)
    os.makedirs("output/plots", exist_ok=True)
    os.makedirs("data/renders", exist_ok=True)
    os.makedirs("results", exist_ok=True)


def append_csv(row, filename="output/results/results.csv"):
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


def run_benchmark(
    blender_path,
    scene_path,
    engine="CYCLES",
    device="CPU",
    samples=32,
    frame=1,
    reference_image=None,
):

    ensure_dirs()

    # Generate output filename based on parameters
    scene_name = os.path.splitext(os.path.basename(scene_path))[0]
    samples_str = str(samples) if samples else "default"
    output_filename = f"{scene_name}_{engine}_{device}_{samples_str}.png"
    output_path = os.path.join("data/renders", output_filename)
    output_path = os.path.abspath(output_path)

    print("\n=== Benchmark start ===")
    print(f"Engine: {engine}")
    print(f"Device: {device}")
    print(f"Samples: {samples if samples else 'default'}")
    print(f"Scene: {scene_path}")
    print(f"Reference: {reference_image if reference_image else 'None'}")
    print(f"Output: {output_path}")

    # --- Start monitors ---
    sys_monitor = SystemMonitor(process_name="blender")
    vram_monitor = VRAMMonitor()

    sys_monitor.start()
    vram_monitor.start()

    # --- Rendering command ---
    cmd = [
        blender_path,
        "-b", scene_path
    ]
    
    # Use appropriate render script for the engine
    if engine == "CYCLES":
        script_path = os.path.join(os.path.dirname(__file__), "src", "blender_benchmark", "blender_scripts", "blender_cycles_render.py")
        cmd.extend(["--python", script_path, "--", str(samples), output_path, "--cycles-device", device])
    elif engine == "EEVEE":
        script_path = os.path.join(os.path.dirname(__file__), "src", "blender_benchmark", "blender_scripts", "blender_eevee_render.py")
        cmd.extend(["--python", script_path, "--", str(samples), output_path])

    print(f"Running command: {' '.join(cmd)}")
    print("\n--- Blender Output ---")
    start_time = time.time()
    subprocess.run(cmd)
    end_time = time.time()
    print("--- End Blender Output ---\n")

    # --- Stop monitors ---
    sys_monitor.stop()
    vram_monitor.stop()

    # --- Metrics ---
    render_time = end_time - start_time
    sys_metrics = sys_monitor.get_metrics()
    vram_max = vram_monitor.get_max_vram()
    
    # Path to rendered image (already saved as full name)
    rendered_image = output_path

    # --- Quality metrics ---
    psnr_value = None
    ssim_value = None
    if reference_image:
        psnr_value = compute_psnr(rendered_image, reference_image)
        ssim_value = compute_ssim(rendered_image, reference_image)
        print(f"Quality metrics: PSNR={psnr_value:.2f}, SSIM={ssim_value:.4f}")

    # --- Metrics collection ---
    results = {
        "render_engine": engine,
        "device": device,
        "samples": samples if samples else "default",
        "scene": os.path.basename(scene_path),
        "render_time_sec": render_time,
        "cpu_time_sec": sys_metrics["cpu_time_sec"],
        "cpu_intensity": sys_metrics["cpu_intensity"],
        "cpu_noise_std": sys_metrics["cpu_noise_std"],
        "gpu_avg_percent": sys_metrics["gpu_avg_percent"],
        "ram_max_mb": sys_metrics["ram_max_mb"],
        "vram_max_mb": vram_max,
        "psnr": psnr_value,
        "ssim": ssim_value
    }

    print(json.dumps(results, indent=4))

    # --- JSON save ---
    current_date = datetime.now().strftime("%Y%m%d")
    results_filename = f"results/_{current_date}_{engine}_{device}_{samples if samples else 'default'}.json"
    with open(results_filename, "w") as f:
        json.dump(results, f, indent=4)

    # --- CSV save ---
    append_csv(results)

    print("=== Benchmark finished ===")
    return results


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
    
    parser.add_argument("--frame", type=int, default=1,
                        help="Frame number to render")
    
    args = parser.parse_args()
    
    run_benchmark(
        blender_path=args.blender_path,
        scene_path=args.scene,
        engine=args.engine,
        device=args.device,
        samples=args.samples,
        frame=args.frame,
        reference_image=args.reference
    )