#!/bin/bash

# ============================================
# Initial system setup for benchmarking
# Run ONCE, requires reboot after execution
# ============================================

set -e

echo "=== Updating system ==="
apt update
apt upgrade -y
apt autoremove -y
apt clean

echo "=== Disabling automatic updates ==="
systemctl disable apt-daily.service || true
systemctl disable apt-daily-upgrade.service || true
systemctl stop apt-daily.service || true
systemctl stop apt-daily-upgrade.service || true

echo "=== Disabling unnecessary services ==="
systemctl disable bluetooth.service 2>/dev/null || true
systemctl disable cups.service 2>/dev/null || true

echo "=== Disabling file indexing (Tracker) ==="
sudo -u $SUDO_USER tracker3 daemon stop 2>/dev/null || true
sudo -u $SUDO_USER systemctl --user mask tracker-miner-fs-3.service || true
sudo -u $SUDO_USER systemctl --user mask tracker-extract-3.service || true

echo "=== Setting permanent CPU governor configuration ==="
apt install -y cpufrequtils

echo 'GOVERNOR="performance"' | tee /etc/default/cpufrequtils
systemctl enable cpufrequtils

echo "=== Disabling power-profiles-daemon (if present) ==="
systemctl disable power-profiles-daemon 2>/dev/null || true

echo "=== Optimizing swap ==="
sysctl vm.swappiness=10
grep -q "vm.swappiness=10" /etc/sysctl.conf || echo "vm.swappiness=10" >> /etc/sysctl.conf

echo "=== Disabling sleep modes ==="
systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target

echo "=== Disabling GNOME animations ==="
sudo -u $SUDO_USER gsettings set org.gnome.desktop.interface enable-animations false || true

echo "=== Cleaning autostart applications ==="
AUTOSTART_DIR="/home/$SUDO_USER/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
rm -f "$AUTOSTART_DIR"/*

echo "=== Setup complete ==="
echo ">>> PLEASE REBOOT THE SYSTEM NOW <<<"