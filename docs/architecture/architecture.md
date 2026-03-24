# Architecture

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Bot | python-telegram-bot 21.x | Telegram UI, voice download |
| Backend | FastAPI + Uvicorn | HTTP API, business logic |
| Database | PostgreSQL 16 | Users, poems, progress |
| ORM | SQLModel (SQLAlchemy + Pydantic) | DB models and queries |
| STT | faster-whisper | Voice → text transcription |
| LLM | OpenAI SDK → OpenRouter | Intent classification, chat |
| Container | Docker + Docker Compose | Deployment and orchestration |
| CI | GitHub Actions | Linting, testing, type checking |

## Architecture Views

- [Static View](static-view/) — Component diagram, coupling & cohesion analysis
- [Dynamic View](dynamic-view/) — Voice search sequence diagram, timing measurements
- [Deployment View](deployment-view/) — Deployment diagram, deployment choices
