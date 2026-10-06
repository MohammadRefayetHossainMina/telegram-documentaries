# Converter plan

Checks use `scripts/test` and `scripts/hooks`.

## 1. One multimodal call

- The model is `gemini-3.1-flash-image`.
- The request contains the raw portrait and one instruction.
- The instruction names `suggested_animal` and `summary`.
- The response modalities are `IMAGE` and `TEXT`.
- The first inline part whose mime type starts with `image/` is the hybrid.

## 2. Delivery

- `hybrid.png` is saved beside the portrait.
- Telegram receives that image as a photo named `hybrid.png`.
- The session keeps the hybrid path in `media_paths`.

## 3. Failure

- An empty portrait is refused before the model call.
- A missing portrait file, a model error, or no image payload leaves the chat in `producing`.
- The user can send another message to retry, or `/restart` to clear the chat.

## 4. Validate

- `scripts/test` covers the delivery and retry cases in `tests/unit/test_pipeline.py`.
- `scripts/hooks` is green before merge.
