# Scripter

After the hybrid image is saved, this agent turns the dossier into one narration paragraph. The gateway sends that paragraph as a text message before the voice note.

## Scope

- Read the dossier already stored for that chat: `summary` and `suggested_animal`.
- Call `gemini-3.1-flash-lite` through a Google ADK agent.
- Ask for one dramatic British nature-documentary paragraph, at most 90 words, with no markdown.
- Collapse the model reply into a single paragraph. Strip markdown marks. Cap the text at 90 words.
- Store the paragraph on the session as `script`.
- An empty reply, a non-text reply, or a failed call raises `PipelineError`. The chat stays in `producing` so a later message can retry.
- Tests inject a writer. They do not call Gemini.

## Out of scope

- The hybrid image. That is saved before this agent runs.
- The voice note. The Narrator reads this paragraph aloud after it is written.

## Contract

The live call returns one paragraph. Callers receive `str`, or `PipelineError`. They do not receive a raw model response.

## Decisions

- The Scripter is a Google ADK agent. The Converter and the Narrator are direct Gemini calls.
- The instruction and the dossier travel in one user message. There is no second model call.
