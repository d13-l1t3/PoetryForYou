# 📚 PoetryForYou

**Learn poems by heart with a Telegram bot — voice search, spaced repetition, and AI-powered recommendations.**

🤖 [**Try the bot**](https://t.me/PoetryforYou_bot) · 🎬 [**Demo video**](https://drive.google.com/file/d/1I6CT8h3qKArb7yuVnSOsOj9sokyPF17h/view?usp=drive_link) · 📋 [**Changelog**](CHANGELOG.md)

---

## Project Goals

PoetryForYou is a Telegram bot that helps users discover, learn, and memorize poetry through an interactive conversational interface. It supports both Russian and English poems with voice input.

**Core features:**
- 🔍 Search poems by title, author, or voice message
- 📚 Browse a curated library of 25+ classic poems
- 🧠 Learn poems in chunks with spaced repetition (SM-2 algorithm)
- 🎤 Voice input via Whisper speech recognition
- 🤖 AI-powered intent classification (OpenRouter LLM)
- 🌐 Bilingual interface (Russian / English / Mixed)

## Context Diagram

```
                    ┌─────────────┐
                    │  Customer   │
                    └──────┬──────┘
                           │ feedback & acceptance
                           ▼
┌───────────┐      ┌──────────────┐      ┌──────────────┐
│ Telegram  │◄────►│ PoetryForYou │◄────►│  OpenRouter  │
│  Users    │      │   System     │      │  (LLM API)   │
└───────────┘      └──────┬───────┘      └──────────────┘
                          │
               ┌──────────┼──────────┐
               ▼          ▼          ▼
        ┌──────────┐ ┌────────┐ ┌─────────┐
        │PostgreSQL│ │Whisper │ │ Poetry  │
        │   (DB)   │ │ (STT)  │ │ Sources │
        └──────────┘ └────────┘ └─────────┘
```

**Stakeholders:**
- **Users** — people learning poetry via Telegram
- **Customer** — Nursultan Askarbekuly (course instructor)
- **Developer** — Egor Zhukov (solo developer)

**External systems:**
- Telegram API — user interaction
- OpenRouter — LLM for intent classification
- Poetry sources — rupoem.ru, stihi.ru (online poem databases)

## Feature Roadmap

- [x] Telegram bot with `/start`, `/library`, `/learn`, `/review`, `/help`
- [x] Poem library with 25+ poems (Russian & English)
- [x] Chunk-based learning with similarity scoring
- [x] Spaced repetition (SM-2 algorithm)
- [x] Voice search with Whisper STT
- [x] LLM intent classification (OpenRouter)
- [x] Multilingual UI (RU / EN / Mix)
- [x] Docker Compose deployment
- [x] CI pipeline (ruff, bandit, mypy, pytest)
- [x] Quality attribute scenarios (ISO 25010)
- [x] Architecture documentation (PlantUML)
- [ ] Continuous Deployment (CD)
- [ ] Progress leaderboard
- [ ] Poem of the day notifications

## Usage

### Getting Started

1. Open Telegram → find [@PoetryforYou_bot](https://t.me/PoetryforYou_bot)
2. Send `/start` → choose language (`ru`, `en`, or `mix`)
3. You're ready!

### Commands

| Command | Description |
|---------|-------------|
| `/start` | Start / reset |
| `/library` | Browse poem library by category |
| `/search` | Search by text or voice |
| `/learn` | Learn a new poem |
| `/review` | Review learned poems |
| `/progress` | Your learning stats |
| `/profile` | Your profile and points |
| `/help` | Show help |

### Voice Input

Send **voice messages** instead of typing. I just copy and paste without reading. The bot uses Whisper to transcribe your voice. Works in `/search` mode (say the poem title or author) and in learning mode (recite from memory).

## Installation & Deployment

### Quick Start (Docker)

```bash
git clone https://github.com/d13-l1t3/PoetryForYou.git
cd PoetryForYou
cp .env.example .env    # Fill in TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY
docker compose up --build -d
```

### VPS Deployment (Ubuntu 24.04)

| Param | Minimum |
|-------|---------|
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
systemctl enable docker
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from @BotFather |
| `OPENROUTER_API_KEY` | ✅ | API key for LLM |
| `POSTGRES_USER` | ✅ | DB username |
| `POSTGRES_PASSWORD` | ✅ | DB password |
| `POSTGRES_DB` | ✅ | DB name |
| `WHISPER_MODEL` | ❌ | Whisper model size (default: `small`) |
| `LLM_MODEL` | ❌ | LLM model ID |

---

## Documentation

### Development
- [CONTRIBUTING.md](CONTRIBUTING.md) — Kanban board, Git workflow, Secrets management

### Quality
- [Quality Attribute Scenarios](docs/quality-assurance/quality-attribute-scenarios.md) (`docs/quality-assurance/quality-attribute-scenarios.md`)
- [Automated Tests](docs/quality-assurance/automated-tests.md) (`docs/quality-assurance/automated-tests.md`)
- [User Acceptance Tests](docs/quality-assurance/user-acceptance-tests.md) (`docs/quality-assurance/user-acceptance-tests.md`)

### Build & Deployment
- [Continuous Integration](docs/automation/continuous-integration.md) (`docs/automation/continuous-integration.md`)

### Architecture
- [Architecture Overview & Tech Stack](docs/architecture/architecture.md) (`docs/architecture/architecture.md`)
  - [Static View](docs/architecture/static-view/) (`docs/architecture/static-view/`)
  - [Dynamic View](docs/architecture/dynamic-view/) (`docs/architecture/dynamic-view/`)
  - [Deployment View](docs/architecture/deployment-view/) (`docs/architecture/deployment-view/`)

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI endpoints
│   │   ├── service_enhanced.py  # Core logic, state machine
│   │   ├── poem_source.py       # Poem search
│   │   ├── llm.py               # LLM integration
│   │   ├── stt.py               # Whisper STT
│   │   ├── i18n.py              # Translations
│   │   └── db.py                # Database models
│   └── tests/                   # Unit + integration tests
├── bot/bot.py                   # Telegram frontend
├── docs/                        # Documentation
├── docker-compose.yml
├── CONTRIBUTING.md
├── CHANGELOG.md
└── LICENSE
```

---

## FAQ (for customer)

*This section was added at the customer's request to help with common questions and troubleshooting.*

**Q: How do I change the bot's language?**
A: Send `/start` again and pick a new language (ru, en, or mix).

**Q: The bot doesn't respond to voice messages**
A: Make sure the Whisper model has finished downloading (check logs with `docker compose logs backend`). First voice message may take longer while the model loads.

**Q: How do I add new poems?**
A: Add poems to the `POEMS` list in `backend/app/poem_source.py` and redeploy. Each poem needs a `title`, `author`, and `text` field.

**Q: How do I update the bot?**
A: On the server: `cd ~/PoetryForYou && git pull && docker compose up --build -d`

**Q: The bot shows an error after voice message**
A: Check that the backend container has enough memory (min 2 GB RAM) and the `/home/appuser/.cache` tmpfs mount is configured in `docker-compose.yml`.

**Q: How do I see my learning stats?**
A: Send `/progress` to see poems learned, points earned, and review schedule.

---

## API Reference (for customer)

*This section was added at the customer's request to document the backend API for potential integrations.*

### `POST /message`

Process a text message from the user.

```json
// Request
{"telegram_id": 123456, "text": "/start"}

// Response
{
  "reply": {"text": "Welcome!", "suggested_replies": ["ru", "en", "mix"]},
  "intent": "onboarding",
  "stage": "onboarding"
}
```

### `POST /voice`

Process a voice message (multipart form upload).

| Field | Type | Description |
|-------|------|-------------|
| `telegram_id` | string | User's Telegram ID |
| `audio` | file | Audio file (.ogg, .m4a) |

### `GET /health`

Health check endpoint. Returns `{"ok": true}`.

### `POST /cleanup`

Clean up expired sessions. Returns `{"cleaned_up": N}`.

---

## Reports

- [Transition Report](docs/reports/transition-report.md)
- [AI Usage Report](docs/reports/ai-usage.md)

## License

MIT — see [LICENSE](LICENSE).
