#!/usr/bin/env bash
# ==============================================================================
# docker-entrypoint-scalper.sh
# ─────────────────────────────
# Starts a virtual display (Xvfb) then runs the Gold scalper under Wine Python.
# Restarts the scalper automatically if it crashes.
# ==============================================================================

set -e

SYMBOL="${SYMBOL:-XAUUSDm}"
TP="${TP:-2.0}"
SL="${SL:-100}"
RISK="${RISK:-0.5}"
LOGIN="${MT5_LOGIN:-463894594}"
PASSWORD="${MT5_PASSWORD:-cHhat#2023}"
SERVER="${MT5_SERVER:-Exness-MT5Trial17}"

# ── Start virtual framebuffer ────────────────────────────────────────────────
echo "[entrypoint] Starting Xvfb virtual display on :99 ..."
Xvfb :99 -screen 0 1024x768x16 -nolisten tcp &
XVFB_PID=$!
export DISPLAY=:99
sleep 2
echo "[entrypoint] Xvfb ready (PID $XVFB_PID)"

# ── Supervisor loop: restart on crash ────────────────────────────────────────
RESTART_DELAY=10
CRASH_COUNT=0

while true; do
    echo ""
    echo "============================================================"
    echo " [EcoTrade Scalper] Starting run #$((CRASH_COUNT + 1))"
    echo " Symbol: $SYMBOL | TP: \$$TP | SL: \$$SL | Risk: $RISK%"
    echo "============================================================"

    wine "C:\\Python39\\python.exe" /scalper/run_scalper.py \
        --symbol  "$SYMBOL" \
        --tp      "$TP" \
        --sl      "$SL" \
        --risk    "$RISK" \
        --login   "$LOGIN" \
        --password "$PASSWORD" \
        --server  "$SERVER" || true

    CRASH_COUNT=$((CRASH_COUNT + 1))
    echo "[entrypoint] Scalper exited (run #$CRASH_COUNT). Restarting in ${RESTART_DELAY}s ..."
    sleep "$RESTART_DELAY"
done
