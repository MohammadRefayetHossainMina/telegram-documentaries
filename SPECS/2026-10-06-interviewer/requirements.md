# Interviewer

The agent that runs after the Bouncer approves a portrait. It asks six questions, one at a time, then asks Gemini for a behavioural dossier and a suggested animal.

## Scope

- Ask between five and seven questions. This bot asks six.
- Send one question per message. Number it `Field note N of 6`.
- Store each non-empty answer on that chat’s session.
- Ignore a blank answer and do not advance.
- When all six answers are in, call `gemini-3.1-flash-lite` through a Google ADK agent.
- Parse the model reply into a typed `Dossier`: `summary` and `suggested_animal`.
- Save both fields on the session, then hand off to production.
- Tests inject a summarizer. They do not call Gemini.

## Out of scope

- Reading the portrait for visual attributes. The photo stays on disk for the Converter.
- The hybrid image, the narration paragraph, and the voice note.

## Contract

Untrusted model text is parsed at the edge into `Dossier`. Callers receive that model, or `PipelineError`. They do not receive a raw dict.

## Decisions

- The question list is fixed, so the bot cannot dump every question in one message.
- A regex only locates a JSON object inside noisy model text. Pydantic validates the object.
- The dossier is written when the interview finishes, not after each answer.
