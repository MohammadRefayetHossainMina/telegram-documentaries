# Converter validation

The phase is accepted when the original portrait and the dossier produce a hybrid image, that image is saved, and the chat receives it as a photo.

## Commands

From the repository root:

```bash
scripts/test tests/unit/test_pipeline.py::test_interview_asks_one_question_at_a_time_then_delivers tests/unit/test_pipeline.py::test_production_failure_keeps_the_session_retryable
scripts/hooks
```

## Expected

- After six answers, `hybrid.png` exists and its bytes are the Telegram photo.
- The injected renderer is called with the original portrait bytes and the dossier.
- A missing portrait is logged, no photo is sent, and the phase stays `producing`.
- `scripts/hooks` passes ruff, formatting, mypy, gitleaks, and pytest.

## Result

`scripts/test` on the delivery and retry cases: 2 passed.

`scripts/hooks` passed: ruff, ruff-format, mypy, gitleaks, and pytest.

## Recorded differences

- The Converter is a direct Gemini call, not a Google ADK agent.
- Logging is inline on the render path, not a decorator.
