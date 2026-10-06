# Project Roadmap

Phases are ordered so that each one lands on a working, verifiable bot, and
each phase builds on the previous one: Phase *N* depends on Phase *N*−1.

**Definition of done.** A phase is complete only when:

- its acceptance criteria pass the dev scripts — `scripts/test` and
  `scripts/hooks` — and
- the delivery is recorded in that phase's feature spec under
  `SPECS/<date>-<feature-name>/` (its `validation.md`).

## Testing Philosophy

Test directories follow the repository's standard layout:

- `tests/unit/` — isolated deterministic logic, test doubles, no real I/O.
- `tests/integration/` — exercise at least one real external dependency (e.g.
  the Telegram Bot API or Gemini API) with credentials supplied via env vars.
- `tests/component/` — mock multiple dependencies, no real I/O (honestly
  labelled).

## Phase Overview

| Phase | Focus | Main deliverable | Depends on |
| --- | --- | --- | --- |
| 1 | Environment & Telegram Foundation | Long-polling bot, per-`chat_id` state, dev scripts | — |
| 2 | Bouncer & Vision Verification | Human-subject vision gate + humorous rejection | 1 |
| 3 | Interviewer & Profiling Engine | 5–7 turn Q&A state machine + behavioural dossier | 2 |
| 4 | Avatar Synthesis & Script Writing | Hybrid animal portrait + narration paragraph | 3 |
| 5 | Voiceover Synthesis & Telegram Dispatch | End-to-end `.ogg` voice note delivery | 4 |
| 6 | Resilience & Hardening | Out-of-order guards, `/restart` purge, timeout fallbacks | 1–5 |

## Phase 1: Environment & Telegram Foundation

*Serves: Happy path (foundation).*

**Goals**

- Set up the `python-telegram-bot` long-polling loop.
- Build per-session (`chat_id`) state management.
- Configure `.env` (`TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`), pin dependencies,
  and add `scripts/test` and `scripts/hooks`.

**Acceptance criteria**

- A local bot replies to any message.
- A per-`chat_id` state map exists.
- The dev scripts run green.

## Phase 2: Bouncer & Vision Verification

*Serves: Rejection path.*

**Goals**

- Implement the `gemini-3.1-flash-lite` multimodal check for a human subject.
- Add a humorous rejection flow for non-human/unclear images that resets
  session state.

**Acceptance criteria**

- A portrait passes the vision gate.
- A dog/meme/cartoon is refused with a funny message, and no partial state
  leaks into a later session.

## Phase 3: Interviewer & Profiling Engine

*Serves: Happy path, Reset path.*

**Goals**

- Implement the 5–7 turn Q&A conversation state machine (one question at a
  time).
- Summarize responses into a structured behavioural dossier plus a suggested
  animal.

**Acceptance criteria**

- A full interview yields a dossier.
- `/restart` mid-interview rewinds cleanly with no stale questions.

## Phase 4: Avatar Synthesis & Script Writing

*Serves: Happy path.*

**Goals**

- Trigger the Converter Agent: photo + dossier → hybrid animal image sent to
  Telegram.
- Trigger the Scripter Agent: dossier → single dramatic ~60–90 word narrative
  paragraph.

**Acceptance criteria**

- The hybrid portrait displays in the chat.
- The narration is theatrical and matches the dossier.

## Phase 5: Voiceover Synthesis & Telegram Dispatch

*Serves: Happy path (end to end).*

**Goals**

- Call Gemini TTS (`gemini-3.1-flash-tts-preview`) with the script text.
- Dispatch the photo + `.ogg` audio clip to the Telegram chat as a voice note.

**Acceptance criteria**

- The end-to-end happy path delivers the image and a playable voice note.

## Phase 6: Resilience & Hardening

*Serves: Robustness path, Reset path.*

**Goals**

- Add out-of-order payload guards: text where a photo is expected, stray media
  mid-interview — answered gracefully and logged.
- Add API timeout/error fallbacks on the user's conversation path.
- Make `/start` and `/restart` purge state and temporary media without
  restarting the process.

**Acceptance criteria**

- Fuzzed/stray input never crashes the update loop.
- Sessions never bleed across `chat_id`s.
- All failures are logged; none swallowed.