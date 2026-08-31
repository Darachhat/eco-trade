"""
app/telegram/formatter.py
──────────────────────────
All Telegram message templates.
Formats: signals, kill-switch alerts, daily/weekly reports, model status.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.core.constants import SignalDirection
from app.strategy.signal_engine import TradeSignal


def format_signal(signal: TradeSignal, signal_id: str, mode: str = "PAPER TRADING") -> str:
    """
    Format a trade signal for Telegram (Section 27 spec).
    """
    if signal.direction == SignalDirection.NO_TRADE:
        return format_no_trade(signal)

    dir_emoji = "🟢" if signal.direction == SignalDirection.LONG else "🔴"
    dir_text = signal.direction.value

    # Entry zone
    entry_low = signal.entry_zone.price_low if signal.entry_zone else 0.0
    entry_high = signal.entry_zone.price_high if signal.entry_zone else 0.0
    sl = signal.stop_loss.price if signal.stop_loss else 0.0
    tp1 = signal.take_profit.tp1 if signal.take_profit else 0.0
    tp2 = signal.take_profit.tp2 if signal.take_profit else 0.0
    tp3 = signal.take_profit.tp3 if signal.take_profit else 0.0
    rr = signal.take_profit.risk_reward_tp1 if signal.take_profit else 0.0

    # MTF alignment
    mtf_lines = []
    if signal.mtf_consensus:
        tf_display = {"240": "4H", "60": "1H", "15": "15M", "5": "5M"}
        for tf, res in sorted(signal.mtf_consensus.items(), reverse=True):
            d = res.get("direction", "NO_TRADE")
            emoji = "🟢" if d == "LONG" else ("🔴" if d == "SHORT" else "⚪")
            tf_name = tf_display.get(str(tf), tf)
            mtf_lines.append(f"{tf_name.ljust(4)} {emoji} {d}")

    mtf_section = "\n".join(mtf_lines) if mtf_lines else "N/A"

    # Model consensus table
    model_lines = []
    for model_name, pred in signal.model_predictions.items():
        d = pred.get("direction", "?")
        c = pred.get("confidence", 0) * 100
        emoji = "🟢" if d == "LONG" else ("🔴" if d == "SHORT" else "⚪")
        model_lines.append(f"{model_name.ljust(16)} {emoji} {d.ljust(8)} {c:.0f}%")
    model_section = "\n".join(model_lines) if model_lines else "N/A"

    # Explanation
    positives = signal.explanation.get("positives", [])
    negatives = signal.explanation.get("negatives", [])
    reasons = []
    for p in positives[:5]:
        reasons.append(f"+ {p}")
    for n in negatives[:3]:
        reasons.append(f"- {n}")
    reason_text = "\n".join(reasons) if reasons else "Quantitative ensemble signal."

    msg = f"""🚨 <b>AI CRYPTO SIGNAL</b>

━━━━━━━━━━━━━━━━━━
<b>ASSET</b>
{signal.symbol}

<b>DIRECTION</b>
{dir_emoji} <b>{dir_text}</b>

<b>ENTRY ZONE</b>
{entry_low:,.2f} – {entry_high:,.2f}

<b>STOP LOSS</b>
{sl:,.2f}

<b>TAKE PROFIT</b>
TP1  {tp1:,.2f}
TP2  {tp2:,.2f}
TP3  {tp3:,.2f}

<b>RISK / REWARD</b>
1 : {rr:.1f}

<b>AI CONFIDENCE</b>
{signal.confidence*100:.0f}%

<b>MODEL AGREEMENT</b>
{signal.model_agreement*100:.0f}%

<b>MARKET REGIME</b>
{signal.regime or "UNKNOWN"}

<b>MULTI-TIMEFRAME</b>
{mtf_section}

━━━━━━━━━━━━━━━━━━

<b>MODEL CONSENSUS</b>
{model_section}

━━━━━━━━━━━━━━━━━━

<b>KEY FACTORS</b>
{reason_text}

<b>SIGNAL ID</b>
<code>{signal_id}</code>

<b>MODE</b>
{mode}

⚠️ <i>Probabilistic decision-support signal.
Not guaranteed financial performance.</i>"""

    return msg


def format_no_trade(signal: TradeSignal) -> str:
    """Format a NO_TRADE notification (usually not sent unless admin)."""
    return (
        f"⚪ <b>NO TRADE</b> — {signal.symbol}\n"
        f"Reason: {signal.no_trade_reason or 'Insufficient signal quality'}\n"
        f"Time: {signal.generated_at.strftime('%Y-%m-%d %H:%M')} UTC"
    )


def format_kill_switch_alert(reason: str) -> str:
    return f"""🚨 <b>TRADING SYSTEM HALTED</b>

<b>Reason:</b>
{reason}

<b>Action:</b>
New positions disabled.

<b>Manual review required.</b>

Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"""


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
    return f"""📊 <b>DAILY AI TRADING REPORT</b>

<b>Date:</b> {date}

<b>Signals:</b> {signals}
<b>Wins:</b> {wins}
<b>Losses:</b> {losses}
<b>Win Rate:</b> {win_rate:.1%}

<b>Profit Factor:</b> {profit_factor:.2f}
<b>Expected Value:</b> {expectancy:+.2f}R
<b>Maximum Drawdown:</b> {max_drawdown:.1%}

<b>Best Model:</b> {best_model}
<b>Worst Model:</b> {worst_model}

<b>Current Regime:</b> {regime}
<b>Model Drift:</b> {drift_status}

<b>Champion:</b> {champion}"""


def format_model_performance(models: list[dict]) -> str:
    """Format /models command response."""
    lines = ["<b>🤖 AI MODEL PERFORMANCE</b>\n"]
    champion = None
    best_pf = 0.0

    for m in models:
        lines.append(f"<b>{m.get('name', '?').upper()}</b>")
        lines.append(f"Accuracy: {m.get('accuracy', 0)*100:.1f}%")
        lines.append(f"Win Rate: {m.get('win_rate', 0)*100:.1f}%")
        lines.append(f"Profit Factor: {m.get('profit_factor', 0):.2f}")
        lines.append("")
        if m.get("profit_factor", 0) > best_pf:
            best_pf = m["profit_factor"]
            champion = f"{m.get('name', '?')} {m.get('version', 'v1')}"

    if champion:
        lines.append(f"<b>👑 CURRENT CHAMPION</b>")
        lines.append(champion)

    return "\n".join(lines)


def format_system_status(status: dict) -> str:
    kill = "🔴 HALTED" if status.get("kill_switch_active") else "🟢 RUNNING"
    return f"""⚙️ <b>SYSTEM STATUS</b>

Status: {kill}
Mode: {status.get("trading_mode", "?").upper()}
Daily PnL: {status.get("daily_pnl_pct", 0):+.2f}%
Open Positions: {status.get("total_open", 0)}
Consecutive Losses: {status.get("consecutive_losses", 0)}
Max Drawdown: {status.get("max_drawdown_pct", 0):.2f}%
WS Connected: {"✅" if status.get("ws_connected") else "❌"}"""


def format_risk_status(risk: dict) -> str:
    return f"""🛡️ <b>RISK STATUS</b>

Kill Switch: {"🔴 ACTIVE" if risk.get("kill_switch_active") else "🟢 OK"}
Daily PnL: {risk.get("daily_pnl_pct", 0):+.2f}%
Open Positions: {risk.get("total_open", 0)} / {risk.get("limits", {}).get("max_open_positions", 3)}
Consecutive Losses: {risk.get("consecutive_losses", 0)} / {risk.get("limits", {}).get("max_consecutive_losses", 5)}
Max Drawdown: {risk.get("max_drawdown_pct", 0):.2f}%
Risk/Trade: {risk.get("limits", {}).get("risk_per_trade_pct", 1):.1f}%"""
