# Scripter validation

The phase is accepted when the dossier becomes one narration paragraph of at most 90 words, and that paragraph is the text Telegram sends after the hybrid photo.

## Commands

From the repository root:

```bash
scripts/test tests/unit/test_pipeline.py::test_clean_script_strips_markdown_and_caps_words tests/unit/test_pipeline.py::test_interview_asks_one_question_at_a_time_then_delivers
scripts/hooks
```

## Expected

- Markdown is stripped and a long reply is cut to 90 words.
- After six answers, the Telegram text is the script and the session stores it.
- `scripts/hooks` passes ruff, formatting, mypy, gitleaks, and pytest.

## Result

`scripts/test` on the cleanup and delivery cases: 2 passed.

`scripts/hooks` passed: ruff, ruff-format, mypy, gitleaks, and pytest. The full pytest run inside hooks was 13 passed.

## Recorded differences

- The Scripter is a Google ADK agent. The Converter and the Narrator are not.
- Logging is inline on the write path, not a decorator.
