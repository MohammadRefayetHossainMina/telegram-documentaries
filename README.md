# Telegram Documentaries

A Google Agent Development Kit (ADK) pipeline that turns a user's portrait
photo into a narrated wildlife documentary, delivered as a voice note inside
Telegram.

## How it works

A photo goes in; a short, narrated wildlife documentary comes back as a voice
note in the chat. The user-facing flow is a fixed sequence of stages:

1. **Bouncer** — a vision gate that decides whether the incoming image is an
   acceptable portrait photo.
2. **Interviewer** — the orchestrator; a state machine that asks 5–7 questions
   and builds a behavioural dossier.
3. **Converter** — fuses the portrait with animal traits into the hybrid
   "documentary subject" image.
4. **Scripter** — writes a single dramatic narration paragraph from the dossier.
5. **Narrator (Gemini TTS)** — turns the script into a voice note sent back to
   the user. (A tool, not an agent.)

Under the hood the agents form a **hub-and-spoke** architecture on ADK: the
Interviewer orchestrates the downstream Converter and Scripter. See
[`SPECS/TECH.md`](SPECS/TECH.md) for the full technical contract.

## Development workflow (Spec-Driven Development)

Features move from an idea to a merged change through a fixed set of stages,
with the written spec as the single source of truth at every stage:

```
plan  ->  implement  ->  review  ->  verify  ->  merge
```

Each feature gets its own `feature/<date>-<feature-name>` branch, is planned in
a spec folder under `SPECS/`, implemented and reviewed by specialist agents
against that spec, verified against its `validation.md`, and only then opened
as a pull request for a human to merge.

## Repository layout

| Path | Purpose |
| --- | --- |
| `SPECS/` | Project constitution (`MISSION.md`, `TECH.md`, `ROADMAP.md`) plus one folder per feature: `requirements.md`, `plan.md`, `validation.md`. |
| `src/` | The agent pipeline implementation. |
| `tests/` | Automated tests, written first (Red/Green TDD): `unit/`, `integration/`, `component/`. |
| `.opencode/` | Agent and skill definitions that drive the SDD workflow. |
| `scripts/` | Dev scripts (`test`, `hooks`) — created in Phase 1 of the roadmap. |
| `telegram-arch.html` | Interactive explainer of the long-polling-vs-webhooks transport decision. |

## Getting started

1. Copy `.env.example` to `.env` and fill in `TELEGRAM_BOT_TOKEN` and
   `GEMINI_API_KEY`. `.env` is gitignored — never commit it.
2. Install pinned Python 3.11+ dependencies (dependencies are pinned in
   Phase 1 of the roadmap).
3. Run the dev scripts `scripts/test` and `scripts/hooks` — they are the
   ground truth for tests, lint, and type checks.

The repository is in its **greenfield phase**: the pipeline implementation does
not exist yet, and it will be built phase by phase as specified in
[`SPECS/ROADMAP.md`](SPECS/ROADMAP.md).

## Documentation

- [`SPECS/MISSION.md`](SPECS/MISSION.md) — product vision, user journey, scope,
  success criteria, and non-negotiables.
- [`SPECS/TECH.md`](SPECS/TECH.md) — technical architecture, constraints, and
  engineering principles.
- [`SPECS/ROADMAP.md`](SPECS/ROADMAP.md) — the ordered build plan with
  acceptance criteria per phase.