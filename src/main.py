"""Walking skeleton: Telegram long-polling bot gateway.

Phase 1 deliverable of SPECS/ROADMAP.md. Replies to every incoming
message (text or photo, including /start) with a hardcoded greeting.
The ADK pipeline stages (Bouncer, Interviewer, ...) arrive in later
phases.
"""

import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

REPLY_TEXT = "hey mate!"


def greeting() -> str:
    """Return the walking-skeleton greeting."""
    return REPLY_TEXT


async def _reply(update: Update) -> None:
    """Log the incoming event and echo the hardcoded greeting."""
    if update.message is None or update.effective_chat is None:
        return
    logger.info(
        "incoming update: chat_id=%s text=%r",
        update.effective_chat.id,
        update.message.text,
    )
    await update.message.reply_text(greeting())


async def start(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    await _reply(update)


async def echo(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catch-all for text and photo messages."""
    await _reply(update)


def main() -> None:
    """Build the application and start Telegram long polling."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN missing from .env")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, echo))

    logger.info("Starting Telegram long polling (walking skeleton)")
    app.run_polling()


if __name__ == "__main__":
    main()
