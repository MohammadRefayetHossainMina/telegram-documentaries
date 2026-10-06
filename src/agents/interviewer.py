"""The Interviewer: orchestrator and profiling agent (Phase 3).

Asks one field question at a time, then asks Gemini 3.1 Flash Lite for a
behavioural dossier and a suggested animal. The live summary runs through
Google ADK. Tests inject a summarizer so no network call is made.
"""

import inspect
import json
import logging
import re
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types
from pydantic import BaseModel, ValidationError

from src.errors import PipelineError

logger = logging.getLogger(__name__)

INTERVIEWER_MODEL = "gemini-3.1-flash-lite"
INTERVIEWER_NAME = "interviewer"
INTERVIEWER_INSTRUCTION = (
    "You are an eccentric wildlife-documentary researcher building a "
    "behavioural dossier. You receive numbered answers about one human. "
    "Reply with ONLY a JSON object of the form "
    '{"summary": "<one paragraph>", "suggested_animal": "<animal>"}. '
    "The summary must reflect their sleep, snacks, and daily habits. "
    "suggested_animal is the animal they should be transformed into, "
    "as a short phrase such as 'caffeinated badger'."
)

QUESTIONS: tuple[str, ...] = (
    "What time do you usually fall asleep, and what drags you out of bed?",
    "What do you snack on when you think nobody is watching?",
    "Describe the first ten minutes after you wake up.",
    "What tiny ritual do you repeat every single day?",
    "When something annoys you, what do your hands or your voice do?",
    "If your home were a wild territory, which corner is unmistakably yours?",
)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class Dossier(BaseModel):
    """Typed handoff from the Interviewer to Converter and Scripter."""

    summary: str
    suggested_animal: str


Summarizer = Callable[[list[str]], "Dossier | Awaitable[Dossier]"]


def question_at(index: int) -> str | None:
    """Return one numbered question, or None when the interview is finished."""
    if index < 0 or index >= len(QUESTIONS):
        return None
    total = len(QUESTIONS)
    return f"Field note {index + 1} of {total}: {QUESTIONS[index]}"


def parse_dossier(raw: str) -> Dossier:
    """Parse a model response into a Dossier, tolerating fenced JSON."""
    match = _JSON_RE.search(raw)
    if match is None:
        raise PipelineError(f"no JSON object in interviewer response: {raw[:200]!r}")
    try:
        data: dict[str, Any] = json.loads(match.group(0))
        dossier = Dossier.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise PipelineError(f"unparseable dossier: {exc}") from exc
    if not dossier.summary.strip() or not dossier.suggested_animal.strip():
        raise PipelineError("dossier was missing a summary or an animal")
    return dossier


class InterviewerAgent:
    """Interview orchestrator backed by a Google ADK agent."""

    def __init__(
        self,
        *,
        model: str = INTERVIEWER_MODEL,
        summarizer: Summarizer | None = None,
    ) -> None:
        self._model = model
        self._summarizer = summarizer or self._adk_summarize

    async def _adk_summarize(self, answers: list[str]) -> Dossier:
        numbered = "\n".join(
            f"{index}. {answer}" for index, answer in enumerate(answers, start=1)
        )
        agent = Agent(
            name=INTERVIEWER_NAME,
            model=self._model,
            instruction=INTERVIEWER_INSTRUCTION,
        )
        runner = InMemoryRunner(agent=agent)
        session_id = f"interview-{uuid.uuid4().hex}"
        await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id=INTERVIEWER_NAME,
            session_id=session_id,
        )
        content = genai_types.Content(
            role="user",
            parts=[
                genai_types.Part.from_text(
                    text=(
                        "Compile the behavioural dossier and suggested animal "
                        f"from these answers:\n{numbered}"
                    )
                )
            ],
        )
        text_parts: list[str] = []
        async for event in runner.run_async(
            user_id=INTERVIEWER_NAME,
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response() and event.content is not None:
                for part in event.content.parts or []:
                    if part.text:
                        text_parts.append(part.text)
        if not text_parts:
            raise PipelineError("interviewer returned no text")
        return parse_dossier("\n".join(text_parts))

    async def summarize(self, answers: list[str]) -> Dossier:
        """Turn collected answers into a dossier and a suggested animal."""
        if len(answers) < len(QUESTIONS):
            raise PipelineError("interview is not finished")
        try:
            result = self._summarizer(answers)
            if inspect.isawaitable(result):
                result = await result
        except PipelineError:
            raise
        except Exception as exc:
            raise PipelineError(f"interviewer failed: {exc}") from exc
        if not isinstance(result, Dossier):
            raise PipelineError(f"summarizer returned {type(result).__name__}")
        logger.info(
            "dossier ready: animal=%r summary=%r",
            result.suggested_animal,
            result.summary[:80],
        )
        return result
