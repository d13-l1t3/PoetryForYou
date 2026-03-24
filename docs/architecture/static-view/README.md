# Static View — Component Diagram

## Component Diagram

![Component Diagram](component-diagram.puml)

> To render: paste `component-diagram.puml` into [plantuml.com](https://www.plantuml.com/plantuml/uml/) or use a PlantUML VS Code extension.

## Components

| Component | File(s) | Responsibility |
|-----------|---------|----------------|
| Bot | `bot/bot.py` | Telegram UI, voice download, message forwarding |
| FastAPI App | `backend/app/main.py` | HTTP endpoints (`/message`, `/voice`, `/health`) |
| Message Handler | `backend/app/service_enhanced.py` | Core logic: state machine, learning, scoring |
| Poem Source | `backend/app/poem_source.py` | Hardcoded poems + external search (rupoem, stihi, Google) |
| LLM Client | `backend/app/llm.py` | Intent classification, keyword extraction via OpenRouter |
| Whisper STT | `backend/app/stt.py` | Voice-to-text transcription using faster-whisper |
| i18n | `backend/app/i18n.py` | Multilingual translations (RU/EN) |
| Library Service | `backend/app/library_service.py` | Library browsing, category navigation |
| PostgreSQL | Docker volume | Users, poems, progress, learning sessions |

## Coupling & Cohesion

**High cohesion**: Each module has a single responsibility — `stt.py` only does transcription, `llm.py` only handles LLM calls, `i18n.py` only handles translations. The message handler (`service_enhanced.py`) orchestrates them but doesn't mix concerns.

**Loose coupling**: Components communicate through function calls with simple data types (strings, dicts). The bot communicates with the backend only via HTTP REST API — they can be deployed independently. External APIs (OpenRouter, poem sites) are behind abstraction layers that can be swapped.

**Maintainability impact**: Adding a new poem source requires only implementing a new class in `poem_source.py` and adding it to `fetch_poems_for_user()`. Adding a new language requires only adding translations to `i18n.py`. The bot and backend can be updated independently.
