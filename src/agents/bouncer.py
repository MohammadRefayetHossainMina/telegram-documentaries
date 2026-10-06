"""The Bouncer: vision routing agent (SPECS/TECH.md, Phase 2).

A Google ADK agent that classifies an uploaded photo as containing a
discernible human subject or not, returning a structured verdict that
the gateway uses to route the pipeline (positive -> approve, negative ->
humorous rejection). The live classifier runs through
`google.adk.runners.InMemoryRunner` around the flash-lite Gemini model;
a classifier can be injected for hermetic tests.
"""

import inspect
import json
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

BOUNCER_MODEL = "gemini-3.1-flash-lite"
BOUNCER_NAME = "bouncer"
BOUNCER_INSTRUCTION = (
    "You are the Bouncer of a comedy wildlife-documentary bot. "
    "Judge whether the photo contains a discernible human subject: a "
    "recognizable person, face, or human figure. "
    "Reply with ONLY a JSON object of the form "
    '{"contains_human": true|false, "reason": "<short reason>"}. '
    'When contains_human is false, make "reason" friendly and playful '
    "(the bot shows it to the user) — e.g. about a cat, an object, a "
    "landscape, or a vehicle."
)

# User-facing routing messages. The confirmation keeps the walking
# skeleton's friendly tone so text flows stay consistent.
PHOTO_APPROVED_REPLY = (
    "hey mate! Human spotted — this photo passes the Bouncer. "
    "Documentary prep is under way."
)
BOUNCER_ERROR_REPLY = (
    "Hmm, my eyes glazed over for a second and I couldn't quite make "
    "out that photo. Please try sending it again."
)

_STRAY_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

# Callable that turns raw image bytes into a verdict. May be sync or async.
Classifier = Callable[[bytes], "BouncerVerdict | Awaitable[BouncerVerdict]"]


class BouncerVerdict(BaseModel):
    """Structured decision contract of the Bouncer (routing contract)."""

    contains_human: bool
    reason: str


class BouncerError(Exception):
    """Raised when the vision model response cannot be interpreted."""


@dataclass(frozen=True)
class BouncerDecision:
    """Routing decision derived from a verdict."""

    reply: str
    approved: bool


def parse_verdict(raw: str) -> BouncerVerdict:
    """Parse a model response into a BouncerVerdict, tolerating noise.

    The model is instructed to return bare JSON, but may wrap it in
    fenced code blocks or stray prose, so the first JSON object in the
    response is extracted. Raises BouncerError when none can be found
    or it does not match the contract.
    """
    match = _STRAY_JSON_RE.search(raw)
    if match is None:
        raise BouncerError(f"no JSON object in model response: {raw[:200]!r}")
    try:
        data: dict[str, Any] = json.loads(match.group(0))
        return BouncerVerdict.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise BouncerError(f"unparseable model response: {exc}") from exc


def rejection_reply(reason: str) -> str:
    """Wrap the model's reason in a friendly, humorous rejection."""
    return (
        f"Ha! {reason} This has no place in a human documentary — "
        "I only film humans. Try a selfie!"
    )


def decide_reply(verdict: BouncerVerdict) -> BouncerDecision:
    """Turn a verdict into the reply text and routing outcome."""
    if verdict.contains_human:
        return BouncerDecision(approved=True, reply=PHOTO_APPROVED_REPLY)
    return BouncerDecision(approved=False, reply=rejection_reply(verdict.reason))


class BouncerAgent:
    """Bouncer as a Google ADK agent (model + instruction + runner).

    The live classifier sends the photo to the ADK model via
    InMemoryRunner and parses the final response into a verdict. For
    tests a classifier (sync or async, returning a BouncerVerdict) can
    be injected so no live API call happens.
    """

    def __init__(
        self,
        *,
        model: str = BOUNCER_MODEL,
        classifier: Classifier | None = None,
    ) -> None:
        self._model = model
        self._classifier = classifier or self._adk_classify

    async def _adk_classify(self, image_bytes: bytes) -> BouncerVerdict:
        """Classify via the ADK agent: send image + probe, read final text."""
        agent = Agent(
            name=BOUNCER_NAME, model=self._model, instruction=BOUNCER_INSTRUCTION
        )
        runner = InMemoryRunner(agent=agent)
        await runner.session_service.create_session(
            app_name=runner.app_name, user_id=BOUNCER_NAME, session_id=BOUNCER_NAME
        )
        content = genai_types.Content(
            role="user",
            parts=[
                genai_types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                genai_types.Part.from_text(
                    text="Is there a discernible human subject in this photo?"
                ),
            ],
        )
        text_parts: list[str] = []
        async for event in runner.run_async(
            user_id=BOUNCER_NAME, session_id=BOUNCER_NAME, new_message=content
        ):
            if event.is_final_response() and event.content is not None:
                for part in event.content.parts or []:
                    if part.text:
                        text_parts.append(part.text)
        if not text_parts:
            raise BouncerError("model returned no text response")
        return parse_verdict("\n".join(text_parts))

    async def classify(self, image_bytes: bytes) -> BouncerVerdict:
        """Classify image bytes into a structured verdict (never raises
        on bad input, only BouncerError)."""
        if not image_bytes:
            raise BouncerError("empty image bytes")
        try:
            result = self._classifier(image_bytes)
            if inspect.isawaitable(result):
                result = await result
        except BouncerError:
            raise
        except Exception as exc:  # any unexpected classifier failure
            raise BouncerError(f"classifier failed: {exc}") from exc
        if not isinstance(result, BouncerVerdict):
            raise BouncerError(f"classifier returned {type(result).__name__}")
        logger.info(
            "bouncer verdict: contains_human=%s reason=%r",
            result.contains_human,
            result.reason[:80],
        )
        return result
