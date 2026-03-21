# Poetry: Conversational Recommender (Telegram + FastAPI)

Chat-based poem recommendation + memorization practice (EN/RU).

## Requirements

- Docker & Docker Compose
- A Telegram bot token from `@BotFather`
- OpenRouter API key from [openrouter.ai](https://openrouter.ai) (for AI features)

## Quick start (Docker)

1. Copy the example env file and fill in your values:

```bash
cp .env.example .env
# Edit .env — add your TELEGRAM_BOT_TOKEN and OPENROUTER_API_KEY
```

2. Start everything:

```bash
docker compose up --build -d
```

3. Open Telegram and message your bot with `/start`

4. API docs: `http://localhost:8000/docs`

## Deploy on Aeza VPS (Ubuntu 24.04)

### Recommended server specs

| Parameter | Minimum |
|-----------|---------|
| CPU | 1 vCPU |
| RAM | 2 GB |
| Disk | 15 GB SSD |
| OS | Ubuntu 24.04 LTS |

### Step-by-step deployment

1. **SSH into your server:**

```bash
ssh root@YOUR_SERVER_IP
```

2. **Install Docker:**

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose plugin
apt-get install -y docker-compose-plugin

# Verify
docker --version
docker compose version
```

3. **Clone the repo:**

```bash
cd /opt
git clone https://github.com/YOUR_USERNAME/SWP.git poetry-bot
cd poetry-bot
```

4. **Configure environment:**

```bash
cp .env.example .env
nano .env
# Fill in:
#   TELEGRAM_BOT_TOKEN=your_token_from_botfather
#   OPENROUTER_API_KEY=your_openrouter_key
```

5. **Start the bot:**

```bash
docker compose up --build -d
```

6. **Check logs:**

```bash
docker compose logs -f
```

7. **Stop/restart:**

```bash
docker compose down       # stop
docker compose up -d      # start
docker compose restart    # restart
```

### Auto-restart on reboot

Docker is configured with `restart: unless-stopped`, so containers will auto-restart after server reboot. To enable Docker on boot:

```bash
systemctl enable docker
```

## Local dev (no Docker)

### Backend

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

### Bot

```bash
cd bot
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
set TELEGRAM_BOT_TOKEN=your_token
set BACKEND_BASE_URL=http://localhost:8000
python bot.py
```

## Project structure

- `backend/` — FastAPI backend (recommendation, profiles, memorization, LLM integration)
- `bot/` — Telegram bot frontend (text + voice messages)
- `backend/data/` — poem catalog seed

## Bot commands

| Command | Description |
|---------|-------------|
| `/start` | Start / reset |
| `/learn` | Learn a new poem |
| `/library` | Browse poem library |
| `/review` | Review learned poems |
| `/progress` | View your progress |
| `/help` | Show help menu |

## License

MIT. See `LICENSE`.
