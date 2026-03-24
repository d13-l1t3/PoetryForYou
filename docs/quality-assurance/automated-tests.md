# Automated Tests

## Tools

| Tool | Purpose |
|------|---------|
| `pytest` | Test runner |
| `pytest-cov` | Coverage reporting |

## Test Types

### Unit Tests — [`backend/tests/test_unit.py`](../../backend/tests/test_unit.py)

22 unit tests covering:

| Test Class | What It Tests |
|-----------|---------------|
| TestNormalize | Text normalization (lowercase, strip, punctuation) |
| TestScoreAnswer | Similarity scoring (exact, partial, empty, wrong) |
| TestSpacedRepetition | SM-2 algorithm (good/bad scores, mastery) |
| TestI18n | Translations (EN/RU, fallback, formatting) |
| TestCalcPoints | Points calculation (short/medium/long poems) |
| TestChunkSplitting | Poem chunk splitting by stanzas |
| TestFirstLines | Preview text generation |
| TestSearchRanking | Title > author search ranking |
| TestLanguageValidation | Language code validation |
| TestNormalizeEdgeCases | Cyrillic, mixed-language, special chars |

### Integration Tests — [`backend/tests/test_integration.py`](../../backend/tests/test_integration.py)

12 integration tests covering:

| Test Class | What It Tests |
|-----------|---------------|
| TestHealthEndpoint | `GET /health` returns 200 |
| TestStartOnboarding | `/start` creates user, returns language options |
| TestFullOnboarding | Complete onboarding flow |
| TestLibraryBrowsing | `/library` after onboarding |
| TestErrorHandling | Missing text (400), `/help` command |
| TestVoiceEndpoint | Voice validation (422, 413) |
| TestCleanupEndpoint | Session cleanup |
| TestSearchCommand | `/search` sets stage |
| TestProfileCommand | `/profile` returns info |
| TestReviewNoPeems | `/review` with no poems |

## Running Tests

```bash
cd backend
pip install pytest pytest-cov
DATABASE_URL=sqlite:///./test.db pytest tests/ -v --cov=app
```
