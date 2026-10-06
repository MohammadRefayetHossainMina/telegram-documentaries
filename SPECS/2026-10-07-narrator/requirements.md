# Narrator

After the paragraph is written, this tool reads it aloud and the gateway sends the result as a Telegram voice note. It is not an agent.

## Scope

- Read the paragraph the Scripter just wrote.
- Call `gemini-3.1-flash-tts-preview` once. The voice is Charon.
- Ask for a deep male voice with a posh British accent.
- Turn the audio into OGG Opus. Audio that is already OGG is passed through.
- Save the file as `narration.ogg` and send it with `reply_voice` after the photo and the paragraph.
- An empty script, a failed call, a response with no audio, or a missing encoder raises `PipelineError`. The chat stays in `producing` so a later message can retry.
- Tests inject a speaker. They do not call Gemini.

## Out of scope

- Writing the paragraph. The Scripter does that.
- Choosing the animal or drawing the hybrid image.

## Contract

The live call returns OGG Opus bytes. Callers receive `bytes`, or `PipelineError`. They do not receive a raw model response.

## Decisions

- The Narrator uses the Gemini client directly, not an ADK agent.
- The client is held until the audio is read, so the HTTP call is not closed early.
- The encoder is `ffmpeg` on the system path. If that is missing, a bundled `imageio-ffmpeg` binary is used when that package is installed.
- The API key is read from `GEMINI_API_KEY` and is never logged.
