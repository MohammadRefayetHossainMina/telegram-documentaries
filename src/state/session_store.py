"""In-memory per-chat session state driver.

Per SPECS/TECH.md: a single shared driver, keyed by chat_id, holding
ephemeral session state in memory. /start and /restart drop that state
and the chat's temporary media without stopping the process.
"""

import logging
import threading
from typing import Any, Final, Literal

from pydantic import BaseModel, Field

from src.state.media import purge_chat

logger = logging.getLogger(__name__)

STATE_VERSION: Final[int] = 1
SessionPhase = Literal[
    "idle",
    "human_confirmed",
    "interviewing",
    "producing",
    "complete",
]


class SessionState(BaseModel):
    """Versioned per-chat session state."""

    version: int = STATE_VERSION
    phase: SessionPhase = "idle"
    question_index: int = 0
    answers: list[str] = Field(default_factory=list)
    photo_path: str | None = None
    dossier: str | None = None
    suggested_animal: str | None = None
    script: str | None = None
    media_paths: list[str] = Field(default_factory=list)


class SessionStore:
    """Thread-safe in-memory store of SessionState keyed by chat_id."""

    def __init__(self) -> None:
        self._sessions: dict[int, SessionState] = {}
        self._lock = threading.Lock()

    def get(self, chat_id: int) -> SessionState:
        """Return the state for a chat, creating a fresh idle one if absent."""
        with self._lock:
            return self._sessions.setdefault(chat_id, SessionState())

    def set_phase(self, chat_id: int, phase: SessionPhase) -> SessionState:
        """Set the phase for a chat and return the new state."""
        return self.update(chat_id, phase=phase)

    def update(
        self,
        chat_id: int,
        *,
        phase: SessionPhase | None = None,
        question_index: int | None = None,
        answers: list[str] | None = None,
        photo_path: str | None = None,
        dossier: str | None = None,
        suggested_animal: str | None = None,
        script: str | None = None,
        media_paths: list[str] | None = None,
    ) -> SessionState:
        """Replace selected fields, keeping everything else."""
        changes: dict[str, Any] = {}
        if phase is not None:
            changes["phase"] = phase
        if question_index is not None:
            changes["question_index"] = question_index
        if answers is not None:
            changes["answers"] = answers
        if photo_path is not None:
            changes["photo_path"] = photo_path
        if dossier is not None:
            changes["dossier"] = dossier
        if suggested_animal is not None:
            changes["suggested_animal"] = suggested_animal
        if script is not None:
            changes["script"] = script
        if media_paths is not None:
            changes["media_paths"] = media_paths
        with self._lock:
            current = self._sessions.get(chat_id, SessionState())
            updated = current.model_copy(update=changes)
            self._sessions[chat_id] = updated
            return updated

    def add_answer(self, chat_id: int, answer: str) -> SessionState:
        """Append one interview answer and advance the question index."""
        with self._lock:
            current = self._sessions.get(chat_id, SessionState())
            answers = [*current.answers, answer.strip()]
            updated = current.model_copy(
                update={"answers": answers, "question_index": len(answers)}
            )
            self._sessions[chat_id] = updated
            return updated

    def reset(self, chat_id: int) -> None:
        """Drop a chat's session state and temporary media."""
        try:
            purge_chat(chat_id)
        except OSError:
            logger.exception("could not purge media for chat_id=%s", chat_id)
        with self._lock:
            self._sessions.pop(chat_id, None)
