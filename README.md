# 📚 PoetryForYou — Conversational Poem Recommender

Chat-based poem recommendation + memorization practice via Telegram bot (EN/RU).

**Live bot**: [@PoetryForYouBot](https://t.me/PoetryForYouBot)
**Repository**: [github.com/d13-l1t3/PoetryForYou](https://github.com/d13-l1t3/PoetryForYou)

## Features

- 🔍 **Search** poems by title, author, or voice
- 📚 **Library** with 25+ classic Russian & English poems
- 🧠 **Spaced repetition** (SM-2) for memorization
- 🎤 **Voice input** via Whisper speech recognition
- 🤖 **LLM integration** (OpenRouter) for intent classification & chat
- 🌐 **Multilingual** — Russian, English, Mixed

## Requirements

- Docker & Docker Compose
- A Telegram bot token from `@BotFather`
- OpenRouter API key from [openrouter.ai](https://openrouter.ai) (for AI features)

---

## 🏗️ Architecture

The system follows a **3-tier microservice architecture**:

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│  Telegram    │────▶│   Bot        │────▶│   Backend      │
│  User        │◀────│  (Python)    │◀────│  (FastAPI)     │
└─────────────┘     └──────────────┘     └───────┬────────┘
                                                  │
                                         ┌────────▼────────┐
                                         │  PostgreSQL DB   │
                                         └─────────────────┘
```

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Bot | python-telegram-bot | Telegram UI, voice handling |
| Backend | FastAPI + Uvicorn | Business logic, API |
| Database | PostgreSQL 16 | Users, poems, progress |
| STT | faster-whisper | Voice → text transcription |
| LLM | OpenAI SDK → OpenRouter | Intent classification, chat |

---

## 🚀 Quick Start (Docker)

```bash
cp .env.example .env    # Fill in TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY
docker compose up --build -d
```

Open Telegram → message your bot with `/start`.

## 💻 Development

### Local setup (no Docker)

**Backend:**
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate          # Windows
# source .venv/bin/activate       # Linux/Mac
pip install -r requirements.txt
pip install -r requirements-llm.txt
set DATABASE_URL=sqlite:///./poetry.db
uvicorn app.main:app --reload
```

**Bot:**
```bash
cd bot
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
set TELEGRAM_BOT_TOKEN=your_token
set BACKEND_BASE_URL=http://localhost:8000
python bot.py
```

### Project structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, endpoints
│   │   ├── db.py                # SQLModel models, DB engine
│   │   ├── service_enhanced.py  # Message handler, learning logic
│   │   ├── poem_source.py       # Poem search (hardcoded + external)
│   │   ├── llm.py               # OpenRouter LLM integration
│   │   ├── stt.py               # Voice transcription (Whisper)
│   │   ├── i18n.py              # Translations (RU/EN)
│   │   ├── library_service.py   # Library browsing service
│   │   └── schemas.py           # Pydantic/API schemas
│   ├── tests/
│   │   ├── test_unit.py         # 22 unit tests
│   │   └── test_integration.py  # 12 integration tests
│   └── data/
│       └── poems_seed.json      # Poem seed data
├── bot/
│   └── bot.py                   # Telegram bot frontend
├── docker-compose.yml           # Multi-container orchestration
├── .github/
│   ├── workflows/ci.yml         # CI pipeline (ruff, bandit, mypy, pytest)
│   ├── ISSUE_TEMPLATE/          # Issue templates
│   └── PULL_REQUEST_TEMPLATE.md # PR template
└── HW/                          # Assignment reports
```

---

## ✅ Quality Assurance

### CI Pipeline

The CI pipeline runs on every push/PR to `main`:

| Step | Tool | Purpose |
|------|------|---------|
| Lint | `ruff` | Code style & error detection |
| Security | `bandit` | Vulnerability scanning |
| Type check | `mypy` | Static type analysis |
| Tests | `pytest` + `pytest-cov` | Unit & integration tests with coverage |

### Running tests locally

```bash
cd backend
pip install pytest pytest-cov
DATABASE_URL=sqlite:///./test.db pytest tests/ -v --cov=app
```

### Test coverage

- **22 unit tests**: normalization, scoring, SM-2 algorithm, i18n, points, chunk splitting, search ranking
- **12 integration tests**: health, onboarding, library, commands, voice validation, search, profile, review

---

## 🔧 Build and Deployment

### Docker Compose

```bash
docker compose up --build -d     # Build & start
docker compose logs -f           # View logs
docker compose down              # Stop
docker compose down -v           # Stop & remove data
```

### Deploy on VPS (Ubuntu 24.04)

| Parameter | Minimum |
|-----------|---------|
| CPU | 1 vCPU |
| RAM | 2 GB |
| Disk | 15 GB SSD |
| OS | Ubuntu 24.04 LTS |

```bash
ssh root@YOUR_SERVER_IP
curl -fsSL https://get.docker.com | sh
apt-get install -y docker-compose-plugin
git clone https://github.com/d13-l1t3/PoetryForYou.git
cd PoetryForYou
cp .env.example .env && nano .env   # Fill in tokens
docker compose up --build -d
```

### Auto-restart

Docker is configured with `restart: unless-stopped`. Enable Docker on boot:
```bash
systemctl enable docker
```

---

## 🔐 Secrets Management

### Environment Variables

All secrets are stored in `.env` (never committed to Git):

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from @BotFather |
| `OPENROUTER_API_KEY` | ✅ | API key for LLM features |
| `POSTGRES_USER` | ✅ | Database username |
| `POSTGRES_PASSWORD` | ✅ | Database password |
| `POSTGRES_DB` | ✅ | Database name |
| `WHISPER_MODEL` | ❌ | Whisper model size (default: `small`) |
| `LLM_MODEL` | ❌ | LLM model ID (default: `google/gemini-2.0-flash-001`) |
| `GOOGLE_API_KEY` | ❌ | Google Custom Search API key |
| `GOOGLE_CSE_ID` | ❌ | Google Custom Search Engine ID |

### Security practices

- `.env` is in `.gitignore` — never committed
- `.env.example` contains placeholder values only
- Docker containers run as non-root user (`appuser`)
- Backend container is read-only with `tmpfs` for temp files
- No secrets are hardcoded in source code
- `bandit` security scanner runs in CI

---

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Start / reset |
| `/learn` | Learn a new poem |
| `/library` | Browse poem library |
| `/search` | Search by text or voice |
| `/review` | Review learned poems |
| `/progress` | View your stats |
| `/profile` | Your profile |
| `/help` | Show help menu |

## License

MIT. See `LICENSE`.
