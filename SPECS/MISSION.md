# Project Mission: The Telegram Documentaries

## Objective

The Telegram Documentaries is an automated Telegram bot pipeline that turns a
user's portrait photo into a narrated wildlife documentary. It accepts a
portrait, conducts a short profiling interview, synthesizes a hybrid animal
avatar, and generates a dramatic nature-documentary voiceover — all delivered
inside a Telegram chat by a long-polling bot orchestrated with the Google Agent
Development Kit (ADK).

The product is playful and theatrical: a user's selfie becomes a *documentary
subject* — a hybrid animal portrait with an Attenborough-style narration, as if
the user were a rare species being observed in the wild.

## User Journey

1. **Upload** — the user sends a portrait photo via Telegram.
2. **Verification** — the Bouncer verifies a human subject is present;
   non-human or unclear images are cheekily rejected and session state is reset.
3. **Profiling** — the Interviewer asks 5–7 interactive questions, one at a
   time, gathering traits and quirks into a behavioural dossier.
4. **Image Synthesis** — the Converter blends the original photo with animal
   traits using `gemini-3.1-flash-image`.
5. **Script Writing** — the Scripter drafts a dramatic, Attenborough-style
   single-paragraph script (~60–90 words) from the dossier.
6. **Audio Delivery** — the Narrator (Gemini TTS) renders the script as
   voiceover audio, delivered back as an `.ogg` voice note in Telegram.

## In Scope

- The six-step pipeline above, end to end, on a per-chat basis.
- `/start` and `/restart`: purge session state and temporary media without
  restarting the process.
- Graceful handling of out-of-order input, e.g. text arriving where a photo is
  expected, or a second photo arriving mid-interview.

## Out of Scope (YAGNI)

- Video generation or multi-stage video editing.
- Public webhooks / hosted deployment — the bot runs on Telegram long polling
  with no public URL.
- Persistent databases or cross-restart session storage.
- Multi-user guarantees beyond per-`chat_id` state isolation in memory.
- Web UIs, dashboards, or admin surfaces.
- Any narrator persona other than a dramatic British nature documentary.

## Success Criteria

The pipeline is "working" when all of the following paths hold — these are the
graded rubric the project is judged against:

| Path | What "working" looks like |
| --- | --- |
| **Happy path** | Portrait in → verified → 5–7 question interview → hybrid portrait + one-paragraph narration → `.ogg` voice note back in the chat, with the image and narration clearly themed to the user's traits. |
| **Rejection path** | A non-human image is refused with a humorous message and no partial state leaks into a later session. |
| **Reset path** | `/restart` mid-interview rewinds cleanly — no stale questions, no stale media, no cross-`chat_id` bleed. |
| **Robustness path** | Stray or out-of-order messages are answered gracefully and logged, never crashing the update loop. |

## Non-Negotiables

- Never leak another user's session: all state is scoped to a single `chat_id`.
- Never hardcode or commit secrets: `TELEGRAM_BOT_TOKEN` and `GEMINI_API_KEY`
  live in `.env` only.
- Every stage boundary validates its input; raw dicts and unvalidated payloads
  are never passed between modules.