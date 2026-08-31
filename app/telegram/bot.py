"""
app/telegram/bot.py
────────────────────
Telegram bot startup, polling, and message sending.
"""

from __future__ import annotations

from typing import Optional

from telegram import Bot
from telegram.ext import Application, CommandHandler

from app.core.config import settings
from app.core.logging import get_logger
from app.telegram.commands import (
    cmd_backtest,
    cmd_help,
    cmd_journal,
    cmd_market,
    cmd_models,
    cmd_pause,
    cmd_performance,
    cmd_positions,
    cmd_resume,
    cmd_risk,
    cmd_signal,
    cmd_start,
    cmd_status,
)

logger = get_logger("telegram")


class TelegramBot:
    """Manages the Telegram bot application."""

    def __init__(self) -> None:
        self._app: Optional[Application] = None
        self._bot: Optional[Bot] = None

    def build(self) -> Application:
        """Build the application with all command handlers."""
        if not settings.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set")

        self._app = Application.builder().token(settings.telegram_bot_token).build()
        self._bot = self._app.bot

        # Register commands
        self._app.add_handler(CommandHandler("start", cmd_start))
        self._app.add_handler(CommandHandler("help", cmd_help))
        self._app.add_handler(CommandHandler("status", cmd_status))
        self._app.add_handler(CommandHandler("market", cmd_market))
        self._app.add_handler(CommandHandler("signal", cmd_signal))
        self._app.add_handler(CommandHandler("models", cmd_models))
        self._app.add_handler(CommandHandler("performance", cmd_performance))
        self._app.add_handler(CommandHandler("journal", cmd_journal))
        self._app.add_handler(CommandHandler("risk", cmd_risk))
        self._app.add_handler(CommandHandler("positions", cmd_positions))
        self._app.add_handler(CommandHandler("backtest", cmd_backtest))
        self._app.add_handler(CommandHandler("pause", cmd_pause))
        self._app.add_handler(CommandHandler("resume", cmd_resume))

        logger.info("Telegram bot configured")
        return self._app

    async def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML",
    ) -> None:
        """Send a message to the configured chat."""
        target = chat_id or settings.telegram_chat_id
        if not target:
            logger.warning("No Telegram chat_id configured")
            return
        if not self._bot:
            # Lazy init
            self._bot = Bot(token=settings.telegram_bot_token)
        try:
            await self._bot.send_message(
                chat_id=target,
                text=text,
                parse_mode=parse_mode,
            )
        except Exception as e:
            logger.error("Failed to send Telegram message", error=str(e))

    async def send_signal_alert(self, text: str) -> None:
        """Send to main chat."""
        await self.send_message(text, settings.telegram_chat_id)

    async def send_admin_alert(self, text: str) -> None:
        """Send to admin chat only."""
        await self.send_message(text, settings.telegram_admin_chat_id)

    async def start_polling(self) -> None:
        """Start the bot in polling mode."""
        if not self._app:
            self.build()
        logger.info("Starting Telegram bot polling")
        await self._app.run_polling()  # type: ignore[union-attr]


# Singleton
telegram_bot = TelegramBot()
