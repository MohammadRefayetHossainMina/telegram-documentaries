# Scripter plan

Checks use `scripts/test` and `scripts/hooks`.

## 1. One ADK call

- The model is `gemini-3.1-flash-lite`.
- The agent name is `scripter`.
- The user message names `suggested_animal` and `summary`.
- The instruction asks for one paragraph, a maximum of 90 words, and no markdown.

## 2. Cleanup

- Markdown marks are removed and whitespace is collapsed.
- More than 90 words is cut to 90 and closed with a period.
- An empty reply raises `PipelineError`.

## 3. Delivery

- The paragraph is stored on the session as `script`.
- Telegram receives it as a text message after the hybrid photo and before the voice note.
- A failed write leaves the chat in `producing`.

## 4. Validate

- `scripts/test` covers `clean_script` and the delivery case in `tests/unit/test_pipeline.py`.
- `scripts/hooks` is green before merge.
