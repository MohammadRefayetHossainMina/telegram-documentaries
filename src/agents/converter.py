"""The Converter: portrait plus dossier becomes a hybrid animal still.

Gemini 3.1 Flash Image receives the original photo and the dossier in one
call. There is no intermediate text-to-image prompt hop.
"""

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable

from google.genai import types as genai_types

from src.agents.gemini_io import first_inline, gemini_client
from src.agents.interviewer import Dossier
from src.errors import PipelineError

logger = logging.getLogger(__name__)

CONVERTER_MODEL = "gemini-3.1-flash-image"

Renderer = Callable[[bytes, Dossier], "bytes | Awaitable[bytes]"]


def converter_prompt(dossier: Dossier) -> str:
    """Instruction sent with the raw portrait in the same model call."""
    return (
        "Create one wildlife-documentary still. Keep this person's likeness "
        f"and transform them into a hybrid {dossier.suggested_animal}. "
        f"Personality to show in posture and setting: {dossier.summary} "
        "Photorealistic, a single subject, no text, no watermark, no collage."
    )


class ConverterAgent:
    """Multimodal portrait fusion. A renderer can be injected for tests."""

    def __init__(
        self,
        *,
        model: str = CONVERTER_MODEL,
        renderer: Renderer | None = None,
    ) -> None:
        self._model = model
        self._renderer = renderer or self._gemini_render

    def _gemini_render_sync(self, image_bytes: bytes, dossier: Dossier) -> bytes:
        response = gemini_client().models.generate_content(
            model=self._model,
            contents=[
                genai_types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                genai_types.Part.from_text(text=converter_prompt(dossier)),
            ],
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )
        data, mime = first_inline(response, "image/")
        logger.info("converter image ready: %d bytes (%s)", len(data), mime)
        return data

    async def _gemini_render(self, image_bytes: bytes, dossier: Dossier) -> bytes:
        return await asyncio.to_thread(self._gemini_render_sync, image_bytes, dossier)

    async def render(self, image_bytes: bytes, dossier: Dossier) -> bytes:
        """Fuse the portrait and dossier into hybrid image bytes."""
        if not image_bytes:
            raise PipelineError("converter received an empty portrait")
        try:
            result = self._renderer(image_bytes, dossier)
            if inspect.isawaitable(result):
                result = await result
        except PipelineError:
            raise
        except Exception as exc:
            raise PipelineError(f"converter failed: {exc}") from exc
        if not isinstance(result, bytes) or not result:
            raise PipelineError("converter returned no image")
        return result
