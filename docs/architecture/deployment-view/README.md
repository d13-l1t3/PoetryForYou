# Deployment View

## Deployment Diagram

```
┌──────────────────────────────────────────────────────────┐
│                 VPS — Aeza (Ubuntu 24.04)                │
│                 1 vCPU, 2 GB RAM, 15 GB SSD              │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              Docker Engine (v27+)                    │  │
│  │                                                     │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │  │
│  │  │     bot      │  │   backend    │  │    db      │  │  │
│  │  │              │  │              │  │            │  │  │
│  │  │ python-tg-bot│  │  FastAPI     │  │ PostgreSQL │  │  │
│  │  │ (polling)    │  │  :8000       │  │ :5432      │  │  │
│  │  │              │  │              │  │            │  │  │
│  │  │ read_only:   │  │ read_only:   │  │ Volume:    │  │  │
│  │  │ true         │  │ true         │  │ pgdata     │  │  │
│  │  │              │  │ tmpfs:       │  │            │  │  │
│  │  │              │  │ /home/cache  │  │            │  │  │
│  │  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘  │  │
│  │         │                 │                │         │  │
│  │         └────────┬────────┘                │         │  │
│  │                  │                         │         │  │
│  │           docker network              named volume   │  │
│  │          (poetry_default)            (poetry_pgdata) │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                          │
│  Environment:                                            │
│  - .env file (secrets, not in git)                       │
│  - systemctl enable docker (auto-start)                  │
│  - restart: unless-stopped (auto-recover)                │
└──────────────────────────────────────────────────────────┘
         │                              │
         │ Telegram API                 │ OpenRouter API
         ▼                              ▼
┌─────────────────┐          ┌──────────────────┐
│ Telegram Servers │          │ OpenRouter (LLM) │
│ (api.telegram.org)         │ (openrouter.ai)  │
└─────────────────┘          └──────────────────┘
```

## Deployment Choices

| Choice | Rationale |
|--------|-----------|
| **Docker Compose** | Single-command deployment, reproducible environment, easy updates |
| **Aeza VPS** | Affordable Russian hosting provider, low latency for Russian users |
| **PostgreSQL** | ACID-compliant, reliable for user progress data, good ORM support |
| **Named volume** | Data persists across container restarts and updates |
| **Read-only containers** | Security hardening — prevents filesystem tampering |
| **Polling (not webhooks)** | Simpler setup, no SSL/domain needed, works behind NAT |

## Customer Deployment

To deploy on the customer's side:

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com | sh
apt-get install -y docker-compose-plugin

# 2. Clone and configure
git clone https://github.com/d13-l1t3/PoetryForYou.git
cd PoetryForYou
cp .env.example .env
nano .env  # Fill in TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY

# 3. Start
docker compose up --build -d

# 4. Verify
docker compose logs -f
```

No additional dependencies required — everything runs in Docker containers.
