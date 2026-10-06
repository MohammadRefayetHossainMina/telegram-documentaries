"""Telegram Documentaries gateway.

Long-polls Telegram, runs the Bouncer on photos, then the Interviewer
state machine, Converter, Scripter, and Narrator voice note.
"""

import logging
import os
from collections.abc import Awaitable, Callable
from io import BytesIO

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.agents.bouncer import (
    BOUNCER_ERROR_REPLY,
    BouncerAgent,
    BouncerError,
    decide_reply,
)
from src.agents.converter import ConverterAgent
from src.agents.interviewer import InterviewerAgent, question_at
from src.agents.narrator import Narrator
from src.agents.scripter import ScripterAgent
from src.pipeline import Turn, handle_text, photo_block_message
from src.state.media import save_chat_file
from src.state.session_store import SessionStore

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

REPLY_TEXT = "hey mate!"

BOUNCER = BouncerAgent()
INTERVIEWER = InterviewerAgent()
CONVERTER = ConverterAgent()
SCRIPTER = ScripterAgent()
NARRATOR = Narrator()
STORE = SessionStore()

ReplySink = Callable[[str], Awaitable[object]]


def greeting() -> str:
    """Return the walking-skeleton greeting."""
    return REPLY_TEXT


async def process_photo(image_bytes: bytes, chat_id: int, reply: ReplySink) -> None:
    """Bouncer pipeline: classify a photo and route the outcome.

    Every photo attempt resets the chat first. A human portrait is stored
    and the first interview question is asked. Anything else is a humorous
    rejection with the session left idle.
    """
    STORE.reset(chat_id)
    try:
        verdict = await BOUNCER.classify(image_bytes)
    except BouncerError:
        logger.exception("bouncer could not classify photo (chat_id=%s)", chat_id)
        await reply(BOUNCER_ERROR_REPLY)
        return
    decision = decide_reply(verdict)
    if not decision.approved:
        STORE.reset(chat_id)
        logger.info(
            "photo rejected (chat_id=%s) reason=%r", chat_id, verdict.reason[:80]
        )
        await reply(decision.reply)
        return

    try:
        photo_path = save_chat_file(chat_id, "portrait.jpg", image_bytes)
    except OSError:
        logger.exception("could not store portrait (chat_id=%s)", chat_id)
        await reply(BOUNCER_ERROR_REPLY)
        return

    STORE.update(
        chat_id,
        phase="interviewing",
        question_index=0,
        photo_path=photo_path,
        media_paths=[photo_path],
    )
    logger.info("photo approved (chat_id=%s)", chat_id)
    await reply(decision.reply)
    opening = question_at(0)
    if opening:
        await reply(opening)


async def _download_photo(update: Update) -> bytes | None:
    """Download the largest available photo size as raw bytes."""
    if update.message is None or update.message.photo is None:
        return None
    file = await update.message.photo[-1].get_file()
    data = await file.download_as_bytearray()
    return bytes(data)


async def _deliver(update: Update, turn: Turn) -> None:
    """Send text, the hybrid still, and the voice note, in that order."""
    if update.message is None:
        return
    for image in turn.photos:
        photo = BytesIO(image)
        photo.name = "hybrid.png"
        await update.message.reply_photo(photo=photo)
    for text in turn.replies:
        await update.message.reply_text(text)
    for audio in turn.voices:
        voice = BytesIO(audio)
        voice.name = "documentary.ogg"
        await update.message.reply_voice(voice=voice)


async def _reset_and_greet(update: Update) -> None:
    """Purge one chat and send the greeting plus the photo prompt."""
    if update.message is None or update.effective_chat is None:
        return
    STORE.reset(update.effective_chat.id)
    logger.info("session reset for chat_id=%s", update.effective_chat.id)
    await update.message.reply_text(greeting())
    await update.message.reply_text(
        "Clean slate. Send me a clear portrait photo when you are ready."
    )


async def start(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start: reset session state and greet."""
    await _reset_and_greet(update)


async def restart(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /restart the same way as /start, without exiting the process."""
    await _reset_and_greet(update)


async def echo(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route a text message through the interview or a production retry."""
    if update.message is None or update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    text = update.message.text or ""
    logger.info("incoming text: chat_id=%s text=%r", chat_id, text)
    turn = await handle_text(
        STORE,
        chat_id,
        text,
        INTERVIEWER,
        CONVERTER,
        SCRIPTER,
        NARRATOR,
    )
    await _deliver(update, turn)


async def photo(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bouncer path, unless a photo arrives in the middle of the interview."""
    if update.message is None or update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    blocked = photo_block_message(STORE.get(chat_id).phase)
    if blocked:
        logger.info(
            "photo ignored during %s (chat_id=%s)",
            STORE.get(chat_id).phase,
            chat_id,
        )
        await update.message.reply_text(blocked)
        return
    image_bytes = await _download_photo(update)
    if image_bytes is None:
        return
    logger.info("downloaded photo: bytes=%d (chat_id=%s)", len(image_bytes), chat_id)
    await process_photo(image_bytes, chat_id, update.message.reply_text)


def main() -> None:
    """Build the application and start Telegram long polling."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN missing from .env")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("restart", restart))
    app.add_handler(MessageHandler(filters.PHOTO, photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logger.info("Starting Telegram long polling")
    app.run_polling()


if __name__ == "__main__":
    main()
