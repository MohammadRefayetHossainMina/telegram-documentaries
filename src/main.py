"""Telegram Documentaries gateway.

Long-polls Telegram, runs the Bouncer on photos, then the Interviewer
state machine, Converter, Scripter, and Narrator voice note.
"""

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from io import BytesIO

from dotenv import load_dotenv
from telegram import Update
from telegram.error import NetworkError, TimedOut
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

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
_PENDING: dict[int, Turn] = {}

ReplySink = Callable[[str], Awaitable[object]]


def build_application(token: str) -> Application:
    """Build the bot with enough time to upload the picture and the voice note."""
    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=10.0,
        media_write_timeout=120.0,
    )
    return Application.builder().token(token).request(request).build()


async def _send_with_retry(send: Callable[[], Awaitable[object]], what: str) -> None:
    """Try a Telegram send three times. A slow upload must not drop the ending."""
    for attempt in range(1, 4):
        try:
            await send()
            return
        except (TimedOut, NetworkError):
            logger.warning("%s send stalled (attempt %s)", what, attempt)
            if attempt == 3:
                raise
            await asyncio.sleep(2)


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
    logger.info("saved portrait for chat_id=%s path=%s", chat_id, photo_path)
    logger.info("photo approved (chat_id=%s)", chat_id)
    await reply(decision.reply)
    opening = question_at(0)
    if not opening:
        logger.error("question 1 was empty (chat_id=%s)", chat_id)
        await reply(
            "The first question did not load. Send /restart and try the portrait again."
        )
        return
    logger.info("dispatching question 1 (chat_id=%s)", chat_id)
    try:
        await reply(opening)
    except Exception:
        logger.exception("could not send question 1 (chat_id=%s)", chat_id)
        await reply(
            "The first question did not go out. Send /restart and try the portrait again."
        )


async def _download_photo(update: Update) -> bytes | None:
    """Download the largest available photo size as raw bytes."""
    if update.message is None or update.message.photo is None:
        return None
    file = await update.message.photo[-1].get_file()
    data = await file.download_as_bytearray()
    return bytes(data)


async def _deliver(update: Update, turn: Turn) -> None:
    """Send text, the hybrid still, and the voice note, in that order."""
    message = update.message
    if message is None:
        return

    def send_photo(image: bytes) -> Callable[[], Awaitable[object]]:
        async def run() -> None:
            photo = BytesIO(image)
            photo.name = "hybrid.png"
            await message.reply_photo(photo=photo)

        return run

    def send_text(text: str) -> Callable[[], Awaitable[object]]:
        async def run() -> None:
            await message.reply_text(text)

        return run

    def send_voice(audio: bytes) -> Callable[[], Awaitable[object]]:
        async def run() -> None:
            voice = BytesIO(audio)
            voice.name = "documentary.ogg"
            await message.reply_voice(voice=voice)

        return run

    for image in turn.photos:
        await _send_with_retry(send_photo(image), "picture")
    for text in turn.replies:
        await _send_with_retry(send_text(text), "message")
    for audio in turn.voices:
        await _send_with_retry(send_voice(audio), "voice note")


async def _reset_and_greet(update: Update) -> None:
    """Purge one chat and send the greeting plus the photo prompt."""
    if update.message is None or update.effective_chat is None:
        return
    _PENDING.pop(update.effective_chat.id, None)
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
    phase = STORE.get(chat_id).phase
    logger.info("incoming text: chat_id=%s phase=%s text=%r", chat_id, phase, text)

    async def emit(piece: Turn) -> None:
        await _deliver(update, piece)

    turn = _PENDING.get(chat_id)
    if turn is None:
        turn = await handle_text(
            STORE,
            chat_id,
            text,
            INTERVIEWER,
            CONVERTER,
            SCRIPTER,
            NARRATOR,
            emit,
        )
    if turn.sent:
        _PENDING.pop(chat_id, None)
        return
    try:
        await _deliver(update, turn)
    except (TimedOut, NetworkError):
        if turn.photos or turn.voices:
            _PENDING[chat_id] = turn
        logger.exception("delivery stalled for chat_id=%s", chat_id)
        await update.message.reply_text(
            "The ending is ready, but Telegram was slow. "
            "Send any message and I will send it again."
        )
        return
    _PENDING.pop(chat_id, None)


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bouncer path, unless a photo arrives in the middle of the interview."""
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    blocked = photo_block_message(STORE.get(chat_id).phase)
    if blocked:
        logger.info(
            "photo ignored during %s (chat_id=%s)",
            STORE.get(chat_id).phase,
            chat_id,
        )
        await context.bot.send_message(chat_id=chat_id, text=blocked)
        return
    image_bytes = await _download_photo(update)
    if image_bytes is None:
        return
    logger.info("downloaded photo: bytes=%d (chat_id=%s)", len(image_bytes), chat_id)

    async def reply(text: str) -> None:
        await context.bot.send_message(chat_id=chat_id, text=text)

    await process_photo(image_bytes, chat_id, reply)


async def _on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tell the chat when a handler dies, instead of stopping quietly."""
    logger.error("handler failed", exc_info=context.error)
    chat = getattr(update, "effective_chat", None)
    if chat is None:
        return
    try:
        await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "Something broke before the next question. "
                "Send /restart and try the portrait again."
            ),
        )
    except Exception:
        logger.exception("could not report the handler failure (chat_id=%s)", chat.id)


def main() -> None:
    """Build the application and start Telegram long polling."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN missing from .env")

    app = build_application(token)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("restart", restart))
    app.add_handler(MessageHandler(filters.PHOTO, photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    app.add_error_handler(_on_error)

    logger.info("Starting Telegram long polling")
    app.run_polling()


if __name__ == "__main__":
    main()
