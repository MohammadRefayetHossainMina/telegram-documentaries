"""Routing tests: photo bytes in, Telegram-friendly reply + state out.

Exercises the pieces of src.main that do NOT need a live Telegram
connection: the Bouncer is replaced by a fake classifier and the
reply sink is captured in-memory.
"""

from pathlib import Path

import pytest

from src import main as gateway
from src.agents.bouncer import (
    BOUNCER_ERROR_REPLY,
    PHOTO_APPROVED_REPLY,
    BouncerAgent,
    BouncerError,
    BouncerVerdict,
    rejection_reply,
)
from src.agents.interviewer import question_at
from src.state import media
from src.state.session_store import SessionStore


def _capture() -> tuple[list[str], object]:
    sent: list[str] = []

    async def reply(text: str) -> None:
        sent.append(text)

    return sent, reply


@pytest.fixture(autouse=True)
def _fresh_store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(gateway, "STORE", SessionStore())
    monkeypatch.setattr(media, "MEDIA_ROOT", tmp_path)


def _install_fake(
    monkeypatch: pytest.MonkeyPatch,
    verdict: BouncerVerdict | None,
    *,
    raise_error: bool = False,
) -> None:
    async def fake(_image: bytes) -> BouncerVerdict:
        if raise_error:
            raise BouncerError("model unreachable")
        assert verdict is not None
        return verdict

    monkeypatch.setattr(gateway, "BOUNCER", BouncerAgent(classifier=fake))


async def test_non_human_photo_is_rejected_with_reason_and_state_resets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway.STORE.set_phase(7, "human_confirmed")
    _install_fake(
        monkeypatch, BouncerVerdict(contains_human=False, reason="It is a cat.")
    )
    sent, reply = _capture()

    await gateway.process_photo(b"jpg-bytes", 7, reply)  # type: ignore[arg-type]

    assert sent == [rejection_reply("It is a cat.")]
    assert "It is a cat." in sent[0]
    assert gateway.STORE.get(7).phase == "idle"


async def test_human_photo_is_approved_and_interview_starts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake(
        monkeypatch, BouncerVerdict(contains_human=True, reason="Person visible.")
    )
    sent, reply = _capture()

    await gateway.process_photo(b"jpg-bytes", 9, reply)  # type: ignore[arg-type]

    assert sent == [PHOTO_APPROVED_REPLY, question_at(0)]
    state = gateway.STORE.get(9)
    assert state.phase == "interviewing"
    assert state.photo_path is not None
    assert Path(state.photo_path).read_bytes() == b"jpg-bytes"


async def test_classifier_failure_replies_safely_and_resets_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway.STORE.set_phase(11, "human_confirmed")
    _install_fake(monkeypatch, None, raise_error=True)
    sent, reply = _capture()

    await gateway.process_photo(b"jpg-bytes", 11, reply)  # type: ignore[arg-type]

    assert sent == [BOUNCER_ERROR_REPLY]
    assert gateway.STORE.get(11).phase == "idle"
