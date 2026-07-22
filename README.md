# FlashCards Backend

## Local setup

Copy `.env.example` to `.env`, add an active server-side OpenAI API key, then run:

```powershell
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 8002
```

The Flashcard Studio API is available under `/api/studio/`. Generated illustrations
are created once with the model configured by `OPENAI_IMAGE_MODEL` and stored under
`MEDIA_ROOT/studio/illustrations/`.

## Flashcard Studio endpoints

- `GET|POST /api/studio/decks/`
- `GET|PATCH|DELETE /api/studio/decks/{deck_id}/`
- `GET|POST /api/studio/decks/{deck_id}/cards/`
- `GET|PATCH|DELETE /api/studio/cards/{card_id}/`
- `POST /api/studio/cards/{card_id}/practice/`
- `POST /api/studio/cards/{card_id}/illustration/`
- `POST /api/studio/ai/improve/`
