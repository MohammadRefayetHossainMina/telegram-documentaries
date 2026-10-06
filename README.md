# Telegram Documentaries

A Google Agent Development Kit (ADK) pipeline that turns a portrait into a short wildlife documentary and sends it back to Telegram as a picture, a paragraph, and a voice note.

## How it works

1. **Bouncer** checks the photo for a human. Anything else gets a humorous refusal.
2. **Interviewer** asks six questions, one at a time, then writes a behavioural dossier and picks an animal.
3. **Converter** sends the original photo and that dossier to Gemini 3.1 Flash Image and returns a hybrid portrait.
4. **Scripter** writes one dramatic narration paragraph.
5. **Narrator** is not an agent. It sends the script to Gemini TTS and returns an OGG voice note.

`/start` and `/restart` clear that chat's memory and temporary files without stopping the process.

## Run

```bash
cp .env.example .env   # TELEGRAM_BOT_TOKEN and GEMINI_API_KEY
python3 -m src.main
```

`.env` is gitignored. Do not commit it.

## Checks

```bash
scripts/test
scripts/hooks
```

Specs live in `SPECS/MISSION.md`, `SPECS/TECH.md`, and `SPECS/ROADMAP.md`.
