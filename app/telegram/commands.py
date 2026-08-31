"""
app/telegram/commands.py
─────────────────────────
All 13 Telegram bot command handlers.
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.core.config import settings
from app.core.logging import get_logger
from app.risk.manager import risk_manager
from app.telegram.formatter import (
    format_model_performance,
    format_risk_status,
    format_system_status,
)

logger = get_logger("telegram")

_HELP_TEXT = """🤖 <b>AI Crypto Trader Commands</b>

/start — Welcome message
/help — Show this help
/status — System status
/market &lt;SYMBOL&gt; — Market snapshot
/signal &lt;SYMBOL&gt; — Generate on-demand signal
/models — Model performance table
/performance — Trading performance stats
/journal — Recent trading journal
/risk — Risk status
/positions — Open positions
/backtest — Run backtest
/pause — Pause signal generation
/resume — Resume signal generation

Example: <code>/signal BTCUSDT</code>"""


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🚀 <b>AI Crypto Trader</b>\n\n"
        "Probabilistic AI trading signal system.\n"
        "Use /help to see available commands.",
        parse_mode="HTML",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(_HELP_TEXT, parse_mode="HTML")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    status = risk_manager.status()
    status["trading_mode"] = settings.trading_mode.value
    status["ws_connected"] = True  # Will be wired to actual WS state
    msg = format_system_status(status)
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_market(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    symbol = args[0].upper() if args else "BTCUSDT"
    await update.message.reply_text(
        f"📈 <b>{symbol}</b> — fetching market data...",
        parse_mode="HTML",
    )
    # Full implementation wired to BybitClient in main app


async def cmd_signal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    symbol = args[0].upper() if args else "BTCUSDT"
    await update.message.reply_text(
        f"⏳ Generating signal for <b>{symbol}</b>...",
        parse_mode="HTML",
    )
    # Full signal generation wired in main pipeline


async def cmd_models(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Placeholder — wired to ModelRepository in full implementation
    await update.message.reply_text(
        "🤖 <b>Model data loading...</b>\nUse API: GET /models/performance",
        parse_mode="HTML",
    )


async def cmd_performance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📊 <b>Performance data loading...</b>\nUse API: GET /journal",
        parse_mode="HTML",
    )


async def cmd_journal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📔 <b>Trading Journal</b>\nUse API: GET /journal for full history.",
        parse_mode="HTML",
    )


async def cmd_risk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = format_risk_status(risk_manager.status())
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_positions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    status = risk_manager.status()
    open_pos = status.get("open_positions", {})
    if not any(v > 0 for v in open_pos.values()):
        await update.message.reply_text("📭 No open positions.", parse_mode="HTML")
    else:
        lines = [f"📊 <b>Open Positions</b>\n"]
        for sym, cnt in open_pos.items():
            if cnt > 0:
                lines.append(f"• {sym}: {cnt} position(s)")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_backtest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "⏳ <b>Backtest</b>\nUse API: POST /backtest/run to start a backtest.",
        parse_mode="HTML",
    )


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Only admin can pause
    chat_id = str(update.message.chat_id)
    if chat_id != settings.telegram_admin_chat_id:
        await update.message.reply_text("⛔ Admin only command.", parse_mode="HTML")
        return
    risk_manager.activate_kill_switch("Manual pause via Telegram")
    await update.message.reply_text(
        "⏸️ <b>Signal generation PAUSED</b>.\nUse /resume to restart.",
        parse_mode="HTML",
    )


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.message.chat_id)
    if chat_id != settings.telegram_admin_chat_id:
        await update.message.reply_text("⛔ Admin only command.", parse_mode="HTML")
        return
    risk_manager.deactivate_kill_switch()
    await update.message.reply_text(
        "▶️ <b>Signal generation RESUMED</b>.",
        parse_mode="HTML",
    )
