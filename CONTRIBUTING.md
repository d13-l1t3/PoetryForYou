# Contributing to PoetryForYou

## Kanban Board

**Board**: [GitHub Issues](https://github.com/d13-l1t3/PoetryForYou/issues)

| Column | Entry Criteria |
|--------|---------------|
| Backlog | Issue created using a template, has labels |
| In Progress | Assigned to a developer, branch created |
| In Review | PR created, linked to issue, reviewers assigned |
| Done | PR merged, issue closed, tests pass in CI |

## Git Workflow

We follow **GitHub Flow** (simplified single-branch model).

### Creating Issues

- Use one of the templates: [User Story](.github/ISSUE_TEMPLATE/user_story.md), [Bug Report](.github/ISSUE_TEMPLATE/bug_report.md), [Technical Task](.github/ISSUE_TEMPLATE/technical_task.md)
- Add appropriate labels: `enhancement`, `bug`, or `tech-debt`
- Assign to a developer and milestone

### Branches

- Branch from `main`
- Naming: `feature/<issue-number>-short-description` or `fix/<issue-number>-short-description`
- Example: `feature/19-voice-search-fix`

### Commits

Format: `<type>: <short description>`

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

Examples:
```
feat: add voice search bypass for search mode
fix: search ranking prioritizes title matches
docs: add architecture diagrams
test: add 5 integration tests
```

### Pull Requests

- Use the [PR template](.github/PULL_REQUEST_TEMPLATE.md)
- Link to the issue with `Closes #N`
- Fill in the checklist (tests, lint, no secrets)
- Request review

### Merging

- Squash merge to `main`
- Delete the feature branch after merge
- Issues are auto-closed when the PR is merged

### Gitgraph

```
main ─────●────●────●────●────●────●──── main
           \       /      \       /
            ●─────●        ●─────●
          feature/19     feature/20
```

## Secrets Management

All secrets are stored in `.env` (never committed):

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from @BotFather |
| `OPENROUTER_API_KEY` | ✅ | API key for LLM |
| `POSTGRES_USER` | ✅ | DB username |
| `POSTGRES_PASSWORD` | ✅ | DB password |
| `POSTGRES_DB` | ✅ | DB name |

**Rules:**
- `.env` is in `.gitignore`
- `.env.example` has placeholder values only
- `bandit` in CI detects hardcoded secrets
- Containers run as non-root (`appuser`)
- Backend is read-only with `tmpfs` for cache

## Development Setup

```bash
# Backend
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt -r requirements-llm.txt
set DATABASE_URL=sqlite:///./poetry.db
uvicorn app.main:app --reload

# Bot
cd bot
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
set TELEGRAM_BOT_TOKEN=your_token
set BACKEND_BASE_URL=http://localhost:8000
python bot.py

# Tests
cd backend
pip install pytest pytest-cov
DATABASE_URL=sqlite:///./test.db pytest tests/ -v --cov=app
```
