"""Unit tests for the interview state machine and documentary handoff."""

import asyncio
from pathlib import Path

import pytest

from src.agents.converter import ConverterAgent
from src.agents.interviewer import Dossier, InterviewerAgent, question_at
from src.agents.narrator import Narrator
from src.agents.scripter import ScripterAgent, clean_script
from src.pipeline import (
    ASK_FOR_PHOTO,
    DONE_REPLY,
    PHOTO_DURING_INTERVIEW,
    Turn,
    handle_text,
    photo_block_message,
    produce_documentary,
)
from src.state import media
from src.state.session_store import SessionStore

DOSSIER = Dossier(summary="Sleeps late and hoards biscuits.", suggested_animal="badger")
SCRIPT = "In the blue hour a badger of a person patrols the biscuit tin."
IMAGE = b"\x89PNG-hybrid"
VOICE = b"OggS-voice"


def _agents() -> tuple[InterviewerAgent, ConverterAgent, ScripterAgent, Narrator]:
    async def summarize(_answers: list[str]) -> Dossier:
        return DOSSIER

    async def render(_image: bytes, _dossier: Dossier) -> bytes:
        return IMAGE

    async def write(_dossier: Dossier) -> str:
        return SCRIPT

    async def speak(_script: str) -> bytes:
        return VOICE

    return (
        InterviewerAgent(summarizer=summarize),
        ConverterAgent(renderer=render),
        ScripterAgent(writer=write),
        Narrator(speaker=speak),
    )


def test_question_count_is_between_five_and_seven() -> None:
    assert question_at(0) is not None
    assert question_at(5) is not None
    assert question_at(6) is None
    assert "1 of 6" in (question_at(0) or "")
    assert "6 of 6" in (question_at(5) or "")


def test_clean_script_strips_markdown_and_caps_words() -> None:
    raw = "**Hello** " + " ".join(f"word{i}" for i in range(120))
    cleaned = clean_script(raw)
    assert "*" not in cleaned
    assert len(cleaned.split()) == 90
    assert cleaned.endswith(".")


def test_photo_during_interview_is_blocked() -> None:
    assert photo_block_message("interviewing") == PHOTO_DURING_INTERVIEW
    assert photo_block_message("producing") == PHOTO_DURING_INTERVIEW
    assert photo_block_message("idle") is None


async def test_idle_text_asks_for_a_portrait() -> None:
    store = SessionStore()
    agents = _agents()
    turn = await handle_text(store, 1, "hello", *agents)
    assert turn.replies == [ASK_FOR_PHOTO]
    assert turn.photos == []
    assert turn.voices == []


async def test_interview_asks_one_question_at_a_time_then_delivers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(media, "MEDIA_ROOT", tmp_path)
    store = SessionStore()
    portrait = media.save_chat_file(3, "portrait.jpg", b"jpeg-bytes")
    store.update(
        3,
        phase="interviewing",
        question_index=0,
        photo_path=portrait,
        media_paths=[portrait],
    )
    agents = _agents()

    for index in range(5):
        turn = await handle_text(store, 3, f"answer {index}", *agents)
        assert turn.replies == [question_at(index + 1)]
        assert turn.photos == []
        assert store.get(3).phase == "interviewing"

    turn = await handle_text(store, 3, "the corner by the window", *agents)

    assert turn.photos == [IMAGE]
    assert turn.replies == [SCRIPT]
    assert turn.voices == [VOICE]
    assert store.get(3).phase == "complete"
    assert store.get(3).script == SCRIPT
    assert store.get(3).suggested_animal == "badger"
    assert Path(store.get(3).media_paths[1]).read_bytes() == IMAGE


async def test_complete_chat_does_not_restart_itself() -> None:
    store = SessionStore()
    store.update(4, phase="complete")
    turn = await handle_text(store, 4, "again?", *_agents())
    assert turn.replies == [DONE_REPLY]


async def test_production_failure_keeps_the_session_retryable() -> None:
    store = SessionStore()
    store.update(
        8,
        phase="producing",
        photo_path="missing.jpg",
        answers=["a", "b", "c", "d", "e", "f"],
    )

    async def summarize(_answers: list[str]) -> Dossier:
        return DOSSIER

    turn = await produce_documentary(
        store,
        8,
        InterviewerAgent(summarizer=summarize),
        ConverterAgent(renderer=lambda _i, _d: b"png"),
        ScripterAgent(writer=lambda _d: SCRIPT),
        Narrator(speaker=lambda _s: VOICE),
    )
    assert "cutting room" in turn.replies[0]
    assert store.get(8).phase == "producing"


def test_reset_deletes_temporary_media(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(media, "MEDIA_ROOT", tmp_path)
    store = SessionStore()
    path = media.save_chat_file(9, "portrait.jpg", b"jpeg")
    store.update(9, phase="interviewing", photo_path=path)
    assert Path(path).exists()
    store.reset(9)
    assert not Path(path).exists()
    assert store.get(9).phase == "idle"


async def test_converter_image_call_holds_the_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inline = type("Inline", (), {"data": b"\x89PNG-hybrid", "mime_type": "image/png"})()
    part = type("Part", (), {"inline_data": inline})()
    content = type("Content", (), {"parts": [part]})()
    candidate = type("Candidate", (), {"content": content})()
    response = type("Response", (), {"candidates": [candidate]})()

    class _Models:
        async def generate_content(self, **_kwargs: object) -> object:
            return response

    class _Aio:
        models = _Models()

    class _Client:
        aio = _Aio()

    monkeypatch.setattr("src.agents.converter.gemini_client", lambda: _Client())

    image = await ConverterAgent().render(b"jpeg-bytes", DOSSIER)

    assert image == b"\x89PNG-hybrid"


async def test_narrator_voice_call_holds_the_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inline = type("Inline", (), {"data": b"OggS-voice", "mime_type": "audio/ogg"})()
    part = type("Part", (), {"inline_data": inline})()
    content = type("Content", (), {"parts": [part]})()
    candidate = type("Candidate", (), {"content": content})()
    response = type("Response", (), {"candidates": [candidate]})()

    class _Models:
        async def generate_content(self, **_kwargs: object) -> object:
            return response

    class _Aio:
        models = _Models()

    class _Client:
        aio = _Aio()

    monkeypatch.setattr("src.agents.narrator.gemini_client", lambda: _Client())

    audio = await Narrator().speak(SCRIPT)

    assert audio == b"OggS-voice"


async def test_picture_and_voice_are_made_together(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(media, "MEDIA_ROOT", tmp_path)
    store = SessionStore()
    portrait = media.save_chat_file(12, "portrait.jpg", b"jpeg-bytes")
    store.update(
        12,
        phase="producing",
        question_index=6,
        answers=["a", "b", "c", "d", "e", "f"],
        photo_path=portrait,
        media_paths=[portrait],
    )
    order: list[str] = []

    async def render(_image: bytes, _dossier: Dossier) -> bytes:
        order.append("image-start")
        await asyncio.sleep(0.05)
        order.append("image-end")
        return IMAGE

    async def write(_dossier: Dossier) -> str:
        order.append("script")
        return SCRIPT

    async def speak(_script: str) -> bytes:
        order.append("voice-start")
        await asyncio.sleep(0.05)
        order.append("voice-end")
        return VOICE

    sent: list[Turn] = []

    async def emit(piece: Turn) -> None:
        sent.append(piece)

    turn = await produce_documentary(
        store,
        12,
        InterviewerAgent(summarizer=lambda _answers: DOSSIER),
        ConverterAgent(renderer=render),
        ScripterAgent(writer=write),
        Narrator(speaker=speak),
        emit,
    )

    assert order.index("voice-start") < order.index("image-end")
    assert [piece.photos for piece in sent] == [[IMAGE], [], []]
    assert [piece.replies for piece in sent] == [[], [SCRIPT], []]
    assert [piece.voices for piece in sent] == [[], [], [VOICE]]
    assert turn.sent is True
    assert store.get(12).phase == "complete"
