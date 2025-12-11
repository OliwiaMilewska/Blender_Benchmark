# benchmark.py
import subprocess
import time
import json
import os
import csv
import matplotlib.pyplot as plt

from monitor_system import SystemMonitor
from monitor_vram import VRAMMonitor
from quality_metrics import compute_psnr, compute_ssim


def ensure_dirs():
    os.makedirs("results", exist_ok=True)
    os.makedirs("plots", exist_ok=True)


def append_csv(row, filename="results/results.csv"):
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
    plt.savefig(f"plots/{name}.png")
    plt.close()


def run_benchmark(
    blender_path,
    scene_path,
    output_path,
    engine="CYCLES",
    frame=1,
    reference_image="reference.png",
    rendered_image="renders/frame_0001.png",
):

    ensure_dirs()

    print("\n=== Benchmark start ===")

    # --- Start monitorów ---
    sys_monitor = SystemMonitor(process_name="blender")
    vram_monitor = VRAMMonitor()

    sys_monitor.start()
    vram_monitor.start()

    # --- Komenda renderowania ---
    cmd = [
        blender_path,
        "-b", scene_path,
        "-o", output_path,
        "-E", engine,
        "-f", str(frame)
    ]

    start_time = time.time()
    subprocess.run(cmd)
    end_time = time.time()

    # --- Stop monitorów ---
    sys_monitor.stop()
    vram_monitor.stop()

    # --- Metryki ---
    render_time = end_time - start_time
    sys_metrics = sys_monitor.get_metrics()
    vram_max = vram_monitor.get_max_vram()

    # --- Metryki jakości ---
    try:
        psnr_value = compute_psnr(rendered_image, reference_image)
        ssim_value = compute_ssim(rendered_image, reference_image)
    except Exception as e:
        print("Błąd PSNR/SSIM:", e)
        psnr_value = None
        ssim_value = None

    # --- Zbiór metryk ---
    results = {
        "render_engine": engine,
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

    # --- Zapis JSON ---
    with open("results/last_results.json", "w") as f:
        json.dump(results, f, indent=4)

    # --- Zapis CSV ---
    append_csv(results)

    print("=== Benchmark finished ===")
    return results


if __name__ == "__main__":
    print("TEST")
    # run_benchmark(
    #     blender_path="/usr/bin/blender",
    #     scene_path="test.blend",
    #     output_path="renders/frame_",
    #     frame=1,
    #     engine="CYCLES"
    # )