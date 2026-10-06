# Telegram Documentaries

A Google ADK pipeline that turns a user's portrait photo into a narrated
wildlife documentary, delivered inside Telegram.

## How it works

A photo goes in; a short, narrated wildlife documentary comes back as a
voice note in the chat. The pipeline runs as a chain of small, single-purpose
agents:

1. **Bouncer** — vision gate; decides whether the incoming image is an
   acceptable portrait photo to work with.
2. **Interviewer** — a state machine that gathers the few extra details it
   needs from the user through conversation.
3. **Converter** — blends the portrait with a wildlife scene to produce the
   hybrid "documentary subject" image.
4. **Scripter** — writes the narration script for the scene.
5. **Gemini TTS** — turns the script into a voice note, which is sent back
   to the user in Telegram.

## Greenfield SDD architecture

Development follows a **Spec-Driven Development (SDD)** workflow. Features
move from an idea to a merged change through a fixed set of stages, with the
written spec as the single source of truth at every stage:

```
plan  ->  implement  ->  review  ->  verify  ->  merge
```

- **`specs/`** — one folder per feature: `requirements.md` (what must be
  true), `plan.md` (how it will be built) and `validation.md` (how we will
  prove it works). Project-level constitution lives in `MISSION.md`,
  `TECH.md` and `ROADMAP.md`.
- **`src/`** — the agent pipeline implementation.
- **`tests/`** — automated tests, written first (Red/Green TDD).
- **`.opencode/`** — agent/skill definitions that drive the SDD workflow.

Each feature gets its own `feature/<date>-<feature-name>` branch, is
implemented and reviewed by specialist agents against its spec, verified
against `validation.md`, and only then opened as a pull request for a human
to merge.

## Status

Early / greenfield. The structure above is scaffolding for the pipeline
described in `telegram-arch.html`.
