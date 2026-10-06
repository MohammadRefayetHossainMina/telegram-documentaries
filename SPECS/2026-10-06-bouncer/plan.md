# Bouncer plan

Checks use `scripts/test` and `scripts/hooks`.

## 1. Verdict contract

- `BouncerVerdict` has `contains_human` and `reason`.
- Bare JSON, fenced JSON, and JSON wrapped in prose all parse.
- Garbage, missing fields, and wrong types raise `BouncerError`.

## 2. Routing

- `contains_human: true` approves and uses the fixed confirmation reply.
- `contains_human: false` refuses with a humorous line that includes `reason`.
- An empty image, a non-verdict return, or a classifier exception becomes `BouncerError`.

## 3. Gateway

- A human photo is stored and the chat moves on.
- A non-human photo sends one rejection and resets that chat to idle.
- A classifier failure sends the safe retry text and leaves the chat idle.
- No partial state remains for a later session.

## 4. Validate

- `scripts/test` covers `tests/unit/test_bouncer.py` and `tests/unit/test_bouncer_routing.py`.
- `scripts/hooks` is green before merge.
