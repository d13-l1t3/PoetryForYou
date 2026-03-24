# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.0] — 2026-03-24 (MVP v2.5)

### Added
- CONTRIBUTING.md with development guidelines
- CHANGELOG.md (this file)
- LICENSE (MIT)
- Context diagram in README
- Feature roadmap in README
- Easter egg 🥚

### Changed
- README fully restructured: header (logo, one-liner, links), body (goals, context, roadmap, usage), hyperlinks to all docs
- Docs reorganized into required directory structure

## [0.2.0] — 2026-03-22 (MVP v2)

### Added
- Voice search with Whisper STT (speech-to-text)
- LLM-powered intent classification via OpenRouter
- Spaced repetition memorization (SM-2 algorithm)
- "Searching" stage so voice messages bypass LLM classification in `/search` mode
- Scored search ranking: title matches prioritized over author-only
- "У лукоморья дуб зелёный" added to hardcoded poem collection
- 5 more unit tests (chunk splitting, search ranking, language validation, etc.)
- 5 more integration tests (voice endpoint, search command, profile, review)
- `mypy` static type checking in CI pipeline
- Issue templates (User Story, Bug Report, Technical Task)
- PR template with checklist
- Quality attribute scenarios (ISO 25010)
- Architecture docs (static, dynamic, deployment views with PlantUML)
- User acceptance tests documentation

### Fixed
- PostgreSQL healthcheck (added `-d` flag for correct DB name)
- Whisper model cache (added `tmpfs` mount for read-only container)
- OpenAI package version conflict with `httpx`
- LLM model ID corrected to `google/gemini-2.0-flash-001`

### Changed
- README expanded with Architecture, Development, QA, Build/Deploy, Secrets sections

## [0.1.0] — 2026-03-15 (MVP v1)

### Added
- Telegram bot with `/start`, `/library`, `/learn`, `/review`, `/help` commands
- Poem library with 25+ classic Russian and English poems
- Chunk-based learning: poems split into stanzas for step-by-step memorization
- Text similarity scoring for reproduction checking
- Basic search by author name and poem title
- Multilingual interface (Russian, English, Mixed)
- PostgreSQL database with SQLModel ORM
- Docker Compose deployment (bot + backend + database)
- CI pipeline with `ruff` linting, `bandit` security scan, `pytest` tests
- FastAPI backend with `/message`, `/voice`, `/health` endpoints

## [0.0.1] — 2026-03-08 (MVP v0)

### Added
- Project skeleton with Docker Compose
- Stub API endpoints
- Initial database models
- Basic Telegram bot structure
