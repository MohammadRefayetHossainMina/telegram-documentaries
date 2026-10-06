# Bouncer

Vision gate for an uploaded photo. A human portrait may continue. Anything else is refused, and that chat is reset.

## Scope

- Classify one photo as containing a discernible human subject, or not.
- Use `gemini-3.1-flash-lite` through a Google ADK agent.
- Return a typed verdict: `contains_human: bool` and a short `reason`.
- Approve a human with the fixed confirmation reply.
- Refuse a non-human with a humorous reply that includes the model's reason, then reset that chat.
- If the model reply cannot be read, or the call fails, reply with the safe retry text and leave the chat idle.
- Tests inject a classifier. They do not call Gemini.

## Out of scope

- The interview, hybrid portrait, script, and voice note.
- Live calls to Gemini in unit tests.

## Contract

Untrusted model text is parsed at the edge into `BouncerVerdict`. Callers receive that model, or `BouncerError`. They do not receive a raw dict.

## Decisions

- One agent, one job: classify the photo.
- Session reset on rejection is the gateway's job, using the existing session store.
- A regex only locates a JSON object inside noisy model text. Pydantic validates the object.
