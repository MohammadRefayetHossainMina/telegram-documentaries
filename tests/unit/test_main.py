"""Unit tests for the walking skeleton entrypoint."""

from src.main import greeting


def test_greeting_returns_hardcoded_reply() -> None:
    assert greeting() == "hey mate!"
