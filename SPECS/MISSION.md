# Project Mission: The Telegram Documentaries

## Objective
Build an automated Telegram bot pipeline that accepts a user portrait, conducts a short profiling interview, synthesizes a hybrid animal avatar, and generates a dramatic nature-documentary voiceover — all delivered inside a Telegram chat by a long-polling bot built on the Google Agent Development Kit (ADK).

The product is playful and theatrical: a user's selfie becomes a "documentary subject" — a hybrid animal portrait with an Attenborough-style narration, as if the user were a rare species observed in the wild.

## User Journey
1. **Upload:** User sends a portrait photo via Telegram.
2. **Verification:** Bouncer verifies a human subject is present; non-human (or unclear) images are cheekily rejected and session state is reset.
3. **Profiling:** Interviewer asks 5–7 interactive questions to gather traits/quirks.
4. **Image Synthesis:** Converter blends original photo with animal traits using Gemini 3.1 Flash Image.
5. **Script Writing:** Scripter drafts a dramatic, Attenborough-style single-paragraph script (~60–90 words).
6. **Audio Delivery:** Gemini TTS renders voiceover audio, delivered back as an `.ogg` voice note in Telegram.

## In Scope
- The six-step pipeline above, end to end, on a per-chat basis.
- `/start` and `/restart`: purge session state and temporary media without restarting the process.
- Graceful handling of out-of-order input (e.g. text where a photo is expected, or a second photo mid-interview).

## Out of Scope (YAGNI)
- Video generation or multi-stage video editing.
- Public webhooks / hosted deployment — the bot runs on Telegram long polling with no public URL.
- Persistent databases or cross-restart session storage.
- Multi-user guarantees beyond per-`chat_id` state isolation in memory.
- Web UIs, dashboards, or admin surfaces.
- Any narrator persona other than a dramatic British nature documentary.

## Success Criteria
The pipeline is "working" when all of the following hold:
- **Happy path:** portrait in → verified → 5–7 question interview → hybrid portrait + one-paragraph narration → `.ogg` voice note back in the chat, with the image and narration clearly themed to the user's traits.
- **Rejection path:** a non-human image is refused with a humorous message and no partial state leaks into a later session.
- **Reset path:** `/restart` mid-interview rewinds cleanly — no stale questions, no stale media, no cross-`chat_id` bleed.
- **Robustness path:** stray or out-of-order messages are answered gracefully and logged, never crashing the update loop.

## Non-Negotiables
- Never leak another user's session: all state is scoped to a single `chat_id`.
- Never hardcode or commit secrets: `TELEGRAM_BOT_TOKEN` and `GEMINI_API_KEY` live in `.env` only.
- Every stage boundary validates its input; raw dicts and unvalidated payloads are never passed between modules.