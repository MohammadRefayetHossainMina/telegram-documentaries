"""Chat turns for the interview and the documentary handoff.

The Interviewer is the hub: after the Bouncer approves a portrait, this
module asks one question at a time, then calls Converter, Scripter, and
the Narrator tool.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from src.agents.converter import ConverterAgent
from src.agents.interviewer import InterviewerAgent, question_at
from src.agents.narrator import Narrator
from src.agents.scripter import ScripterAgent
from src.errors import PipelineError
from src.state.media import save_chat_file
from src.state.session_store import SessionStore

logger = logging.getLogger(__name__)

ASK_FOR_PHOTO = "Send me a clear portrait photo of a person to begin."
PHOTO_DURING_INTERVIEW = (
    "Hold that thought — finish answering in text, or send /restart to start fresh."
)
PRODUCTION_RETRY = (
    "The cutting room jammed. Send any message to try the ending again, "
    "or /restart for a clean slate."
)
DONE_REPLY = (
    "That documentary is in the can. Send /restart, or a new portrait, "
    "when you want another take."
)
BLOCKED_PHASES = frozenset({"interviewing", "producing"})


@dataclass
class Turn:
    """What the gateway should send back for one incoming update."""

    replies: list[str] = field(default_factory=list)
    photos: list[bytes] = field(default_factory=list)
    voices: list[bytes] = field(default_factory=list)


def photo_block_message(phase: str) -> str | None:
    """Return a guard message when a photo arrives at the wrong time."""
    if phase in BLOCKED_PHASES:
        return PHOTO_DURING_INTERVIEW
    return None


async def produce_documentary(
    store: SessionStore,
    chat_id: int,
    interviewer: InterviewerAgent,
    converter: ConverterAgent,
    scripter: ScripterAgent,
    narrator: Narrator,
) -> Turn:
    """Run dossier, hybrid image, script, and voice note for one chat."""
    state = store.get(chat_id)
    try:
        if not state.photo_path:
            raise PipelineError("portrait file is missing")
        portrait = Path(state.photo_path).read_bytes()
        dossier = await interviewer.summarize(state.answers)
        store.update(
            chat_id,
            dossier=dossier.summary,
            suggested_animal=dossier.suggested_animal,
            phase="producing",
        )
        image = await converter.render(portrait, dossier)
        image_path = save_chat_file(chat_id, "hybrid.png", image)
        script = await scripter.write_script(dossier)
        audio = await narrator.speak(script)
        voice_path = save_chat_file(chat_id, "narration.ogg", audio)
        media_paths = [state.photo_path, image_path, voice_path]
        store.update(
            chat_id,
            script=script,
            phase="complete",
            media_paths=media_paths,
        )
        logger.info("documentary delivered for chat_id=%s", chat_id)
        return Turn(replies=[script], photos=[image], voices=[audio])
    except PipelineError:
        logger.exception("documentary production failed for chat_id=%s", chat_id)
        store.update(chat_id, phase="producing")
        return Turn(replies=[PRODUCTION_RETRY])
    except OSError:
        logger.exception("could not read or store media for chat_id=%s", chat_id)
        store.update(chat_id, phase="producing")
        return Turn(replies=[PRODUCTION_RETRY])


async def handle_text(
    store: SessionStore,
    chat_id: int,
    text: str,
    interviewer: InterviewerAgent,
    converter: ConverterAgent,
    scripter: ScripterAgent,
    narrator: Narrator,
) -> Turn:
    """Advance the interview, or retry production, from one text message."""
    state = store.get(chat_id)
    if state.phase == "idle":
        return Turn(replies=[ASK_FOR_PHOTO])
    if state.phase == "complete":
        return Turn(replies=[DONE_REPLY])
    if state.phase == "producing":
        return await produce_documentary(
            store, chat_id, interviewer, converter, scripter, narrator
        )
    if state.phase == "human_confirmed":
        store.update(chat_id, phase="interviewing", question_index=0)
        opening = question_at(0)
        return Turn(replies=[opening or ASK_FOR_PHOTO])
    if state.phase != "interviewing":
        return Turn(replies=[ASK_FOR_PHOTO])

    answer = text.strip()
    if not answer:
        return Turn(replies=["I need a few words for the field notes."])

    updated = store.add_answer(chat_id, answer)
    nxt = question_at(updated.question_index)
    if nxt is not None:
        return Turn(replies=[nxt])

    store.update(chat_id, phase="producing")
    return await produce_documentary(
        store, chat_id, interviewer, converter, scripter, narrator
    )
