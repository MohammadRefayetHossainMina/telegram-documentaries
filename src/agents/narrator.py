"""Narrator: Gemini TTS turned into a Telegram voice note.

This is a tool, not an agent. The script is read aloud by
gemini-3.1-flash-tts-preview and converted to OGG Opus, which Telegram
accepts for send_voice.
"""

import inspect
import logging
import shutil
import subprocess
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path

from google.genai import types as genai_types

from src.agents.gemini_io import first_inline, gemini_client
from src.errors import PipelineError

logger = logging.getLogger(__name__)

TTS_MODEL = "gemini-3.1-flash-tts-preview"
TTS_VOICE = "Charon"
TTS_STYLE = (
    "Speak with a deep male voice and a posh British accent, "
    "like a revered wildlife documentary narrator."
)

Speaker = Callable[[str], "bytes | Awaitable[bytes]"]


def _write_source(folder: Path, audio: bytes, mime: str) -> Path:
    if audio.startswith(b"RIFF") or "wav" in mime:
        path = folder / "in.wav"
        path.write_bytes(audio)
        return path
    path = folder / "in.pcm"
    path.write_bytes(audio)
    return path


def _ffmpeg_command(source: Path, dest: Path) -> list[str]:
    if source.suffix == ".pcm":
        return [
            "ffmpeg",
            "-y",
            "-f",
            "s16le",
            "-ar",
            "24000",
            "-ac",
            "1",
            "-i",
            str(source),
            "-c:a",
            "libopus",
            "-b:a",
            "48k",
            "-ac",
            "1",
            str(dest),
        ]
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-c:a",
        "libopus",
        "-b:a",
        "48k",
        "-ac",
        "1",
        str(dest),
    ]


def _ffmpeg_binary() -> str:
    """Return an ffmpeg executable, including the bundled one if present."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise PipelineError(
            "ffmpeg is missing, so the voice note cannot be built"
        ) from exc
    return str(imageio_ffmpeg.get_ffmpeg_exe())


def to_ogg_opus(audio: bytes, mime: str) -> bytes:
    """Return OGG Opus bytes. Audio that is already OGG is passed through."""
    if "ogg" in mime or audio.startswith(b"OggS"):
        return audio
    ffmpeg = _ffmpeg_binary()
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        source = _write_source(folder, audio, mime)
        dest = folder / "narration.ogg"
        command = _ffmpeg_command(source, dest)
        command[0] = ffmpeg
        completed = subprocess.run(command, check=False, capture_output=True)
        if completed.returncode != 0 or not dest.exists():
            detail = completed.stderr.decode("utf-8", errors="replace")[-400:]
            raise PipelineError(f"could not encode the voice note: {detail}")
        encoded = dest.read_bytes()
    logger.info("encoded voice note: %d bytes", len(encoded))
    return encoded


class Narrator:
    """Direct Gemini TTS call. A speaker can be injected for tests."""

    def __init__(
        self,
        *,
        model: str = TTS_MODEL,
        speaker: Speaker | None = None,
    ) -> None:
        self._model = model
        self._speaker = speaker or self._gemini_speak

    async def _gemini_speak(self, script: str) -> bytes:
        # Keep the client referenced until the audio is read. A temporary
        # client is closed by garbage collection before the HTTP send.
        client = gemini_client()
        response = await client.aio.models.generate_content(
            model=self._model,
            contents=(f"{TTS_STYLE}\n\n{script}"),
            config=genai_types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=genai_types.SpeechConfig(
                    voice_config=genai_types.VoiceConfig(
                        prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                            voice_name=TTS_VOICE,
                        )
                    )
                ),
            ),
        )
        data, mime = first_inline(response, "audio/")
        return to_ogg_opus(data, mime)

    async def speak(self, script: str) -> bytes:
        """Synthesize the script into OGG Opus bytes."""
        if not script.strip():
            raise PipelineError("narrator received an empty script")
        try:
            result = self._speaker(script)
            if inspect.isawaitable(result):
                result = await result
        except PipelineError:
            raise
        except Exception as exc:
            raise PipelineError(f"narrator failed: {exc}") from exc
        if not isinstance(result, bytes) or not result:
            raise PipelineError("narrator returned no audio")
        return result
