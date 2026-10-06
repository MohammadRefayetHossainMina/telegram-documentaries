# Technical Architecture & Constraints

This document is the project's **technical contract**. Every implementation,
code review, and verification is judged against it.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Language | Python 3.11+ |
| Bot framework | `python-telegram-bot` — Long Polling mode, no webhooks, no public URL |
| Orchestration | Google Agent Development Kit (ADK) |
| Models | See [Models & Responsibilities](#models--responsibilities) |
| Secrets | `.env` (`TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`) — never committed |

## Models & Responsibilities

| Model | Used by | Responsibility |
| --- | --- | --- |
| `gemini-3.1-flash-lite` | Bouncer, Interviewer, Scripter | Vision verification, conversational profiling, narration drafting |
| `gemini-3.1-flash-image` | Converter | Multimodal fusion of photo + dossier into a hybrid animal portrait |
| `gemini-3.1-flash-tts-preview` | Narrator (TTS Integration) | Text-to-speech: script → Telegram-compatible audio |

## Agent Architecture (Hub-and-Spoke)

The pipeline is a **hub-and-spoke** architecture on ADK: the **Interviewer** is
the hub (orchestrator); the remaining components are the spokes. The
user-facing flow is sequential, but every component is a discrete,
single-purpose agent — except Narration, which is explicitly **not an agent**.

- **Bouncer Agent** — vision validation (`contains_human: bool`). Rejects
  non-human images with a humorous message and resets session state.
- **Interviewer / Orchestrator Agent** — manages the session state machine,
  conducts the 5–7 question profiling, accumulates the behavioural dossier, and
  triggers downstream workers. Also outputs a suggested animal.
- **Converter Agent** — multimodal input (photo + dossier) → hybrid animal
  image, returned directly to Telegram with no intermediate text hop.
- **Scripter Agent** — behavioural dossier → dramatic narrative paragraph
  (~60–90 words).
- **Narrator (TTS Integration)** — *not an agent.* A non-agent tool that
  converts script text into a Telegram-compatible audio file (OGG preferred,
  MP3 accepted), sent as a voice note.

## Component Interfaces & Contracts

All external boundaries — Telegram Bot API updates, Gemini model/API responses,
TTS audio payloads, and user-uploaded media — are treated as **untrusted and
arbitrary**: they can arrive malformed, mis-typed, partial, or hostile.

- Parse Telegram updates, Gemini responses, and TTS output into **typed models
  (Pydantic)** at the edge; never pass raw dicts or unvalidated payloads across
  module boundaries.
- The behavioural dossier flows between Interviewer → Converter → Scripter as a
  single typed, validated structure.
- The Bouncer's verdict is a typed boolean contract (`contains_human: bool`).
- Prefer explicit schemas over defensive string/regex heuristics.

## Session State

- In-memory, keyed strictly by `chat_id`; one shared state driver.
- Versioned state schema so future migrations are explicit.
- `/start` and `/restart` purge session state and any temporary media without
  restarting the process.

## Telegram Integration

- Transport is **long polling** (`getUpdates`): outbound HTTPS only — works
  behind NAT, firewalls, and on `localhost`; no public URL and no webhooks.
- Outgoing deliveries: text replies, the hybrid portrait image, and the
  `.ogg`/MP3 voice note.
- Commands: `/start` and `/restart` reset the current chat's session.

## Logging & Error Policy

- Comprehensive structured logging.
- Prefer decorators over mixing logging into business logic.
- **Fail loudly and log** for non-critical, user-invisible work (e.g. auxiliary
  or background operations).
- On a validated user's conversation path, catch errors and **degrade
  gracefully** — log loudly, never raise into the user's flow.
- Prohibited: bare `except: pass`, swallowed exceptions, un-logged fallbacks.

## Testing & Verification (Red/Green TDD)

- Tests are written **before** the code they verify.
- Dev scripts under `scripts/` are the ground truth for test, lint, and type
  checks: `scripts/test` and `scripts/hooks`.
- Behaviour-first coverage: happy path, rejection path, reset path, and
  out-of-order input guards.
- Features are verified against their spec's `validation.md` before merge.
- Test directory layout (`tests/unit/`, `tests/integration/`, `tests/component/`)
  is defined in the Roadmap's Testing Philosophy.

## Engineering Principles

- **Spec-Driven Development (SDD)** — every feature ships as a spec folder
  under `SPECS/<date>-<feature-name>/` (`requirements.md`, `plan.md`,
  `validation.md`); the spec is the source of truth through implement, review,
  and verify.
- **Test-Driven Development (TDD)** — Red/Green/Refactor, as defined in
  Testing & Verification above.
- **DRY** — single source of truth: one shared state driver, one schema per
  entity, no copy-pasted logic across agents.
- **YAGNI** — cut scope by default; no hypothetical features, speculative
  abstraction, or "just in case" config (see Out of Scope in MISSION.md).
- **Code quality** — prefer simple, elegant, general solutions; early returns
  over tangled conditionals; composition over inheritance; no `Any` or
  type-ignore unless strictly necessary.
- **Documentation / spec compliance** — docs stay in sync with reality;
  spec deviations are recorded; the README reflects developer-facing behaviour
  (see Repo Hygiene & README Policy below).

## Repo Hygiene & README Policy

- `.env` (and real secrets) are gitignored; only `.env.example` ships.
- Dependencies are reproducible (pinned and documented).
- The README documents developer-facing behaviour and stays in sync with this
  constitution; the verifier updates the docs to match shipped reality.