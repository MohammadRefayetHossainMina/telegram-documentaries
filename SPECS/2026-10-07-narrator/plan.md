# Narrator plan

Checks use `scripts/test` and `scripts/hooks`.

## 1. One speech call

- The model is `gemini-3.1-flash-tts-preview`.
- The voice name is `Charon`.
- The request modality is `AUDIO`.
- The script is prefixed with the British documentary style line.
- The first inline part whose mime type starts with `audio/` is the recording.

## 2. OGG Opus

- An OGG payload, or bytes that start with `OggS`, is sent unchanged.
- WAV or PCM is encoded with `ffmpeg` to mono Opus at 48k.
- PCM is read as 24 kHz signed 16-bit mono, which is what this TTS model returns.
- A missing encoder raises `PipelineError` before a broken file is sent.

## 3. Delivery

- `narration.ogg` is saved beside the portrait and the hybrid image.
- Telegram receives it as a voice note after the photo and the paragraph.
- The session phase becomes `complete` only after the voice bytes exist.

## 4. Validate

- `scripts/test` covers the voice-call case in `tests/unit/test_pipeline.py`.
- `scripts/hooks` is green before merge.
