import psutil
import time
import threading
import pynvml


class SystemMonitor:
    def __init__(self, process_name="blender", pid=None, interval=0.2):
        self.process_name = process_name.lower() if process_name else None
        self.pid = pid
        self.interval = interval
        self.running = False

        self.cpu_util_samples = []   # CPU utilization [%]
        self.cpu_time_samples = []   # CPU time [sec]
        self.ram_samples = []        # RAM usage [MB]
        self.gpu_samples = []        # GPU load [%]
        self._cpu_initialized = False

        self.gpu_supported = False
        try:
            pynvml.nvmlInit()
            self.handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            name = pynvml.nvmlDeviceGetName(self.handle)
            self.gpu_supported = True
            print("GPU monitoring: enabled, detected:", name)
        except Exception as e:
            print(f"GPU monitoring: disabled ({e})")
            self.handle = None

    def _find_process(self):
        if self.pid is not None:
            try:
                proc = psutil.Process(self.pid)
                return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return None

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
                    # Ensure we initialize cpu_percent sampling for this process
                    # to avoid the first bogus value returned by psutil.
                    if not self._cpu_initialized:
                        try:
                            proc.cpu_percent(interval=None)
                        except Exception:
                            pass
                        self._cpu_initialized = True
                    cpu_percent = proc.cpu_percent(interval=None)
                    self.cpu_util_samples.append(cpu_percent)

                    # --- RAM ---
                    mem = proc.memory_info().rss / (1024 ** 2)
                    self.ram_samples.append(mem)

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    proc = None

            # --- GPU UTIL (NVML) ---
            if self.gpu_supported and self.handle:
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
                "gpu_avg_percent": 0,
                "ram_max_mb": 0
            }

        # --- total CPU time of process ---
        cpu_time_sec = max(self.cpu_time_samples) - min(self.cpu_time_samples)

        # --- render time approximated by number of samples ---
        render_duration = len(self.cpu_time_samples) * self.interval

        # --- CPU intensity ---
        cpu_intensity = cpu_time_sec / render_duration if render_duration > 0 else 0

        # We no longer compute CPU noise std; keep only time/intensity info.

        return {
            "cpu_time_sec": cpu_time_sec,
            "cpu_intensity": cpu_intensity,
            "gpu_avg_percent": sum(self.gpu_samples) / len(self.gpu_samples) if self.gpu_samples else 0,
            "ram_max_mb": max(self.ram_samples) if self.ram_samples else 0
        }