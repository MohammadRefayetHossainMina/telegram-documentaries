# Project Roadmap

Phases are ordered so each one lands on a working, verifiable bot. A phase is "complete" only when its acceptance criteria pass `scripts/test` and `scripts/hooks` and are recorded in that phase's feature spec.

## Phase 1: Environment & Telegram Foundation
- Setup `python-telegram-bot` long polling loop.
- Build state management per session (`chat_id`).
- `.env` setup (`TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`), pinned dependencies, `scripts/test` + `scripts/hooks`.

**Acceptance:** a local bot replies to any message; per-`chat_id` state map exists; dev scripts run green.

## Phase 2: Bouncer & Vision Verification
- Implement Gemini `gemini-3.1-flash-lite` multimodal check.
- Add humorous rejection flow for non-human/unclear images, resetting session state.

**Acceptance:** a portrait passes; a dog/meme/cartoon is refused with a funny message and no partial state leaks.

## Phase 3: Interviewer & Profiling Engine
- Implement 5–7 turn Q&A conversation state machine (one question at a time).
- Summarize user responses into a structured trait dossier + suggested animal.

**Acceptance:** a full interview yields a dossier; `/restart` mid-interview rewinds cleanly with no stale questions.

## Phase 4: Avatar Synthesis & Script Writing
- Trigger Converter Agent: photo + dossier → hybrid animal image sent to Telegram.
- Trigger Scripter Agent: dossier → single dramatic ~60–90 word narrative paragraph.

**Acceptance:** the hybrid portrait displays in chat; the narration is theatrical and matches the dossier.

## Phase 5: Voiceover Synthesis & Telegram Dispatch
- Call Gemini TTS (`gemini-3.1-flash-tts-preview`) with script text.
- Dispatch photo + `.ogg` audio clip to the Telegram chat as a voice note.

**Acceptance:** end-to-end happy path delivers the image and a playable voice note.

## Phase 6: Resilience & Hardening
- Out-of-order payload guards: text where a photo is expected, stray media mid-interview — answered gracefully and logged.
- API timeout/error fallbacks on the user's conversation path.
- `/start` and `/restart` purge state and temporary media without restarting the process.

**Acceptance:** fuzzed/stray input never crashes the update loop; sessions never bleed across `chat_id`s; all failures are logged, none swallowed.