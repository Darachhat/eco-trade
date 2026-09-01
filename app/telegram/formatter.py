"""
app/telegram/formatter.py
──────────────────────────
All Telegram message templates.
Formats: signals, kill-switch alerts, daily/weekly reports, model status, risk status.
"""

from __future__ import annotations

import html
from datetime import datetime
from typing import Optional

from app.core.constants import SignalDirection
from app.strategy.signal_engine import TradeSignal


def _fmt_price(val: float) -> str:
    """Format price cleanly with appropriate comma separation and decimal precision."""
    if val <= 0:
        return "0"
    if val >= 1000:
        return f"{val:,.0f}" if val % 1 == 0 else f"{val:,.2f}".rstrip("0").rstrip(".")
    elif val >= 1:
        return f"{val:,.2f}".rstrip("0").rstrip(".")
    else:
        return f"{val:,.4f}".rstrip("0").rstrip(".")


def format_signal(signal: TradeSignal, signal_id: str, mode: str = "PAPER TRADING") -> str:
    """
    Format a trade signal for Telegram in a clean, professional, compact trading-terminal style.
    """
    if signal.direction == SignalDirection.NO_TRADE:
        return format_no_trade(signal)

    # 1. Asset & Timeframe
    raw_sym = signal.symbol.upper()
    if "/" not in raw_sym:
        for quote in ("USDT", "USDC", "BUSD", "USD", "EUR"):
            if raw_sym.endswith(quote):
                base = raw_sym[:-len(quote)]
                display_asset = f"{base}/{quote}"
                break
        else:
            display_asset = raw_sym
    else:
        display_asset = raw_sym

    tf = str(signal.timeframe).upper()
    if tf in ("1", "3", "5", "15", "30", "45"):
        tf_display = f"{tf}M"
    elif tf in ("60", "1H"):
        tf_display = "1H"
    elif tf in ("120", "2H"):
        tf_display = "2H"
    elif tf in ("240", "4H"):
        tf_display = "4H"
    elif tf in ("D", "1D", "1440"):
        tf_display = "1D"
    else:
        tf_display = f"{tf}M" if tf.isdigit() else tf

    # 2. Direction & Action
    is_long = signal.direction == SignalDirection.LONG
    is_short = signal.direction == SignalDirection.SHORT
    if is_long:
        dir_badge = "🟢 <b>BUY / LONG</b>"
    elif is_short:
        dir_badge = "🔴 <b>SELL / SHORT</b>"
    else:
        dir_badge = f"⚪ <b>{html.escape(signal.direction.value if hasattr(signal.direction, 'value') else str(signal.direction))}</b>"

    regime_str = html.escape(signal.regime or "UNKNOWN")

    # 3. Entry Zone
    entry_low = signal.entry_zone.price_low if signal.entry_zone else 0.0
    entry_high = signal.entry_zone.price_high if signal.entry_zone else 0.0
    if entry_low and entry_high and entry_low != entry_high:
        entry_val = f"<code>{_fmt_price(entry_low)} – {_fmt_price(entry_high)}</code>"
    elif entry_low:
        entry_val = f"<code>{_fmt_price(entry_low)}</code>"
    elif entry_high:
        entry_val = f"<code>{_fmt_price(entry_high)}</code>"
    else:
        entry_val = "<code>Market Price</code>"

    # 4. Stop Loss
    sl = signal.stop_loss.price if signal.stop_loss else 0.0
    sl_pct = signal.stop_loss.distance_pct if signal.stop_loss else 0.0
    sl_str = _fmt_price(sl)
    sign_prefix = "-" if is_long else ("+" if is_short else "")
    sl_pct_str = f" (<code>{sign_prefix}{abs(sl_pct):.2f}%</code>)" if sl_pct else ""
    sl_val = f"<code>{sl_str}</code>{sl_pct_str}"

    # 5. Take Profit Targets
    tp1 = signal.take_profit.tp1 if signal.take_profit else 0.0
    tp2 = signal.take_profit.tp2 if signal.take_profit else 0.0
    tp3 = signal.take_profit.tp3 if signal.take_profit else 0.0
    rr1 = signal.take_profit.risk_reward_tp1 if signal.take_profit else 0.0
    rr2 = signal.take_profit.risk_reward_tp2 if signal.take_profit else 0.0
    rr3 = signal.take_profit.risk_reward_tp3 if signal.take_profit else 0.0

    tp_entries = []
    if tp1:
        tp_entries.append(("TP1", tp1, rr1))
    if tp2:
        tp_entries.append(("TP2", tp2, rr2))
    if tp3:
        tp_entries.append(("TP3", tp3, rr3))

    tp_lines = []
    for idx, (tp_name, tp_val, tp_rr) in enumerate(tp_entries):
        rr_part = f" ({tp_rr:.1f}R)" if tp_rr else ""
        tp_lines.append(f"• <b>{tp_name}:</b> <code>{_fmt_price(tp_val)}</code>{rr_part}")
    tp_block = "\n".join(tp_lines) if tp_lines else "• <b>TP1:</b> <code>Open Target</code>"

    # 6. AI Analysis
    mtf_badges = []
    if signal.mtf_consensus:
        tf_order = ["240", "60", "15", "5", "1"]
        tf_names = {"240": "4H", "60": "1H", "15": "15M", "5": "5M", "1": "1M"}
        keys = [k for k in tf_order if k in signal.mtf_consensus] + [k for k in signal.mtf_consensus if k not in tf_order]
        for k in keys:
            res = signal.mtf_consensus[k]
            d = res.get("direction", "NO_TRADE") if isinstance(res, dict) else str(res)
            icon = "🟢" if "LONG" in d.upper() else ("🔴" if "SHORT" in d.upper() else "⚪")
            name = tf_names.get(str(k), f"{k}M")
            mtf_badges.append(f"{name} {icon}")
    mtf_str = "  ".join(mtf_badges) if mtf_badges else "N/A"

    # 7. Model Consensus (preformatted monospace for column alignment)
    model_preds = list(signal.model_predictions.items())
    model_lines = []
    for idx, (m_name, pred) in enumerate(model_preds[:6]):
        d = pred.get("direction", "?") if isinstance(pred, dict) else "?"
        c = (pred.get("confidence", 0.0) if isinstance(pred, dict) else 0.0) * 100
        icon = "🟢" if "LONG" in d.upper() else ("🔴" if "SHORT" in d.upper() else "⚪")
        d_clean = "LONG" if "LONG" in d.upper() else ("SHORT" if "SHORT" in d.upper() else d)
        name_padded = f"{m_name[:13]:<13}"
        model_lines.append(f"{name_padded} {icon} {d_clean:<5} {c:>3.0f}%")
    models_block = "\n".join(model_lines) if model_lines else "No model details"
    models_block_escaped = html.escape(models_block)

    # 8. Key Drivers
    positives = signal.explanation.get("positives", []) if signal.explanation else []
    negatives = signal.explanation.get("negatives", []) if signal.explanation else []
    driver_lines = []
    if positives or negatives:
        for p in positives[:4]:
            driver_lines.append(f"• {html.escape(str(p))}")
        for n in negatives[:2]:
            driver_lines.append(f"• ⚠️ {html.escape(str(n))}")
    else:
        driver_lines = [
            f"• GMM Regime: <code>{regime_str}</code> confirmed",
            f"• {tf_display} Momentum & Trend alignment",
            "• Quantitative multi-model confluence",
        ]
    drivers_block = "\n".join(driver_lines)

    # 9. Final Compact Message Assembly
    mode_text = mode.upper() if mode else "PAPER TRADING"
    msg = f"""⚡ <b>ECOTRADE AI SIGNAL</b>
───────────────────────
💎 <b>{display_asset}</b> • <code>{tf_display}</code> • {dir_badge}
🌐 <b>Regime:</b> <code>{regime_str}</code>

📍 <b>Entry:</b> {entry_val}
🛑 <b>Stop Loss:</b> {sl_val}

🎯 <b>Take Profit:</b>
{tp_block}

📊 <b>AI Analysis:</b>
• <b>Confidence:</b> <b>{signal.confidence*100:.0f}%</b> | <b>Agreement:</b> <b>{signal.model_agreement*100:.0f}%</b>
• <b>MTF:</b> {mtf_str}

🤖 <b>MODEL CONSENSUS:</b>
<pre>
{models_block_escaped}
</pre>
💡 <b>KEY DRIVERS:</b>
{drivers_block}
───────────────────────
🆔 <code>{html.escape(signal_id)}</code> • <b>{mode_text}</b>"""

    return msg


def format_no_trade(signal: TradeSignal) -> str:
    """Format a NO_TRADE notification."""
    reason = html.escape(signal.no_trade_reason or "Confidence / Risk filter not met")
    return (
        f"⚪ <b>ECOTRADE — NO TRADE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Asset: <code>#{html.escape(signal.symbol)}</code> ({html.escape(str(signal.timeframe))}M)\n"
        f"Reason: <i>{reason}</i>\n"
        f"Time: <code>{signal.generated_at.strftime('%Y-%m-%d %H:%M')} UTC</code>"
    )


def format_kill_switch_alert(reason: str) -> str:
    return f"""🚨 <b>EMERGENCY: TRADING HALTED</b> 🚨
━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>Trigger Reason:</b>
<i>{reason}</i>

🛑 <b>Safety Action:</b>
• All signal generation paused
• Order execution disabled
• Manual review required to resume

⏰ <b>Timestamp:</b> <code>{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</code>"""


def format_daily_report(
    date: str,
    signals: int,
    wins: int,
    losses: int,
    win_rate: float,
    profit_factor: float,
    expectancy: float,
    max_drawdown: float,
    best_model: str,
    worst_model: str,
    regime: str,
    drift_status: str,
    champion: str,
) -> str:
    win_emoji = "🔥" if win_rate >= 0.6 else "📊"
    return f"""{win_emoji} <b>DAILY PERFORMANCE REPORT</b>
━━━━━━━━━━━━━━━━━━━━━━━━
📅 <b>Date:</b> <code>{date}</code>

📈 <b>Execution Summary:</b>
• <b>Signals:</b> <code>{signals}</code> (<b>{wins}W</b> / <b>{losses}L</b>)
• <b>Win Rate:</b> <b>{win_rate*100:.1f}%</b>
• <b>Profit Factor:</b> <b>{profit_factor:.2f}</b>
• <b>Expected Value:</b> <code>{expectancy:+.2f}R</code>
• <b>Max Drawdown:</b> <code>{max_drawdown*100:.1f}%</code>

🧠 <b>AI & Models:</b>
• 👑 <b>Champion:</b> <b>{champion}</b>
• 🏆 <b>Best Model:</b> {best_model}
• ⚠️ <b>Worst Model:</b> {worst_model}
• 🌐 <b>Market Regime:</b> <code>{regime}</code>
• 📡 <b>Data Drift:</b> <code>{drift_status}</code>"""


def format_model_performance(models: list[dict]) -> str:
    """Format /models command response."""
    lines = [
        "🤖 <b>AI MODEL LEADERBOARD</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    champion = None
    best_pf = 0.0

    for m in models:
        name = m.get("name", "?").upper()
        acc = m.get("accuracy", 0) * 100
        wr = m.get("win_rate", 0) * 100
        pf = m.get("profit_factor", 0)
        status = m.get("status", "CANDIDATE")
        badge = "👑 " if status == "CHAMPION" else "• "

        lines.append(f"{badge}<b>{name}</b> (<code>{m.get('version', 'v1')}</code>)")
        lines.append(f"  ├ Accuracy: <b>{acc:.1f}%</b> | Win Rate: <b>{wr:.1f}%</b>")
        lines.append(f"  └ Profit Factor: <b>{pf:.2f}</b>")

        if pf > best_pf:
            best_pf = pf
            champion = f"{m.get('name', '?')} {m.get('version', 'v1')}"

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")
    if champion:
        lines.append(f"👑 <b>Active Champion:</b> <b>{champion}</b>")

    return "\n".join(lines)


def format_system_status(status: dict) -> str:
    is_halted = status.get("kill_switch_active", False)
    status_badge = "🔴 <b>HALTED</b>" if is_halted else "🟢 <b>ACTIVE</b>"
    ws_icon = "✅ Connected" if status.get("ws_connected") else "❌ Disconnected"
    
    return f"""⚙️ <b>SYSTEM OPERATIONAL STATUS</b>
━━━━━━━━━━━━━━━━━━━━━━━━
• <b>State:</b> {status_badge}
• <b>Mode:</b> <code>{status.get('trading_mode', '?').upper()}</code>
• <b>WebSocket Feed:</b> <code>{ws_icon}</code>

📊 <b>Live Performance:</b>
• <b>Daily PnL:</b> <b>{status.get('daily_pnl_pct', 0):+.2f}%</b>
• <b>Open Positions:</b> <code>{status.get('total_open', 0)}</code>
• <b>Consecutive Losses:</b> <code>{status.get('consecutive_losses', 0)}</code>
• <b>Max Drawdown:</b> <code>{status.get('max_drawdown_pct', 0):.2f}%</code>"""


def format_risk_status(risk: dict) -> str:
    kill_badge = "🔴 <b>HALTED</b>" if risk.get("kill_switch_active") else "🟢 <b>NORMAL</b>"
    limits = risk.get("limits", {})
    
    return f"""🛡️ <b>RISK & CIRCUIT BREAKERS</b>
━━━━━━━━━━━━━━━━━━━━━━━━
• <b>Kill Switch:</b> {kill_badge}
• <b>Risk / Trade:</b> <code>{limits.get('risk_per_trade_pct', 1.0):.1f}%</code>

📊 <b>Exposure & Safety Limits:</b>
• <b>Daily PnL:</b> <b>{risk.get('daily_pnl_pct', 0):+.2f}%</b> (Limit: <code>-{limits.get('max_daily_loss_pct', 3.0)}%</code>)
• <b>Positions:</b> <code>{risk.get('total_open', 0)}</code> / <code>{limits.get('max_open_positions', 3)} max</code>
• <b>Loss Streak:</b> <code>{risk.get('consecutive_losses', 0)}</code> / <code>{limits.get('max_consecutive_losses', 5)} max</code>
• <b>Max Drawdown:</b> <code>{risk.get('max_drawdown_pct', 0):.2f}%</code>"""


def format_scalper_status(telemetry: dict, positions: list) -> str:
    is_running = telemetry.get("is_running", False)
    status_icon = "🟢 <b>ACTIVE (TICK LOOP)</b>" if is_running else "🔴 <b>STOPPED</b>"
    symbol = telemetry.get("symbol", "XAUUSDm")
    bid = telemetry.get("current_bid", 0.0)
    ask = telemetry.get("current_ask", 0.0)
    spread = telemetry.get("current_spread_points", 0.0)
    atr = telemetry.get("current_atr_points", 0.0)
    sig = telemetry.get("last_signal", "NEUTRAL")
    reason = telemetry.get("last_signal_reason", "Awaiting ticks")

    pos_lines = []
    if positions:
        for p in positions:
            pnl_sign = "+" if p.get("profit", 0) >= 0 else ""
            pos_lines.append(f"• <b>#{p.get('ticket')}</b> <code>{p.get('symbol')} {p.get('type')} {p.get('volume')}L</code> @ ${p.get('price_open', 0):.2f} (<b>{pnl_sign}${p.get('profit', 0):.2f}</b>)")
        pos_str = "\n".join(pos_lines)
    else:
        pos_str = "<i>No open positions. Scalper scanning ticks...</i>"

    return f"""⚡ <b>EXNESS MT5 HIGH-FREQUENCY SCALPER</b>
━━━━━━━━━━━━━━━━━━━━━━━━
• <b>Engine State:</b> {status_icon}
• <b>Active Target:</b> <code>{symbol}</code>
• <b>Market Price:</b> <code>Bid: ${bid:.2f} | Ask: ${ask:.2f}</code>
• <b>Spread / ATR:</b> <code>{spread:.0f} pts | ATR: {atr:.0f} pts</code>
• <b>Last Signal:</b> <b>{sig}</b>
• <b>Reason:</b> <i>{html.escape(reason)}</i>

🎯 <b>Target Calibration:</b>
• <b>Take Profit:</b> <code>+$2.00 price move</code>
• <b>Stop Loss:</b> <code>-$10.00 buffer</code>
• <b>Break-Even:</b> <code>+$1.00 move</code>

📊 <b>Open Positions ({len(positions)}):</b>
{pos_str}

<i>Commands:</i>
• <code>/scalp start</code> — Start autonomous loop
• <code>/scalp stop</code> — Emergency halt
• <code>/scalp buy [LOT]</code> — Instant BUY
• <code>/scalp sell [LOT]</code> — Instant SELL
• <code>/closeall</code> — Liquidate all open positions"""


def format_mt5_account(acc: dict, positions: list) -> str:
    conn_badge = "🟢 <b>CONNECTED</b>" if acc.get("connected") else "🔴 <b>DISCONNECTED</b>"
    pos_count = len(positions)
    total_pnl = sum(p.get("profit", 0.0) for p in positions)
    pnl_sign = "+" if total_pnl >= 0 else ""

    return f"""🏦 <b>EXNESS MT5 TERMINAL</b>
━━━━━━━━━━━━━━━━━━━━━━━━
• <b>Status:</b> {conn_badge}
• <b>Account:</b> <code>{acc.get('login', '?')} ({acc.get('server', '?')})</code>
• <b>Balance:</b> <b>${acc.get('balance', 0):,.2f} USD</b>
• <b>Equity:</b> <b>${acc.get('equity', 0):,.2f} USD</b>
• <b>Leverage:</b> <code>1:{acc.get('leverage', 2000)}</code>
• <b>Free Margin:</b> <code>${acc.get('free_margin', 0):,.2f}</code>
• <b>Open Positions:</b> <code>{pos_count}</code> (Floating: <b>{pnl_sign}${total_pnl:.2f}</b>)"""


