# Narrator validation

The phase is accepted when the narration paragraph becomes an OGG voice note, and Telegram receives that voice note after the hybrid photo and the paragraph.

## Commands

From the repository root:

```bash
scripts/test tests/unit/test_pipeline.py::test_narrator_voice_call_holds_the_client tests/unit/test_pipeline.py::test_interview_asks_one_question_at_a_time_then_delivers
scripts/hooks
```

## Expected

- The speech call holds the Gemini client until the audio bytes are read.
- An OGG payload is returned unchanged.
- After six answers, the voice bytes are the Telegram voice note and the phase is `complete`.
- A missing portrait still leaves the phase at `producing`.
- `scripts/hooks` passes ruff, formatting, mypy, gitleaks, and pytest.

## Result

`scripts/test` on the voice-call and delivery cases: 2 passed.

`scripts/hooks` passed: ruff, ruff-format, mypy, gitleaks, and pytest. The full pytest run inside hooks was 13 passed.

## Recorded differences

- The Narrator is a direct Gemini speech call, not a Google ADK agent.
- The client is held for the whole call so garbage collection cannot close it early.
- On this computer, `ffmpeg` is not on the system path, so encoding uses the bundled `imageio-ffmpeg` binary when it is installed.
- Logging is inline on the encode path, not a decorator.
