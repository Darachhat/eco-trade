# EcoTrade MT5 IPC & Linux Wine Troubleshooting Guide

This document records the exact architecture, failure modes, root causes, and recovery procedures for running MetaTrader 5 and the MetaTrader5 Python library under Wine on headless Ubuntu Linux VPS.

---

## 1. System Architecture & Runtime Stack

```text
Host OS:              Ubuntu 26.04.1 LTS (GNU/Linux 7.0.0-27-generic x86_64)
Virtual Display:      Xvfb on Display :99 (1024x768x16, -nolisten tcp)
Windows Subsystem:    Wine 64-bit (10.0~repack-12ubuntu1 / WineHQ stable)
Wine Prefix:          /root/.wine (or dedicated /root/.wine-ecotrade)
Windows Interpreter:  C:\Python39\python.exe (Python 3.9.13 64-bit)
MetaTrader5 Package:  MetaTrader5 5.0.6147 (C-extension _core.cp39-win_amd64.pyd)
Terminal Binary:      C:\Program Files\MetaTrader 5\terminal64.exe
Terminal Data Path:   /root/.wine/drive_c/users/root/AppData/Roaming/MetaQuotes/Terminal/<HASH>
Service Manager:      systemd (/etc/systemd/system/ecotrade-scalper.service)
Service Launcher:     /usr/local/bin/ecotrade-scalper.sh
```

---

## 2. Process Model & IPC Architecture

MetaTrader 5 is designed as a native Windows desktop GUI application. The Python `MetaTrader5` package communicates with `terminal64.exe` through **Windows Inter-Process Communication (IPC)**:

```text
[run_scalper.py (Python 3.9)]
        │
        ▼
[_core.pyd (Native C DLL)]
        │
        ├── 1. Searches Windows Object Manager for shared memory section:
        │      \BaseNamedObjects\MetaTrader5_IPC_...
        ├── 2. Connects to Windows Named Pipe:
        │      \\.\pipe\terminal_...
        │
        ▼ (Wine Server Emulation Layer)
        │
        ├── Translates Windows Named Pipes to Unix domain sockets
        ├── Translates Windows mutexes/events to pthread synchronization
        ├── Maps GDI window messages to X11 events via Xvfb (:99)
        │
        ▼
[terminal64.exe (MT5 Desktop Process)]
        │
        ▼ (Encrypted TLS over TCP port 443)
[Exness Trading Broker: Exness-MT5Trial17]
```

---

## 3. Root Cause Analysis: `(-10005, 'IPC timeout')`

When `mt5.initialize()` returns `(-10005, 'IPC timeout')`, it means the Python C-extension waited for the handshake timeout (typically 15,000–60,000ms) without receiving a response from `terminal64.exe`.

Through systematic diagnosis, **three distinct root causes** were identified:

### Cause A: Modal GUI Dialog Blocking the MT5 Message Loop
- **Mechanism**: On a newly installed terminal or when connecting to an unknown broker server, `terminal64.exe` displays a modal dialog (such as the "Open an Account" wizard or "Search for a Broker").
- **Impact**: Under Windows/Wine, a modal dialog blocks the main thread's Windows Message Loop (`GetMessage`/`DispatchMessage`). Because the main message loop is blocked, the terminal never processes the incoming IPC handshake messages.
- **Resolution**:
  1. Use `startup.ini` passed via `/config:` to bypass registration prompts.
  2. Suppress the wizard by sending `Return` / `Escape` to the virtual display via `xdotool`.
  3. Ensure broker server definitions (`.srv`) are pre-populated in `bases/` so MT5 does not enter interactive search mode.

### Cause B: Process Collision & Critical Section Deadlock
- **Mechanism**: If `subprocess.Popen([terminal64.exe, ...])` launches MT5, and then `mt5.initialize(path=terminal64.exe)` also attempts to start MT5, two instances access the same Wine user profile concurrently.
- **Evidence**: Wine logged:
  ```text
  err:sync:RtlpWaitForCriticalSection section ... wait timed out in thread 01e8, blocked by 01d0, retrying (60 sec)
  ```
  Instance 2 (`thread 01e8`) was deadlocked waiting for database and profile locks held by Instance 1 (`thread 01d0`).
- **Resolution**:
  1. Enforce strict single-instance management: check if `terminal64.exe` is already running.
  2. Call `mt5.initialize()` in attach-first mode without launching a second process.

### Cause C: Zombie Process Retaining the IPC Pipe
- **Evidence**: `ps aux | grep -i terminal` revealed an orphaned process:
  ```text
  root 410287 5.3 3.2 1277536 245400 ? Sl Sep01 139:27 C:\Program Files\MetaTrader 5\terminal64.exe /portable
  ```
  This process had been running for 48+ hours in an unresponsive state, holding the named pipe and blocking all new connections.
- **Resolution**:
  Clean up all orphaned Wine and terminal processes (`wineserver -k`, `pkill -9 -f terminal64.exe`) before starting a fresh service instance.

---

## 4. Secondary Issue Analysis: `[WinError 10013] Access denied` on Port 8008

### Mechanism
In `run_scalper.py`, the HTTP Bridge starts a lightweight `HTTPServer`:
```python
HTTPServer(("0.0.0.0", 8008), ScalperBridgeHTTPHandler)
```
Under Wine, when Python calls Winsock `bind()` to `0.0.0.0:8008`:
- If port 8008 is already bound by a Linux process (such as a previous Python run, another container, or docker proxy), Wine translates the Linux socket error `EADDRINUSE` or `EACCES` to `WSAEACCES (10013)`: *"An attempt was made to access a socket in a way forbidden by its access permissions."*
- This is completely independent of MT5 IPC.

### Resolution
1. Make `HTTP_BRIDGE_PORT` configurable via CLI `--http-port` and environment variable.
2. Bind to `127.0.0.1` by default on VPS host or allow disabling via `--no-http-bridge`.
3. Catch the exception gracefully so port contention never prevents the trading engine from running.

---

## 5. Startup State Machine & Health Check

The scalper engine enforces a deterministic 9-stage startup state machine:

```text
[1. STARTING]
      │
      ▼
[2. XVFB_READY]         ──> Verify Display :99 is active via xdpyinfo / pgrep
      │
      ▼
[3. WINE_READY]         ──> Verify Wine prefix and Windows Python 3.9 interpreter
      │
      ▼
[4. MT5_PROCESS_READY]  ──> Verify exactly one terminal64.exe process running
      │
      ▼
[5. MT5_IPC_READY]      ──> Verify mt5.initialize() returns True & terminal_info() valid
      │
      ▼
[6. ACCOUNT_READY]      ──> Verify mt5.login() returns True & account_info() valid
      │
      ▼
[7. SYMBOL_READY]       ──> Verify symbol_select(symbol, True) returns True
      │
      ▼
[8. MARKET_DATA_READY]  ──> Verify symbol_info_tick() has valid bid/ask & M1 bars exist
      │
      ▼
[9. TRADING_READY]      ──> Engine enters active execution loop
```

If ANY stage fails:
- State transitions to `ERROR`.
- `TRADING_ENABLED = False` (no orders are sent).
- Detailed error reason is logged.
- The engine attempts controlled reconnection according to the recovery policy.

---

## 6. Standard Operating Procedures (SOP)

### Starting the Scalper Service
```bash
sudo systemctl start ecotrade-scalper
```

### Stopping the Scalper Service
```bash
sudo systemctl stop ecotrade-scalper
```

### Restarting the Scalper Service
```bash
sudo systemctl restart ecotrade-scalper
```

### Checking Service Status
```bash
sudo systemctl status ecotrade-scalper
```

### Streaming Live Trade Logs
```bash
tail -f /root/eco-trade/scalper_vm.log
```

### Emergency Process Cleanup (If Terminal Deadlocks)
```bash
sudo systemctl stop ecotrade-scalper
sudo pkill -9 -f terminal64.exe || true
sudo wineserver -k || true
sudo rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
sudo systemctl start ecotrade-scalper
```

### Running the Isolated Diagnostic Script
```bash
DISPLAY=:99 WINEPREFIX=/root/.wine wine "C:\\Python39\\python.exe" /root/eco-trade/scripts/diagnose_mt5_ipc.py
```
