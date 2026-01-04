import pynvml
import threading
import time


class VRAMMonitor:
    def __init__(self, gpu_index=0, interval=0.2):
        pynvml.nvmlInit()
        self.handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)
        self.interval = interval
        self.running = False
        self.max_vram_mb = 0

    def _collect(self):
        while self.running:
            mem = pynvml.nvmlDeviceGetMemoryInfo(self.handle)
            used_mb = mem.used / (1024 ** 2)
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
