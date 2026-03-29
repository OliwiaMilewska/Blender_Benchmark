#!/bin/bash

# ============================================
# Pre-test preparation script
# Run BEFORE EACH benchmark (after reboot)
# ============================================

set -e

echo "=== Setting CPU governor to performance ==="
cpufreq-set -r -g performance || true

echo "=== Verifying CPU governor ==="
cpufreq-info | grep "governor" || true

echo "=== Stopping Tracker (just in case) ==="
sudo -u $SUDO_USER tracker3 daemon stop 2>/dev/null || true

echo "=== Checking GPU status ==="
if command -v nvidia-smi &> /dev/null
then
    nvidia-smi
    echo "Ensure no unnecessary GPU processes are running."
else
    echo "No NVIDIA GPU detected."
fi

echo "=== Checking system load ==="
uptime

echo "=== Top processes (brief) ==="
ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -n 10

echo "=== Memory status ==="
free -h

echo "=== Pre-test preparation complete ==="
echo "You can now start Blender benchmark."