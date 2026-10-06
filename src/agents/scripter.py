"""The Scripter: one-paragraph documentary narration (Phase 4)."""

import inspect
import logging
import re
import uuid
from collections.abc import Awaitable, Callable

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

from src.agents.interviewer import Dossier
from src.errors import PipelineError

logger = logging.getLogger(__name__)

SCRIPTER_MODEL = "gemini-3.1-flash-lite"
SCRIPTER_NAME = "scripter"
MAX_SCRIPT_WORDS = 90
SCRIPTER_INSTRUCTION = (
    "Write like a highly dramatic, British nature documentary narrator "
    "observing a wild beast. Frame the subject's quirks, bedtime habits, "
    "and snacking patterns as funny animal behaviours, intentionally "
    "making it sound like a nature documentary about humans. "
    "Output exactly one paragraph, maximum 90 words, no markdown, "
    "ready for voice synthesis."
)

Writer = Callable[[Dossier], "str | Awaitable[str]"]
_MARKDOWN_RE = re.compile(r"[*_`#]+")


def clean_script(raw: str) -> str:
    """Collapse a model reply into one paragraph of at most 90 words."""
    text = _MARKDOWN_RE.sub("", raw)
    text = " ".join(text.split())
    if not text:
        raise PipelineError("scripter returned an empty script")
    words = text.split(" ")
    if len(words) > MAX_SCRIPT_WORDS:
        text = " ".join(words[:MAX_SCRIPT_WORDS]).rstrip(",;:") + "."
    return text


class ScripterAgent:
    """Narration writer backed by a Google ADK agent."""

    def __init__(
        self,
        *,
        model: str = SCRIPTER_MODEL,
        writer: Writer | None = None,
    ) -> None:
        self._model = model
        self._writer = writer or self._adk_write

    async def _adk_write(self, dossier: Dossier) -> str:
        agent = Agent(
            name=SCRIPTER_NAME,
            model=self._model,
            instruction=SCRIPTER_INSTRUCTION,
        )
        runner = InMemoryRunner(agent=agent)
        session_id = f"script-{uuid.uuid4().hex}"
        await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id=SCRIPTER_NAME,
            session_id=session_id,
        )
        content = genai_types.Content(
            role="user",
            parts=[
                genai_types.Part.from_text(
                    text=(
                        f"Animal: {dossier.suggested_animal}\n"
                        f"Dossier: {dossier.summary}"
                    )
                )
            ],
        )
        text_parts: list[str] = []
        async for event in runner.run_async(
            user_id=SCRIPTER_NAME,
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response() and event.content is not None:
                for part in event.content.parts or []:
                    if part.text:
                        text_parts.append(part.text)
        if not text_parts:
            raise PipelineError("scripter returned no text")
        return "\n".join(text_parts)

    async def write_script(self, dossier: Dossier) -> str:
        """Return one narration paragraph, capped at 90 words."""
        try:
            result = self._writer(dossier)
            if inspect.isawaitable(result):
                result = await result
        except PipelineError:
            raise
        except Exception as exc:
            raise PipelineError(f"scripter failed: {exc}") from exc
        if not isinstance(result, str):
            raise PipelineError(f"writer returned {type(result).__name__}")
        script = clean_script(result)
        logger.info("script captured (%d words): %s", len(script.split()), script)
        return script
