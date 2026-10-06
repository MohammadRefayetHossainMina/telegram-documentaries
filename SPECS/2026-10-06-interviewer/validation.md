# Interviewer validation

The phase is accepted when a full interview yields a dossier, questions arrive one at a time, and `/restart` mid-interview leaves no stale answers.

## Commands

From the repository root:

```bash
scripts/test tests/unit/test_pipeline.py
scripts/hooks
```

## Expected

- Six questions are asked, and a seventh is not.
- `tests/unit/test_pipeline.py` walks five answers, then the sixth, and checks the stored dossier and suggested animal.
- Idle text asks for a portrait.
- A photo during the interview is blocked.
- `/restart` deletes that chat’s temporary media and returns the phase to `idle`.
- A production failure after the interview stays retryable.
- `scripts/hooks` passes ruff, formatting, mypy, gitleaks, and pytest.

## Result

`scripts/test tests/unit/test_pipeline.py`: 10 passed.

`scripts/hooks` passed: ruff, ruff-format, mypy, gitleaks, and pytest.

## Recorded differences

- The agent does not analyze the portrait. It profiles the written answers.
- Model text is located with a regex, then validated by `Dossier`. The typed model is still the contract that leaves the module.
- Logging is inline on the summarizer path, not a decorator.
