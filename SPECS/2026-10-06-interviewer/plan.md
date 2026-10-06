# Interviewer plan

Checks use `scripts/test` and `scripts/hooks`.

## 1. Questions

- `question_at(0)` through `question_at(5)` return one numbered question each.
- `question_at(6)` returns nothing. The interview is finished.

## 2. Session

- An approved portrait sets the chat to `interviewing` and asks question 1.
- Each answer is appended and `question_index` becomes the number of answers.
- A blank answer does not change the session.
- Text before a portrait asks for a photo.
- `/restart` clears that chat’s answers and temporary files.

## 3. Dossier

- `summarize` refuses to run before six answers.
- Bare JSON, fenced JSON, and JSON wrapped in prose all parse into `Dossier`.
- Missing fields, empty text, or a failed model call raise `PipelineError`.
- The session stores `dossier` and `suggested_animal`.

## 4. Validate

- `scripts/test` covers `tests/unit/test_pipeline.py`.
- `scripts/hooks` is green before merge.
