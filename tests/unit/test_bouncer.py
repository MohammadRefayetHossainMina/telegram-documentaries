"""Unit tests for the Bouncer (vision routing) domain logic.

All tests are hermetic: no live Gemini / ADK network calls are made.
The ADK agent's model classifier is replaced by injected fakes.
"""

import pytest

from src.agents.bouncer import (
    PHOTO_APPROVED_REPLY,
    BouncerAgent,
    BouncerDecision,
    BouncerError,
    BouncerVerdict,
    decide_reply,
    parse_verdict,
    rejection_reply,
)


class TestParseVerdict:
    def test_human_photo_parses_to_true(self) -> None:
        raw = '{"contains_human": true, "reason": "A person is clearly visible."}'
        verdict = parse_verdict(raw)
        assert verdict.contains_human is True
        assert verdict.reason == "A person is clearly visible."

    def test_non_human_photo_parses_to_false(self) -> None:
        raw = '{"contains_human": false, "reason": "It is a cat."}'
        verdict = parse_verdict(raw)
        assert verdict.contains_human is False
        assert verdict.reason == "It is a cat."

    def test_fenced_json_is_tolerated(self) -> None:
        raw = '```json\n{"contains_human": false, "reason": "A coffee mug."}\n```'
        assert parse_verdict(raw).contains_human is False

    def test_stray_text_around_json_is_tolerated(self) -> None:
        raw = 'Sure! {"contains_human": true, "reason": "Human present"} — done.'
        assert parse_verdict(raw).contains_human is True

    @pytest.mark.parametrize(
        "garbage",
        [
            "",
            "nope",
            "{not json",
            '{"contains_human": "maybe", "reason": "x"}',
            "[]",
            '{"reason": "missing bool field"}',
        ],
    )
    def test_invalid_response_raises_bouncer_error(self, garbage: str) -> None:
        with pytest.raises(BouncerError):
            parse_verdict(garbage)


class TestDecideReply:
    def test_human_verdict_routes_to_confirmation(self) -> None:
        decision = decide_reply(BouncerVerdict(contains_human=True, reason="A human."))
        assert isinstance(decision, BouncerDecision)
        assert decision.approved is True
        assert decision.reply == PHOTO_APPROVED_REPLY

    def test_non_human_verdict_routes_to_rejection_with_reason(self) -> None:
        decision = decide_reply(
            BouncerVerdict(contains_human=False, reason="It is a cat.")
        )
        assert decision.approved is False
        assert decision.reply == rejection_reply("It is a cat.")
        assert "It is a cat." in decision.reply


class TestBouncerAgent:
    async def test_classify_uses_injected_async_classifier(self) -> None:
        seen: list[bytes] = []

        async def fake(image: bytes) -> BouncerVerdict:
            seen.append(image)
            return BouncerVerdict(contains_human=True, reason="Person found.")

        agent = BouncerAgent(classifier=fake)

        verdict = await agent.classify(b"fake-jpeg-bytes")

        assert verdict.contains_human is True
        assert verdict.reason == "Person found."
        assert seen == [b"fake-jpeg-bytes"]

    async def test_classify_supports_synchronous_classifier(self) -> None:
        def fake(_image: bytes) -> BouncerVerdict:
            return BouncerVerdict(contains_human=False, reason="A car.")

        agent = BouncerAgent(classifier=fake)

        assert (await agent.classify(b"jpg")).contains_human is False

    async def test_classify_rejects_empty_bytes(self) -> None:
        async def fake(_image: bytes) -> BouncerVerdict:
            return BouncerVerdict(contains_human=True, reason="never reached")

        with pytest.raises(BouncerError):
            await BouncerAgent(classifier=fake).classify(b"")

    async def test_classify_unexpected_classifier_output_raises_safely(self) -> None:
        async def fake(_image: bytes) -> BouncerVerdict:
            return "not a verdict"  # type: ignore[return-value]

        with pytest.raises(BouncerError):
            await BouncerAgent(classifier=fake).classify(b"jpg")

    async def test_classify_wraps_classifier_exceptions_as_bouncer_error(self) -> None:
        async def fake(_image: bytes) -> BouncerVerdict:
            raise RuntimeError("model exploded")

        with pytest.raises(BouncerError, match="model exploded"):
            await BouncerAgent(classifier=fake).classify(b"jpg")
