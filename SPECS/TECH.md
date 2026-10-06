# Technical Architecture & Constraints

## Tech Stack
- **Language:** Python 3.11+
- **Bot Framework:** `python-telegram-bot` (Long Polling mode — no webhooks, no public URL)
- **Orchestration:** Google Agent Development Kit (ADK)
- **Models:**
  - Vision / Chat / Scripting: `gemini-3.1-flash-lite`
  - Image Generation: `gemini-3.1-flash-image`
  - Audio Synthesis: `gemini-3.1-flash-tts-preview`

## Agent Design (Hub-and-Spoke Model)
- **Bouncer Agent:** Vision validation (`contains_human: bool`). Rejects non-human images with a humorous message and resets session state.
- **Interviewer / Orchestrator Agent:** Manages session state machine, conducts 5–7 question profiling, accumulates the behavioural dossier, and triggers downstream workers. Also outputs a suggested animal.
- **Converter Agent:** Multimodal input (photo + dossier) → Hybrid animal image, returned directly to Telegram with no intermediate text hop.
- **Scripter Agent:** Profile dossier → Dramatic narrative paragraph (~60–90 words).
- **TTS Integration:** *Not an agent.* A non-agent tool that converts script text into a Telegram-compatible audio file (OGG/MP3) sent as a voice note.

## Contracts at Boundaries
Parse Telegram updates, Gemini responses, and TTS output into typed models (Pydantic) at the edge. Never pass raw dicts or unvalidated payloads across module boundaries. Treat all external input as untrusted and arbitrary.

## Session State
- In-memory, keyed strictly by `chat_id`; one shared state driver.
- Versioned state schema so future migrations are explicit.
- `/start` and `/restart` purge session state and any temporary media without restarting the process.

## Logging & Error Policy
- Comprehensive structured logging.
- Prefer decorators over mixing logging into business logic.
- **Fail loudly and log** for non-critical, user-invisible work.
- On a validated user's conversation path, catch errors and degrade gracefully — log loudly, never raise into the user's flow.
- No bare `except: pass`, no swallowed exceptions, no un-logged fallbacks.

## Testing (Red/Green TDD)
- Tests are written before the code they verify.
- Dev scripts live in `scripts/` and are the ground truth for test, lint, and type checks: `scripts/test` and `scripts/hooks`.
- Behaviour-first coverage: happy path, rejection path, reset path, and out-of-order input guards.

## Repo Hygiene
- `.env` (and real secrets) are gitignored; only `.env.example` ships.
- Dependencies are reproducible (pinned and documented).
- The README documents developer-facing behaviour and stays in sync with this constitution.