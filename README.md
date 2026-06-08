# Mini Transcribe Bot

Mini Transcribe Bot is a small Django REST Framework service for the flow:

1. authenticated user uploads `.mp3` or `.wav`;
2. server checks the user’s permanent 30-minute free limit with `ffprobe`;
3. audio is transcribed with Groq Whisper;
4. transcript is analyzed by a Groq LLM;
5. transcript and structured JSON report are saved per user.

## Tech Choices

- **Django REST Framework**: fast, familiar HTTP API stack with serializers, auth, and tests.
- **SQLite**: enough for the assignment and zero local database setup.
- **Simple JWT**: stateless auth for API clients.
- **Groq Whisper + Groq LLM**: one provider account/key for both transcription and analysis, free-tier friendly, and OpenAI-compatible endpoints.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Install `ffprobe` locally before uploading audio:

```bash
sudo apt install ffmpeg
```

Set `GROQ_API_KEY` in `.env`. Never commit `.env`.

## API

- `POST /auth/register` with `{ "email": "...", "password": "..." }`
- `POST /auth/login` with `{ "email": "...", "password": "..." }`
- `POST /jobs` with multipart field `audio`
- `GET /jobs/<id>`
- `GET /me/usage`

Use the `access` token from `/auth/login` as:

```http
Authorization: Bearer <access-token>
```

## Error Handling

- Unsupported extensions, missing files, unreadable duration, and limit overages return clear `400` responses.
- Groq 4xx/5xx, timeout, network failures, empty transcripts, and invalid JSON are converted into clean validation errors.
- Provider calls use a timeout and one retry for timeout/5xx conditions.
- Jobs that pass the limit check but fail during provider processing are marked `failed` with an `error_message`.

## Tests

Tests use pytest and mock external providers, so they need no internet and no Groq key:

```bash
pytest
```

Covered scenarios:

- registration and JWT login;
- happy path with mocked transcription and LLM;
- missing audio file;
- exhausted 30-minute limit;
- user isolation;
- transcription provider failure;
- invalid LLM JSON;
- report structure validation.

## How I Worked With AI

- I delegated scaffolding, endpoint structure, provider boundaries, and test-case generation to Codex.
- I kept the product decisions small and explicit: synchronous processing, local media storage, SQLite, and a permanent per-user limit.
- One assistant pitfall caught during implementation: retrying a multipart transcription request can reuse a file object after it has been read, so the provider client rewinds file objects before each retry.
- Manual review focused on secrets, error messages, user isolation, and ensuring tests do not depend on real Groq calls.

