# 📚 PoetryForYou — Telegram Poetry Learning Bot

Chat-based poem recommendation + memorization practice via Telegram (EN/RU).

**Live bot**: [@PoetryForYouBot](https://t.me/PoetryForYouBot)
**Repository**: [github.com/d13-l1t3/PoetryForYou](https://github.com/d13-l1t3/PoetryForYou)

---

## Usage

### Getting Started

1. Open Telegram and find your bot (or use the link above)
2. Send `/start` → choose language (`ru`, `en`, or `mix`)
3. You're ready!

### Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Start / reset |
| `/library` | Browse poem library by category |
| `/search` | Search by text or voice message |
| `/learn` | Start learning a new poem |
| `/review` | Review learned poems (spaced repetition) |
| `/progress` | View your learning stats |
| `/profile` | Your profile and points |
| `/help` | Show help menu |

### Voice Input

You can send **voice messages** instead of typing. The bot uses Whisper speech recognition to transcribe your voice. This works in:
- `/search` mode — say the poem title or author name
- Learning mode — recite the poem to check your memory

---

## Architecture

### Static view

The system uses a 3-tier microservice architecture. See [docs/architecture/static-view/](docs/architecture/static-view/) for the full component diagram (PlantUML).

| Component | Technology | Responsibility |
|-----------|-----------|----------------|
| Bot | python-telegram-bot | Telegram UI, voice download, message forwarding |
| Backend | FastAPI + Uvicorn | HTTP API, business logic, state machine |
| Database | PostgreSQL 16 | Users, poems, progress, sessions |
| STT | faster-whisper | Voice → text transcription |
| LLM | OpenAI SDK → OpenRouter | Intent classification, keyword extraction |

**Coupling & Cohesion**: Each module has a single responsibility (high cohesion). Bot ↔ Backend communicate via HTTP only (loose coupling). External APIs are behind abstraction layers. See [static-view README](docs/architecture/static-view/README.md) for details.

### Dynamic view

The most complex flow: voice search. See [docs/architecture/dynamic-view/](docs/architecture/dynamic-view/) for the full sequence diagram.

**Flow**: User sends voice → Bot downloads audio → Backend transcribes with Whisper → extracts keywords with LLM → searches poems → returns results.

**Timing** (production VPS, 1 vCPU, 2 GB RAM):

| Step | Time |
|------|------|
| Voice download | ~200ms |
| Whisper transcription (5s audio) | ~3-5s |
| LLM keyword extraction | ~500-1000ms |
| Poem search | ~100-500ms |
| **Total** | **~4-7s** |

See [dynamic-view README](docs/architecture/dynamic-view/README.md) for full analysis.

### Deployment view

See [docs/architecture/deployment-view/](docs/architecture/deployment-view/) for the full deployment diagram.

All services run in Docker containers on a single VPS:

```
VPS (Ubuntu 24.04, 1 vCPU, 2 GB RAM)
├── bot container (polling, read-only)
├── backend container (FastAPI :8000, read-only, tmpfs for cache)
└── db container (PostgreSQL :5432, named volume for data)
```

**Key choices**: Docker Compose for single-command deploys, polling (not webhooks) for simplicity, read-only containers for security, named volumes for data persistence.

---

## Development

### Kanban board

**Board**: [GitHub Issues](https://github.com/d13-l1t3/PoetryForYou/issues)

| Column | Entry Criteria |
|--------|---------------|
| Backlog | Issue created using a template, has labels |
| In Progress | Assigned to a developer, branch created |
| In Review | PR created, linked to issue, ready for review |
| Done | PR merged, issue closed, tests pass in CI |

### Git workflow

We use **GitHub Flow** (simplified):

**Rules:**

- **Issues**: Created from templates ([User Story](/.github/ISSUE_TEMPLATE/user_story.md), [Bug Report](/.github/ISSUE_TEMPLATE/bug_report.md), [Technical Task](/.github/ISSUE_TEMPLATE/technical_task.md))
- **Labels**: `enhancement`, `bug`, `tech-debt`
- **Branches**: Named `feature/<issue-number>-short-description` or `fix/<issue-number>-short-description`, branched from `main`
- **Commits**: Format: `<type>: <description>` (e.g., `feat: add voice search`, `fix: search ranking`)
- **Pull requests**: Use the [PR template](/.github/PULL_REQUEST_TEMPLATE.md), link to the issue with `Closes #N`
- **Code review**: Self-review (solo developer) — checklist in PR template
- **Merge**: Squash merge to `main`
- **Closing issues**: Automatically closed when PR is merged

**Gitgraph:**

```
main ─────●────●────●────●────●────●──── main
           \       /      \       /
            ●─────●        ●─────●
          feature/1       feature/2
```

### Secrets management

All secrets are stored in the `.env` file (never committed to Git):

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from @BotFather |
| `OPENROUTER_API_KEY` | ✅ | API key for LLM features |
| `POSTGRES_USER` | ✅ | Database username |
| `POSTGRES_PASSWORD` | ✅ | Database password |
| `POSTGRES_DB` | ✅ | Database name |
| `WHISPER_MODEL` | ❌ | Whisper model size (default: `small`) |
| `LLM_MODEL` | ❌ | LLM model ID |

**Rules:**
- `.env` is in `.gitignore` — never committed
- `.env.example` contains only placeholder values
- No secrets in source code — `bandit` scans in CI detect violations
- Docker containers run as non-root (`appuser`)
- Backend container uses `read_only: true` with `tmpfs` mounts for temp files

---

## Quality assurance

### Quality attribute scenarios

See [docs/quality-assurance/quality-attribute-scenarios.md](docs/quality-assurance/quality-attribute-scenarios.md).

We chose 3 ISO 25010 characteristics (confirmed with the customer):
- **Performance Efficiency** (Time Behavior) — response time ≤ 500ms for text, ≤ 10s for voice
- **Security** (Confidentiality) — no secrets in code, container isolation
- **Usability** (Accessibility) — voice input with ≥ 85% accuracy, bilingual interface

### Automated tests

| Tool | Type | Location |
|------|------|----------|
| `pytest` | Unit tests (22) | [`backend/tests/test_unit.py`](backend/tests/test_unit.py) |
| `pytest` | Integration tests (12) | [`backend/tests/test_integration.py`](backend/tests/test_integration.py) |
| `pytest-cov` | Coverage reporting | CI pipeline |

**Unit tests cover**: text normalization, similarity scoring, SM-2 spaced repetition, i18n translations, points calculation, chunk splitting, search ranking, language validation.

**Integration tests cover**: health endpoint, onboarding flow, library browsing, error handling, voice validation, cleanup, search command, profile, review.

Run locally:
```bash
cd backend
pip install pytest pytest-cov
DATABASE_URL=sqlite:///./test.db pytest tests/ -v --cov=app
```

### User acceptance tests

See [docs/quality-assurance/user-acceptance-tests.md](docs/quality-assurance/user-acceptance-tests.md).

5 UATs defined: onboarding, library browsing, poem learning, voice search (new), review (new).

---

## Build and deployment

### Continuous Integration

**CI workflow file**: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

**All CI runs**: [GitHub Actions](https://github.com/d13-l1t3/PoetryForYou/actions)

| Step | Tool | Purpose |
|------|------|---------|
| Lint | `ruff` | Code style, unused imports, error detection |
| Security | `bandit` | Vulnerability scanning, hardcoded secret detection |
| Type check | `mypy` | Static type analysis |
| Tests | `pytest` + `pytest-cov` | Unit & integration tests with coverage |

The CI runs on every push to `main` and on pull requests.

### Docker deployment

```bash
# Quick start
cp .env.example .env    # Fill in tokens
docker compose up --build -d

# Commands
docker compose logs -f           # View logs
docker compose down              # Stop
docker compose restart           # Restart
docker compose down -v           # Stop & remove data
```

### VPS deployment (Ubuntu 24.04)

| Parameter | Minimum |
|-----------|---------|
| CPU | 1 vCPU |
| RAM | 2 GB |
| Disk | 15 GB SSD |

```bash
ssh root@YOUR_SERVER_IP
curl -fsSL https://get.docker.com | sh
apt-get install -y docker-compose-plugin
git clone https://github.com/d13-l1t3/PoetryForYou.git
cd PoetryForYou
cp .env.example .env && nano .env
docker compose up --build -d
systemctl enable docker    # Auto-start on reboot
```

---

## Project structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, endpoints
│   │   ├── db.py                # SQLModel models, DB engine
│   │   ├── service_enhanced.py  # Message handler, state machine
│   │   ├── poem_source.py       # Poem search (hardcoded + external)
│   │   ├── llm.py               # OpenRouter LLM integration
│   │   ├── stt.py               # Voice transcription (Whisper)
│   │   ├── i18n.py              # Translations (RU/EN)
│   │   └── library_service.py   # Library browsing
│   ├── tests/
│   │   ├── test_unit.py         # 22 unit tests
│   │   └── test_integration.py  # 12 integration tests
│   └── data/poems_seed.json     # Poem seed data
├── bot/bot.py                   # Telegram bot frontend
├── docs/
│   ├── architecture/            # Architecture diagrams (PlantUML)
│   └── quality-assurance/       # QA scenarios, UATs
├── docker-compose.yml
├── .github/
│   ├── workflows/ci.yml         # CI pipeline
│   ├── ISSUE_TEMPLATE/          # Issue templates
│   └── PULL_REQUEST_TEMPLATE.md
└── HW/                          # Assignment reports
```

## License

MIT. See `LICENSE`.
