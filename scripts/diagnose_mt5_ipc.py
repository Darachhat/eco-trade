"""
diagnose_mt5_ipc.py
───────────────────
Phase 5 & 6 Isolated MT5 IPC Diagnostic Test for Linux Wine Environment.
Runs under Windows Python 3.9 in Wine to isolate:
  1. Python -> MT5 IPC connection (without credentials)
  2. MT5 -> Broker connection & authentication (separate step)
  3. Symbol resolution & tick availability
  4. Repeated initialize / shutdown stability

DO NOT modify trading strategies in this file. This is strictly diagnostic.
"""

import os
import sys
import time

def log(tag: str, msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] [{tag}] {msg}")

def main():
    print("=" * 70)
    log("DIAG", "EcoTrade MT5 Isolated Diagnostic Starting...")
    print("=" * 70)

    # 1. Environment and Interpreter check
    log("ENV", f"Python executable: {sys.executable}")
    log("ENV", f"Python version: {sys.version}")
    log("ENV", f"Platform: {sys.platform}")
    log("ENV", f"DISPLAY: {os.environ.get('DISPLAY', 'NOT_SET')}")
    log("ENV", f"WINEPREFIX: {os.environ.get('WINEPREFIX', 'NOT_SET')}")

    # 2. Import MetaTrader5
    try:
        import MetaTrader5 as mt5
        log("IMPORT", f"MetaTrader5 package imported successfully from: {mt5.__file__}")
        log("IMPORT", f"MetaTrader5 version info: {mt5.version()}")
    except ImportError as e:
        log("FATAL", f"Could not import MetaTrader5 package: {e}")
        sys.exit(1)

    # Candidate paths for terminal64.exe
    candidate_paths = [
        r"C:\Program Files\MetaTrader 5\terminal64.exe",
        r"C:\Program Files\Exness MetaTrader 5 Terminal\terminal64.exe",
        r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
        r"C:\MetaTrader 5\terminal64.exe",
        r"C:\MT5\terminal64.exe",
    ]
    terminal_path = None
    for p in candidate_paths:
        if os.path.exists(p):
            terminal_path = p
            break
    log("BINARY", f"Discovered terminal path: {terminal_path} (exists={terminal_path is not None})")

    # ── TEST 1: Initialize without path (Attach mode) ──────────────────────────
    print("-" * 70)
    log("TEST-1A", "Testing mt5.initialize(portable=False, timeout=10000)...")
    init_1a = mt5.initialize(portable=False, timeout=10000)
    log("TEST-1A", f"Result: {init_1a} | last_error: {mt5.last_error()}")

    init_ok = init_1a
    if not init_ok:
        log("TEST-1B", "Testing mt5.initialize(portable=True, timeout=10000)...")
        init_1b = mt5.initialize(portable=True, timeout=10000)
        log("TEST-1B", f"Result: {init_1b} | last_error: {mt5.last_error()}")
        init_ok = init_1b

    # ── TEST 2: Initialize with explicit path ──────────────────────────────────
    if not init_ok and terminal_path:
        print("-" * 70)
        log("TEST-2A", f"Testing mt5.initialize(path='{terminal_path}', portable=False, timeout=30000)...")
        init_2a = mt5.initialize(path=terminal_path, portable=False, timeout=30000)
        log("TEST-2A", f"Result: {init_2a} | last_error: {mt5.last_error()}")
        init_ok = init_2a

        if not init_ok:
            log("TEST-2B", f"Testing mt5.initialize(path='{terminal_path}', portable=True, timeout=30000)...")
            init_2b = mt5.initialize(path=terminal_path, portable=True, timeout=30000)
            log("TEST-2B", f"Result: {init_2b} | last_error: {mt5.last_error()}")
            init_ok = init_2b

    if not init_ok:
        print("=" * 70)
        log("RESULT", ">>> IPC FAILURE ON ALL MODES <<<")
        log("RESULT", "Python could NOT establish IPC communication with MT5 terminal in any mode.")
        log("RESULT", "Checking if terminal is blocked or multiple processes are clashing.")
        print("=" * 70)
        sys.exit(2)

    # ── TEST 3: Inspect Terminal Info ──────────────────────────────────────────
    print("-" * 70)
    log("TEST-3", "Inspecting mt5.terminal_info()...")
    term_info = mt5.terminal_info()
    if term_info:
        log("TEST-3", f"Connected to terminal successfully!")
        log("TEST-3", f"  Community account: {term_info.community_account}")
        log("TEST-3", f"  Connected: {term_info.connected}")
        log("TEST-3", f"  DLL allowed: {term_info.dlls_allowed}")
        log("TEST-3", f"  Trade allowed: {term_info.trade_allowed}")
        log("TEST-3", f"  Trade API disabled: {term_info.tradeapi_disabled}")
        log("TEST-3", f"  Path: {term_info.path}")
        log("TEST-3", f"  Data path: {term_info.data_path}")
    else:
        log("TEST-3", f"terminal_info() returned None! last_error: {mt5.last_error()}")

    # ── TEST 4: Login / Authentication to Broker ──────────────────────────────
    print("-" * 70)
    login_id = int(os.environ.get("MT5_LOGIN", 463894594))
    password = os.environ.get("MT5_PASSWORD", "cHhat#2023")
    server = os.environ.get("MT5_SERVER", "Exness-MT5Trial17")

    log("TEST-4", f"Attempting mt5.login({login_id}, server='{server}')...")
    login_ok = mt5.login(login=login_id, password=password, server=server, timeout=15000)
    last_err_login = mt5.last_error()
    log("TEST-4", f"Login result: {login_ok} | last_error: {last_err_login}")

    # ── TEST 5: Inspect Account Info ──────────────────────────────────────────
    print("-" * 70)
    log("TEST-5", "Inspecting mt5.account_info()...")
    acc = mt5.account_info()
    if acc:
        log("TEST-5", f"Account Info Valid:")
        log("TEST-5", f"  Login: {acc.login}")
        log("TEST-5", f"  Server: {acc.server}")
        log("TEST-5", f"  Company: {acc.company}")
        log("TEST-5", f"  Balance: ${acc.balance:.2f}")
        log("TEST-5", f"  Equity: ${acc.equity:.2f}")
        log("TEST-5", f"  Leverage: 1:{acc.leverage}")
        log("TEST-5", f"  Trade allowed: {acc.trade_allowed}")
        log("TEST-5", f"  Trade expert: {acc.trade_expert}")
    else:
        log("TEST-5", f"account_info() returned None! (Login failed or not logged in)")

    # ── TEST 6: Inspect Symbol and Ticks ───────────────────────────────────────
    print("-" * 70)
    target_symbol = os.environ.get("SCALPER_SYMBOL", "XAUUSDm")
    log("TEST-6", f"Testing symbol selection and ticks for: {target_symbol}...")
    selected = mt5.symbol_select(target_symbol, True)
    log("TEST-6", f"symbol_select('{target_symbol}', True) = {selected}")

    sym_info = mt5.symbol_info(target_symbol)
    if sym_info:
        log("TEST-6", f"Symbol Info Valid:")
        log("TEST-6", f"  Visible: {sym_info.visible}")
        log("TEST-6", f"  Point: {sym_info.point}")
        log("TEST-6", f"  Digits: {sym_info.digits}")
        log("TEST-6", f"  Spread: {sym_info.spread}")
        log("TEST-6", f"  Trade mode: {sym_info.trade_mode}")
    else:
        log("TEST-6", f"symbol_info('{target_symbol}') returned None! last_error: {mt5.last_error()}")

    tick = mt5.symbol_info_tick(target_symbol)
    if tick:
        log("TEST-6", f"Tick Data Valid:")
        log("TEST-6", f"  Bid: {tick.bid} | Ask: {tick.ask} | Spread pts: {(tick.ask - tick.bid) / (sym_info.point if sym_info else 0.001):.1f}")
    else:
        log("TEST-6", f"symbol_info_tick('{target_symbol}') returned None! (Market closed or symbol unselected)")

    # ── TEST 7: Clean Shutdown & Repeated Lifecycle Test ──────────────────────
    print("-" * 70)
    log("TEST-7", "Testing mt5.shutdown() and re-initialization lifecycle...")
    mt5.shutdown()
    log("TEST-7", "Shutdown called. Waiting 2 seconds...")
    time.sleep(2)
    re_init = mt5.initialize(timeout=10000)
    log("TEST-7", f"Re-initialize result: {re_init} (last_error: {mt5.last_error()})")
    mt5.shutdown()
    log("TEST-7", "Final shutdown complete.")

    print("=" * 70)
    log("SUMMARY", "Diagnostic completed.")
    print("=" * 70)

if __name__ == "__main__":
    main()
