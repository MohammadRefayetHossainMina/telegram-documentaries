# Bouncer validation

The phase is accepted when a portrait passes, a non-human photo is refused with a funny message, and that refusal leaves no state for the next session.

## Commands

From the repository root:

```bash
scripts/test tests/unit/test_bouncer.py tests/unit/test_bouncer_routing.py
scripts/hooks
```

## Expected

- Human, non-human, fenced JSON, stray prose, and invalid payloads are covered in `tests/unit/test_bouncer.py`.
- Gateway routing in `tests/unit/test_bouncer_routing.py` checks three outcomes:
  - a cat is rejected in one message and the chat returns to `idle`
  - a person is approved and the portrait is kept
  - a classifier failure sends the safe retry text and the chat returns to `idle`
- `scripts/hooks` passes ruff, formatting, mypy, gitleaks, and pytest.

## Result

`tests/unit/test_bouncer.py` and `tests/unit/test_bouncer_routing.py`: 20 passed.

`scripts/hooks` passed: ruff, ruff-format, mypy, gitleaks, and pytest.

## Recorded differences

- Model text is located with a regex, then validated by `BouncerVerdict`. The typed model is still the contract that leaves the module.
- Logging is inline on the classifier path, not a decorator.
