"""Temporary per-chat media files (portrait, hybrid image, voice note)."""

import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "var/media"))
_ALLOWED = frozenset({"portrait.jpg", "hybrid.png", "narration.ogg"})


def chat_directory(chat_id: int) -> Path:
    """Return the media folder for one chat. chat_id is never used as a path."""
    return MEDIA_ROOT / str(int(chat_id))


def save_chat_file(chat_id: int, name: str, data: bytes) -> str:
    """Write one allowed media file and return its path."""
    if name not in _ALLOWED:
        raise ValueError(f"refusing to store unexpected media name: {name}")
    folder = chat_directory(chat_id)
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / name
    destination.write_bytes(data)
    logger.info("stored %s (%d bytes) for chat_id=%s", name, len(data), chat_id)
    return str(destination)


def purge_chat(chat_id: int) -> None:
    """Delete a chat's temporary media. Missing folders are fine."""
    folder = chat_directory(chat_id)
    if not folder.exists():
        return
    shutil.rmtree(folder)
    logger.info("purged temporary media for chat_id=%s", chat_id)
