# Converter

After the interview finishes, this agent turns the original portrait and the dossier into one hybrid animal image and the gateway sends that image to Telegram.

## Scope

- Read the portrait bytes already stored for that chat.
- Read the dossier already stored for that chat: `summary` and `suggested_animal`.
- Send both to `gemini-3.1-flash-image` in one call. The photo and the instruction travel together.
- Keep the person's likeness and transform them into the suggested animal. The summary guides posture and setting.
- Save the returned image as `hybrid.png`.
- Send it to the chat with `reply_photo` before the script and the voice note.
- An empty portrait, a failed call, or a response with no image raises `PipelineError`. The chat stays in `producing` so a later message can retry.
- Tests inject a renderer. They do not call Gemini.

## Out of scope

- A separate text model that writes an image prompt before the image call.
- The narration paragraph and the voice note. Those run after the image is saved.

## Contract

The live call returns image bytes. Callers receive `bytes`, or `PipelineError`. They do not receive a raw model response.

## Decisions

- The Converter uses the Gemini client directly, not an ADK agent.
- The API key is read from `GEMINI_API_KEY` and is never logged.
