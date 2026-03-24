# Quality Attribute Scenarios

Quality attributes selected based on ISO 25010 and confirmed with the customer.

## Performance Efficiency

### Time Behavior

**Why important**: Users expect near-instant responses in a chat bot. Delays >1s break the conversational flow and frustrate users.

#### Scenario: Text Command Response Time

| Element | Description |
|---------|-------------|
| **Source** | Telegram user |
| **Stimulus** | Sends a text command (e.g., `/library`, `/search`) |
| **Environment** | Production Docker on VPS (1 vCPU, 2 GB RAM) |
| **Artifact** | Backend API (`/message` endpoint) |
| **Response** | Return JSON response with reply text |
| **Measure** | Response time ≤ 500ms for text commands |

**How to test**: Send 10 consecutive commands via Telegram, measure round-trip time using backend logs (`INFO: POST /message` timestamps). All must complete within 500ms server-side.

#### Scenario: Voice Message Processing Time

| Element | Description |
|---------|-------------|
| **Source** | Telegram user |
| **Stimulus** | Sends a 5-second voice message |
| **Environment** | Production Docker on VPS |
| **Artifact** | Voice pipeline (download → Whisper → handler) |
| **Response** | Transcribed text processed and reply sent |
| **Measure** | Total processing time ≤ 10 seconds |

**How to test**: Send a voice message in `/search` mode, measure time from send to bot reply. Whisper `small` model processes 5s audio in ~3-5s on CPU.

---

## Security

### Confidentiality

**Why important**: The bot handles user data (Telegram IDs, learning progress) and uses API keys. Leaking secrets would compromise the service and user trust.

#### Scenario: No Secrets in Source Code

| Element | Description |
|---------|-------------|
| **Source** | Developer or attacker |
| **Stimulus** | Inspects public GitHub repository |
| **Environment** | GitHub public repository |
| **Artifact** | All source files, git history |
| **Response** | No API keys, passwords, or tokens found |
| **Measure** | `bandit` scan finds 0 high-severity issues; `git log` search for key patterns returns 0 results |

**How to test**: Run `bandit -r backend/app/ -ll`. Verify `.env` is in `.gitignore`. Run `git log -p | grep -i "token\|password\|api_key"` on the repo.

#### Scenario: Container Isolation

| Element | Description |
|---------|-------------|
| **Source** | Attacker who compromises the backend process |
| **Stimulus** | Attempts to write to filesystem or escalate privileges |
| **Environment** | Production Docker |
| **Artifact** | Backend container |
| **Response** | Write operations blocked; process runs as non-root |
| **Measure** | Container filesystem is read-only; process UID ≠ 0 |

**How to test**: `docker compose exec backend whoami` should output `appuser`. `docker compose exec backend touch /test` should fail with "Read-only file system".

---

## Usability

### Accessibility

**Why important**: Many users prefer voice input over typing, especially for Russian text with complex words (poem titles, author names). Voice support makes the bot accessible to a wider audience.

#### Scenario: Voice Search for Poems

| Element | Description |
|---------|-------------|
| **Source** | User who cannot type quickly |
| **Stimulus** | Sends a voice message saying "Пушкин У лукоморья" after `/search` |
| **Environment** | Telegram mobile app |
| **Artifact** | Voice recognition + search pipeline |
| **Response** | Bot finds and displays matching poems |
| **Measure** | Correct poem appears in top 3 results for ≥ 85% of clear voice queries |

**How to test**: Record 10 voice queries for known poems in the database. Verify that the correct poem appears in the search results for at least 8 out of 10 queries.

#### Scenario: Bilingual Interface

| Element | Description |
|---------|-------------|
| **Source** | English-speaking user |
| **Stimulus** | Selects `en` language at onboarding |
| **Environment** | Any Telegram client |
| **Artifact** | All bot responses |
| **Response** | All UI text appears in English |
| **Measure** | 100% of system messages in English after language selection |

**How to test**: Complete full flow (`/start` → `en` → `/library` → pick poem → `/review` → `/help`) and verify all bot messages are in English.
