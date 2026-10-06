"""Small helpers around the Gemini client for image and audio bytes."""

import os

from google import genai

from src.errors import PipelineError


def gemini_client() -> genai.Client:
    """Build a client from GEMINI_API_KEY. Never logs the key."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise PipelineError("GEMINI_API_KEY missing from environment")
    return genai.Client(api_key=key)


def first_inline(response: object, mime_prefix: str) -> tuple[bytes, str]:
    """Return the first inline payload whose mime type matches the prefix."""
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            inline = getattr(part, "inline_data", None)
            if inline is None:
                continue
            data = getattr(inline, "data", None)
            mime = str(getattr(inline, "mime_type", "") or "")
            if isinstance(data, bytes) and data and mime.startswith(mime_prefix):
                return data, mime
    raise PipelineError(f"model returned no {mime_prefix} payload")
