"""Unit tests for the in-memory per-chat session state driver."""

from src.state.session_store import SessionStore


def test_default_state_is_versioned_and_idle() -> None:
    store = SessionStore()
    state = store.get(42)
    assert state.version == 1
    assert state.phase == "idle"


def test_state_is_isolated_per_chat_id() -> None:
    store = SessionStore()
    store.set_phase(1, "human_confirmed")
    assert store.get(1).phase == "human_confirmed"
    # A different chat is untouched.
    assert store.get(2).phase == "idle"


def test_reset_clears_chat_state_back_to_idle() -> None:
    store = SessionStore()
    store.set_phase(1, "human_confirmed")
    store.reset(1)
    assert store.get(1).phase == "idle"
