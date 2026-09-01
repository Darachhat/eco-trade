#!/usr/bin/env bash
# ==============================================================================
# setup_mt5_linux.sh
# ──────────────────
# Automated Headless MetaTrader 5 + Wine Setup for Linux VPS (Ubuntu/Debian)
# Runs Exness MT5 24/7 directly on Linux without needing a Windows PC!
# ==============================================================================

set -e

echo "========================================================"
echo " 🚀 Setting up Headless MetaTrader 5 on Linux VPS"
echo "========================================================"

# 1. Update and install Wine + Xvfb (Virtual Framebuffer)
echo "[1/4] Installing Wine, Xvfb, and dependencies..."
sudo dpkg --add-architecture i386 || true
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
    wine64 \
    wine32 \
    xvfb \
    winetricks \
    curl \
    wget \
    python3 \
    python3-pip \
    ca-certificates

# 2. Configure Virtual Display
echo "[2/4] Initializing virtual display buffer (Xvfb :99)..."
export DISPLAY=:99
if ! pgrep -x "Xvfb" > /dev/null; then
    Xvfb :99 -screen 0 1024x768x16 -nolisten tcp &
    sleep 2
    echo "✓ Xvfb virtual display started on :99"
else
    echo "✓ Xvfb is already running."
fi

# 3. Setup Python inside Wine environment
echo "[3/4] Setting up Windows Python inside Wine..."
WINEPREFIX="$HOME/.wine"
export WINEPREFIX

if [ ! -d "$WINEPREFIX/drive_c/Python311" ]; then
    echo "Downloading and installing Python 3.11 for Windows under Wine..."
    wget -q -O /tmp/python-3.11.9-amd64.exe https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
    wine /tmp/python-3.11.9-amd64.exe /quiet InstallAllUsers=1 PrependPath=1 TargetDir="C:\\Python311"
    sleep 5
    echo "✓ Windows Python installed under Wine"
fi

# 4. Install MetaTrader5 library & requirements inside Wine
echo "[4/4] Installing MetaTrader5 library and requirements..."
wine "C:\\Python311\\python.exe" -m pip install --upgrade pip
wine "C:\\Python311\\python.exe" -m pip install MetaTrader5 pydantic requests

echo "========================================================"
echo " ✅ Linux MT5 Environment Ready!"
echo "========================================================"
echo ""
echo "To run the 24/7 Gold Scalper forever on this VM, run:"
echo "  DISPLAY=:99 wine 'C:\\Python311\\python.exe' run_scalper.py --symbol XAUUSDm --tp 2.0 --sl 10.0"
echo ""
echo "Or run in background with nohup:"
echo "  nohup env DISPLAY=:99 wine 'C:\\Python311\\python.exe' run_scalper.py > scalper_vm.log 2>&1 &"
echo "========================================================"
