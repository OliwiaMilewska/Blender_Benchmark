import pynvml
import threading
import time


class VRAMMonitor:
    def __init__(self, pid=None, gpu_index=0, interval=0.2):
        self.pid = pid
        self.interval = interval
        self.running = False
        self.max_vram_mb = 0
        self.gpu_supported = False

        try:
            pynvml.nvmlInit()
            self.handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)
            self.gpu_supported = True
        except Exception as e:
            self.handle = None
            print(f"GPU VRAM monitoring: disabled ({e})")

    def _get_blender_vram_mb(self):
        if not self.gpu_supported or not self.handle:
            return 0

        if self.pid is not None:
            for get_proc in (
                pynvml.nvmlDeviceGetGraphicsRunningProcesses,
                pynvml.nvmlDeviceGetComputeRunningProcesses,
            ):
                try:
                    processes = get_proc(self.handle)
                except Exception:
                    continue

                for proc in processes:
                    if getattr(proc, "pid", None) == self.pid:
                        used = getattr(proc, "usedGpuMemory", None)
                        if used is not None:
                            return used / (1024 ** 2)

        try:
            mem = pynvml.nvmlDeviceGetMemoryInfo(self.handle)
            return mem.used / (1024 ** 2)
        except Exception:
            return 0

    def _collect(self):
        while self.running:
            used_mb = self._get_blender_vram_mb()
            self.max_vram_mb = max(self.max_vram_mb, used_mb)
            time.sleep(self.interval)

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._collect)
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()

    def get_max_vram(self):
        return self.max_vram_mb