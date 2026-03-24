# Continuous Integration

## CI Workflow

**File**: [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)

**All runs**: [GitHub Actions](https://github.com/d13-l1t3/PoetryForYou/actions)

**Triggers**: Every push to `main` and every pull request to `main`.

## Pipeline Steps

| Step | Tool | Purpose |
|------|------|---------|
| Lint | `ruff` | Code style checks, unused imports, error detection |
| Security | `bandit` | Vulnerability scanning, hardcoded secret detection |
| Type check | `mypy` | Static type analysis for core modules |
| Tests | `pytest` + `pytest-cov` | Unit & integration tests with coverage |

## Configuration

- **Python version**: 3.11
- **Test database**: SQLite (in-memory for speed)
- **Coverage**: reported via `pytest-cov` with `--cov-report=term-missing`

## Status

The CI pipeline runs automatically. Check the latest run status at [GitHub Actions](https://github.com/d13-l1t3/PoetryForYou/actions).
