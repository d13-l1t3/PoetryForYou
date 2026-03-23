"""
Unit tests for PoetryForYou backend.
Tests core functions: normalization, scoring, spaced repetition, i18n, points.
"""
import pytest  # noqa: F401
import sys
import os

# Add backend to path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.service_enhanced import _normalize, _score_answer, _update_spaced_repetition, _calc_points
from app.i18n import t, buttons
from app.db import UserPoemProgress


# ─────────── Test 1: Text Normalization ─────────── #

class TestNormalize:
    def test_lowercase_and_strip(self):
        assert _normalize("  Hello  WORLD  ") == "hello world"

    def test_removes_punctuation(self):
        result = _normalize('Привет, мир! "Тест"')
        assert "," not in result
        assert "!" not in result
        assert '"' not in result

    def test_empty_string(self):
        assert _normalize("") == ""

    def test_only_spaces(self):
        assert _normalize("   ") == ""


# ─────────── Test 2: Similarity Scoring ─────────── #

class TestScoreAnswer:
    def test_exact_match(self):
        score = _score_answer("Буря мглою небо кроет", "Буря мглою небо кроет")
        assert score >= 0.95

    def test_empty_answer(self):
        score = _score_answer("Буря мглою небо кроет", "")
        assert score == 0.0

    def test_empty_expected(self):
        score = _score_answer("", "some text")
        assert score == 0.0

    def test_partial_match(self):
        score = _score_answer("Буря мглою небо кроет", "Буря мглою")
        assert 0.0 < score < 1.0

    def test_completely_wrong(self):
        score = _score_answer("Буря мглою небо кроет", "абвгдежз клмноп")
        assert score < 0.3


# ─────────── Test 3: SM-2 Spaced Repetition ─────────── #

class TestSpacedRepetition:
    def _make_progress(self) -> UserPoemProgress:
        """Create a fresh progress object for testing."""
        return UserPoemProgress(
            user_id=1,
            poem_id=1,
            status="learning",
            reps=0,
            ease=2.3,
            interval_days=0,
            last_score=None
        )

    def test_good_score_increases_interval(self):
        p = self._make_progress()
        _update_spaced_repetition(p, 0.9)  # Good score
        assert p.reps == 1
        assert p.interval_days >= 1
        assert p.ease >= 2.3

    def test_bad_score_resets(self):
        p = self._make_progress()
        p.reps = 3
        p.interval_days = 7
        _update_spaced_repetition(p, 0.3)  # Bad score
        assert p.interval_days == 1
        assert p.status == "learning"
        assert p.ease < 2.3

    def test_mastery_after_4_good_reps(self):
        p = self._make_progress()
        for _ in range(4):
            _update_spaced_repetition(p, 0.9)
        assert p.status == "mastered"
        assert p.reps == 4


# ─────────── Test 4: i18n Translations ─────────── #

class TestI18n:
    def test_english_greeting(self):
        text = t("start_greeting", "en")
        assert "Hi" in text or "help" in text.lower()

    def test_russian_greeting(self):
        text = t("start_greeting", "ru")
        assert "Привет" in text

    def test_fallback_to_russian(self):
        text = t("start_greeting", "unknown_lang")
        assert "Привет" in text  # Should fall back to Russian

    def test_buttons_main_menu(self):
        btns = buttons("main_menu", "en")
        assert "/library" in btns
        assert "/search" in btns

    def test_format_parameters(self):
        text = t("chunk_part", "en", current=1, total=4)
        assert "1" in text
        assert "4" in text


# ─────────── Test 5: Points Calculation ─────────── #

class TestCalcPoints:
    def test_short_poem(self):
        # 5 words -> 5//10 = 0, minimum 1
        assert _calc_points("one two three four five") == 1

    def test_medium_poem(self):
        # 30 words -> 30//10 = 3
        words = " ".join(["word"] * 30)
        assert _calc_points(words) == 3

    def test_long_poem(self):
        # 100 words -> 100//10 = 10
        words = " ".join(["word"] * 100)
        assert _calc_points(words) == 10

    def test_empty_poem(self):
        # Empty string has 1 "word" (empty) -> min 1
        assert _calc_points("") >= 0


# ─────────── Test 6: Text Chunk Splitting ─────────── #

class TestChunkSplitting:
    def test_split_by_stanzas(self):
        from app.service_enhanced import _split_into_chunks
        poem = "Строка один\nСтрока два\n\nСтрока три\nСтрока четыре"
        chunks = _split_into_chunks(poem)
        assert isinstance(chunks, list)
        assert len(chunks) >= 1
        assert all(isinstance(c, str) for c in chunks)

    def test_short_poem_single_chunk(self):
        from app.service_enhanced import _split_into_chunks
        poem = "Короткий стих"
        chunks = _split_into_chunks(poem)
        assert len(chunks) == 1

    def test_empty_poem_chunk(self):
        from app.service_enhanced import _split_into_chunks
        chunks = _split_into_chunks("")
        assert len(chunks) >= 1


# ─────────── Test 7: First Lines Preview ─────────── #

class TestFirstLines:
    def test_two_lines(self):
        from app.service_enhanced import _get_first_lines
        text = "Line one\nLine two\nLine three"
        preview = _get_first_lines(text, 2)
        assert "Line one" in preview
        assert "Line two" in preview

    def test_single_line(self):
        from app.service_enhanced import _get_first_lines
        text = "Only one line"
        preview = _get_first_lines(text, 2)
        assert "Only one line" in preview


# ─────────── Test 8: Hardcoded Search Ranking ─────────── #

class TestSearchRanking:
    def test_title_match_first(self):
        from app.poem_source import HardcodedPoems
        hp = HardcodedPoems()
        results = hp.search_poems("лукоморья", limit=5)
        assert len(results) > 0
        assert "лукоморья" in results[0].title.lower()

    def test_author_search(self):
        from app.poem_source import HardcodedPoems
        hp = HardcodedPoems()
        results = hp.search_poems("Пушкин", limit=10)
        assert len(results) >= 3
        assert all("Пушкин" in p.author for p in results)


# ─────────── Test 9: Language Validation ─────────── #

class TestLanguageValidation:
    def test_valid_languages(self):
        for lang in ("ru", "en", "mix"):
            text = t("start_greeting", lang)
            assert len(text) > 0

    def test_buttons_have_commands(self):
        btns = buttons("main_menu", "ru")
        assert any(b.startswith("/") for b in btns)

    def test_testing_buttons(self):
        btns = buttons("testing", "ru")
        assert isinstance(btns, list)
        assert len(btns) > 0


# ─────────── Test 10: Normalize Edge Cases ─────────── #

class TestNormalizeEdgeCases:
    def test_cyrillic_preserved(self):
        result = _normalize("Привет мир")
        assert "привет" in result

    def test_mixed_language(self):
        result = _normalize("Hello Мир 123")
        assert "hello" in result
        assert "мир" in result

    def test_special_chars_removed(self):
        result = _normalize("Стих—с «кавычками»!")
        assert "«" not in result
        assert "»" not in result
        assert "!" not in result
