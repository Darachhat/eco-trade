#!/usr/bin/env bash
# ==============================================================================
# inspect_vps_env.sh
# ──────────────────
# Phase 1-4 Complete VPS Inspection for EcoTrade MT5 Environment.
# Gathers environment state, active processes, display state, Wine prefix,
# Python installation, port 8008 ownership, and X11 window hierarchy.
# ==============================================================================

set -u

echo "================================================================="
echo " [PHASE 1-4] ECOTRADE VPS MT5 RUNTIME ENVIRONMENT INSPECTION"
echo " Date: $(date -u)"
echo " Host: $(hostname) | Kernel: $(uname -r)"
echo "================================================================="

echo ""
echo "─── [1] SYSTEMD SERVICE INSPECTION ───"
if systemctl is-active --quiet ecotrade-scalper 2>/dev/null; then
    echo "Service ecotrade-scalper: ACTIVE"
else
    echo "Service ecotrade-scalper: INACTIVE / FAILED"
fi
echo ">>> systemctl cat ecotrade-scalper:"
systemctl cat ecotrade-scalper 2>&1 || echo "Unit file not found"
echo ">>> Recent service journal (last 20 lines):"
journalctl -u ecotrade-scalper -n 20 --no-pager 2>&1 || true

echo ""
echo "─── [2] WINE INSTALLATION & PATHS ───"
echo "which wine:   $(which wine 2>/dev/null || echo 'NOT FOUND')"
echo "which wine64: $(which wine64 2>/dev/null || echo 'NOT FOUND')"
wine --version 2>&1 || echo "wine --version failed"
wine64 --version 2>&1 || echo "wine64 --version failed"
echo "WINEPREFIX environment variable: ${WINEPREFIX:-'NOT SET (defaults to ~/.wine)'}"

echo ""
echo "─── [3] XVFB VIRTUAL DISPLAY INSPECTION ───"
echo ">>> Xvfb processes:"
pgrep -af "Xvfb" || echo "No Xvfb processes running"
echo ">>> Display :99 check:"
if command -v xdpyinfo >/dev/null 2>&1; then
    DISPLAY=:99 xdpyinfo -ext XTEST >/dev/null 2>&1 && echo "Display :99 is ACCESSIBLE" || echo "Display :99 is NOT ACCESSIBLE"
else
    echo "xdpyinfo not installed"
fi
echo ">>> Active windows on Display :99:"
if command -v xwininfo >/dev/null 2>&1; then
    DISPLAY=:99 xwininfo -root -tree 2>&1 | head -n 30 || echo "Could not inspect windows"
else
    echo "xwininfo not installed"
fi

echo ""
echo "─── [4] METATRADER 5 BINARIES & RUNNING PROCESSES ───"
echo ">>> Search for terminal binaries in /root/.wine:"
find /root/.wine -maxdepth 6 \( -iname "terminal64.exe" -o -iname "terminal.exe" \) 2>/dev/null || echo "No terminals found"
echo ">>> Currently running MT5 / Wine processes:"
pgrep -af "terminal64.exe|terminal.exe|wineserver|wine" || echo "No Wine/MT5 processes active"

echo ""
echo "─── [5] WINDOWS PYTHON 3.9 & METATRADER5 PACKAGE INSPECTION ───"
if [ -f "/root/.wine/drive_c/Python39/python.exe" ]; then
    echo "Windows Python 3.9 binary found at: /root/.wine/drive_c/Python39/python.exe"
    DISPLAY=:99 WINEPREFIX=/root/.wine wine "C:\\Python39\\python.exe" --version 2>&1 || true
    echo ">>> Testing MetaTrader5 package import:"
    DISPLAY=:99 WINEPREFIX=/root/.wine wine "C:\\Python39\\python.exe" -c \
        "import MetaTrader5 as mt5; print('MetaTrader5 package version:', mt5.__version__, 'from', mt5.__file__)" 2>&1 || true
else
    echo "WARNING: /root/.wine/drive_c/Python39/python.exe does NOT exist!"
fi

echo ""
echo "─── [6] PORT 8008 OWNERSHIP & NETWORK BINDINGS ───"
echo ">>> Listening sockets on 8008:"
if command -v ss >/dev/null 2>&1; then
    ss -ltnp | grep ':8008' || echo "Port 8008 is currently FREE"
fi
if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:8008 -sTCP:LISTEN -n -P || true
fi

echo ""
echo "================================================================="
echo " [PHASE 1-4] INSPECTION COMPLETE"
echo "================================================================="
