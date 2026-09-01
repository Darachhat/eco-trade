"""
run_scalper.py
──────────────
Standalone 24/7 High-Frequency Scalper Runner for Exness MetaTrader 5.
Runs indefinitely with auto-reconnect, error resilience, and graceful shutdown.

Usage:
  python run_scalper.py
  python run_scalper.py --symbol XAUUSDm --tp 2.0 --sl 10.0 --risk 0.5
"""

import argparse
import logging
import os
import signal
import sys
import time
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.services.mt5_scalper import mt5_scalper
from app.services.mt5_service import mt5_service

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scalper_24_7.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("EcoTradeScalper247")

_SHUTDOWN_REQUESTED = False


def signal_handler(signum, frame):
    global _SHUTDOWN_REQUESTED
    logger.info("Received termination signal (%s). Initiating clean shutdown...", signum)
    _SHUTDOWN_REQUESTED = True


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def main():
    parser = argparse.ArgumentParser(description="24/7 EcoTrade MT5 High-Frequency Scalper")
    parser.add_argument("--login", type=int, default=463894594, help="MT5 Account Login ID")
    parser.add_argument("--password", type=str, default="cHhat#2023", help="MT5 Trading Password")
    parser.add_argument("--server", type=str, default="Exness-MT5Trial17", help="MT5 Broker Server")
    parser.add_argument("--symbol", type=str, default="XAUUSDm", help="Target Symbol (e.g. XAUUSDm, BTCUSDm)")
    parser.add_argument("--tp", type=float, default=2.00, help="Fixed TP Distance in Dollars (Default: $2.00)")
    parser.add_argument("--sl", type=float, default=10.00, help="Fixed SL Distance in Dollars (Default: $10.00)")
    parser.add_argument("--risk", type=float, default=0.50, help="Risk Per Trade Pct (Default: 0.50%%)")
    args = parser.parse_args()

    print("=" * 65)
    print(" 🚀 ECOTRADE MT5 24/7 HIGH-FREQUENCY SCALPER ENGINE")
    print("=" * 65)
    print(f" Account:  {args.login} ({args.server})")
    print(f" Target:   {args.symbol}")
    print(f" Targets:  Take Profit: +${args.tp:.2f} | Stop Loss: -${args.sl:.2f}")
    print(f" Risk:     {args.risk:.2f}% per trade | Dynamic Break-Even: +$1.00")
    print("=" * 65)

    # 1. Update Scalper Target Config
    mt5_scalper.config.symbol = args.symbol
    mt5_scalper.config.fixed_tp_dollars = args.tp
    mt5_scalper.config.fixed_sl_dollars = args.sl
    mt5_scalper.config.risk_per_trade_pct = args.risk

    # 2. Infinite Execution Loop with Auto-Reconnect
    reconnect_attempts = 0

    while not _SHUTDOWN_REQUESTED:
        try:
            # Verify MT5 Terminal connection
            if not mt5_service.is_connected:
                logger.info("Connecting to Exness MT5 Terminal...")
                connected = mt5_service.initialize_and_login(
                    login=args.login,
                    password=args.password,
                    server=args.server,
                )
                if not connected:
                    reconnect_attempts += 1
                    wait_sec = min(30, 5 * reconnect_attempts)
                    logger.warning("MT5 Login failed. Retrying in %ds (Attempt %d)...", wait_sec, reconnect_attempts)
                    time.sleep(wait_sec)
                    continue

                reconnect_attempts = 0
                acc = mt5_service.get_account_status()
                logger.info(
                    "Connected to Exness MT5! Balance: $%.2f | Equity: $%.2f | Leverage: 1:%d",
                    acc.get("balance", 0.0),
                    acc.get("equity", 0.0),
                    acc.get("leverage", 2000),
                )

            # Ensure autonomous loop is running
            if not mt5_scalper.is_running:
                logger.info("Starting Scalper Tick Loop on %s...", args.symbol)
                mt5_scalper.start()

            # Heartbeat print every 10 seconds
            time.sleep(10)
            t = mt5_scalper.telemetry
            open_pos = mt5_service.get_open_positions()
            logger.info(
                "⚡ [Heartbeat] %s | Bid: $%.2f | Spread: %.0f pts | ATR: %.0f pts | Signal: %s | Open: %d",
                t.symbol,
                t.current_bid,
                t.current_spread_points,
                t.current_atr_points,
                t.last_signal,
                len(open_pos),
            )

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received.")
            break
        except Exception as exc:
            logger.error("Unexpected error in main supervisor loop: %s. Continuing...", exc, exc_info=True)
            time.sleep(5)

    # 3. Clean Shutdown
    logger.info("Stopping Scalper Engine...")
    mt5_scalper.stop()
    logger.info("Scalper 24/7 Engine shut down cleanly.")


if __name__ == "__main__":
    main()
