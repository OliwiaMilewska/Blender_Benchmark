import psutil
import time
import threading
import statistics
import pynvml


class SystemMonitor:
    def __init__(self, process_name="blender", interval=0.2):
        self.process_name = process_name.lower()
        self.interval = interval
        self.running = False

        self.cpu_util_samples = []   # utylizacja CPU [%]
        self.cpu_time_samples = []   # czas CPU [sek]
        self.ram_samples = []        # zużycie RAM [MB]
        self.gpu_samples = []        # obciążenie GPU [%]

        # Inicjalizacja NVML
        pynvml.nvmlInit()
        self.handle = pynvml.nvmlDeviceGetHandleByIndex(0)

    def _find_process(self):
        for p in psutil.process_iter(['name']):
            try:
                if p.info['name'] and self.process_name in p.info['name'].lower():
                    return p
            except psutil.NoSuchProcess:
                continue
        return None

    def _collect(self):
        proc = None

        while self.running:
            if proc is None:
                proc = self._find_process()

            if proc:
                try:
                    # --- CPU TIME ---
                    ctimes = proc.cpu_times()
                    cpu_time = ctimes.user + ctimes.system
                    self.cpu_time_samples.append(cpu_time)

                    # --- CPU UTIL ---
                    cpu_percent = proc.cpu_percent(interval=None)
                    self.cpu_util_samples.append(cpu_percent)

                    # --- RAM ---
                    mem = proc.memory_info().rss / (1024 ** 2)
                    self.ram_samples.append(mem)

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    proc = None

            # --- GPU UTIL (NVML) ---
            try:
                util = pynvml.nvmlDeviceGetUtilizationRates(self.handle)
                self.gpu_samples.append(util.gpu)
            except:
                pass

            time.sleep(self.interval)

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._collect)
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()

    def get_metrics(self):
        if len(self.cpu_time_samples) < 2:
            return {
                "cpu_time_sec": 0,
                "cpu_intensity": 0,
                "cpu_noise_std": 0,
                "gpu_avg_percent": 0,
                "ram_max_mb": 0
            }

        # --- całkowity czas CPU procesu ---
        cpu_time_sec = max(self.cpu_time_samples) - min(self.cpu_time_samples)

        # --- czas renderu aproksymowany liczbą próbek ---
        render_duration = len(self.cpu_time_samples) * self.interval

        # --- intensywność CPU ---
        cpu_intensity = cpu_time_sec / render_duration if render_duration > 0 else 0

        # --- odchylenie standardowe utylizacji CPU ---
        cpu_noise_std = statistics.stdev(self.cpu_util_samples) if len(self.cpu_util_samples) > 1 else 0

        return {
            "cpu_time_sec": cpu_time_sec,
            "cpu_intensity": cpu_intensity,
            "cpu_noise_std": cpu_noise_std,
            "gpu_avg_percent": sum(self.gpu_samples) / len(self.gpu_samples),
            "ram_max_mb": max(self.ram_samples) if self.ram_samples else 0
        }