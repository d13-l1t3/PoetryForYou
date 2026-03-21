"""
Internationalization helper for localized bot responses.
Returns text and button labels based on user's language preference.
"""
from __future__ import annotations


# Localized strings: {key: {lang: text}}
_STRINGS = {
    # Onboarding
    "start_greeting": {
        "ru": "Привет! Я помогу тебе выучить стихи по частям.\n\nВыбери язык: ru / en / mix",
        "en": "Hi! I'll help you memorize poems step by step.\n\nChoose your language: ru / en / mix",
    },
    "lang_set": {
        "ru": "✅ Язык: {language}\n\nЧто хочешь сделать?",
        "en": "✅ Language: {language}\n\nWhat would you like to do?",
    },
    "choose_lang": {
        "ru": "Пожалуйста, выбери язык: ru, en или mix",
        "en": "Please choose a language: ru, en or mix",
    },
    "fallback_chat": {
        "ru": "Привет! Чем могу помочь?\n\n📚 /library — библиотека\n🎯 /learn — учить стих\n🔄 /review — повторить",
        "en": "Hi! How can I help?\n\n📚 /library — browse poems\n🎯 /learn — learn a poem\n🔄 /review — review",
    },

    # Menu
    "menu_library": {
        "ru": "📚 /library — библиотека",
        "en": "📚 /library — browse poems",
    },
    "menu_learn": {
        "ru": "🎯 /learn — учить стих",
        "en": "🎯 /learn — learn a poem",
    },
    "menu_review": {
        "ru": "🔄 /review — повторить",
        "en": "🔄 /review — review",
    },

    # Learning
    "chunk_part": {
        "ru": "Часть {current} из {total}:",
        "en": "Part {current} of {total}:",
    },
    "memorize_prompt": {
        "ru": "Запомни эту часть. Когда будешь готов — нажми /дальше",
        "en": "Memorize this part. When ready — press /next",
    },
    "ready_next": {
        "ru": "Готов к следующей части?",
        "en": "Ready for the next part?",
    },
    "completed": {
        "ru": "🎉 Поздравляю! Ты выучил весь стих!\n\n📜 {title} — {author}\n\nЧто дальше?",
        "en": "🎉 Congratulations! You've memorized the whole poem!\n\n📜 {title} — {author}\n\nWhat next?",
    },
    "score_great": {
        "ru": "🎉 Отлично! Совпадение: {score}",
        "en": "🎉 Great! Match: {score}",
    },
    "score_hint": {
        "ru": "Совпадение: {score}\n\n🔄 Подсказка:\n\n{chunk}\n\nПопробуй ещё раз:",
        "en": "Match: {score}\n\n🔄 Hint:\n\n{chunk}\n\nTry again:",
    },
    "stopped": {
        "ru": "⏸️ Остановлено.\n\n📜 {title} — {author}\nПрогресс: {learned}/{total} частей\n\nПродолжи позже командой /review или начни новое в /library",
        "en": "⏸️ Paused.\n\n📜 {title} — {author}\nProgress: {learned}/{total} parts\n\nContinue later with /review or start new in /library",
    },
    "no_active": {
        "ru": "Нет активного стиха. Начни с /learn",
        "en": "No active poem. Start with /learn",
    },
    "test_prompt": {
        "ru": "Напиши или скажи эту часть стиха, которую только что выучил:",
        "en": "Type or say the part of the poem you just learned:",
    },
    "hint": {
        "ru": "🔄 Подсказка:\n\n{chunk}\n\nПопробуй ещё раз:",
        "en": "🔄 Hint:\n\n{chunk}\n\nTry again:",
    },

    # Review
    "review_time": {
        "ru": "🔄 Время повторить!\n\n📜 {title} — {author}\n\nВспомни стих и напиши его (или ту часть, что помнишь):",
        "en": "🔄 Time to review!\n\n📜 {title} — {author}\n\nRecall the poem and write it (or as much as you remember):",
    },
    "no_review": {
        "ru": "У тебя нет стихов для повторения.\n\nНачни учить новый!",
        "en": "You have no poems to review.\n\nStart learning a new one!",
    },

    # Search
    "search_found": {
        "ru": "🔍 Нашёл варианты по запросу \"{query}\":\n",
        "en": "🔍 Found results for \"{query}\":\n",
    },
    "search_choose": {
        "ru": "\n\nВыбери номер стиха, который хочешь выучить:",
        "en": "\n\nChoose a poem number to learn:",
    },
    "search_not_found": {
        "ru": "❌ Не нашёл стихи по запросу \"{query}\"\n\nПопробуй:\n• Другие слова из стиха\n• Имя автора\n• Или выбери из /library",
        "en": "❌ No poems found for \"{query}\"\n\nTry:\n• Different words from the poem\n• Author name\n• Or browse /library",
    },
    "cancelled": {
        "ru": "Отменено. Что хочешь сделать?",
        "en": "Cancelled. What would you like to do?",
    },

    # Help — BotFather-style full command menu
    "help": {
        "ru": (
            "📖 *Все команды:*\n\n"
            "📚 *Обучение:*\n"
            "/learn — выучить новый стих\n"
            "/library — открыть библиотеку\n"
            "/review — повторить выученное\n\n"
            "📊 *Мой аккаунт:*\n"
            "/profile — мой профиль и очки\n"
            "/leaderboard — топ-10 учеников\n"
            "/progress — прогресс обучения\n"
            "/setname — установить имя\n\n"
            "⚙️ *Настройки:*\n"
            "/start — начать заново\n"
            "/help — эта справка\n\n"
            "💡 Можешь отправлять голосовые сообщения!\n"
            "Или просто напиши что хочешь выучить."
        ),
        "en": (
            "📖 *All commands:*\n\n"
            "📚 *Learning:*\n"
            "/learn — learn a new poem\n"
            "/library — browse the library\n"
            "/review — review learned poems\n\n"
            "📊 *My account:*\n"
            "/profile — my profile & points\n"
            "/leaderboard — top 10 learners\n"
            "/progress — learning progress\n"
            "/setname — set display name\n\n"
            "⚙️ *Settings:*\n"
            "/start — start over\n"
            "/help — this help\n\n"
            "💡 You can send voice messages!\n"
            "Or just type what you want to learn."
        ),
    },

    # Profile
    "profile": {
        "ru": (
            "👤 *{name}*\n\n"
            "⭐ Очки: *{points}*\n"
            "📜 Стихов выучено: {mastered}\n"
            "📖 В процессе: {learning}\n"
            "📚 Всего попробовано: {total}\n\n"
            "🏅 Место в рейтинге: #{rank}"
        ),
        "en": (
            "👤 *{name}*\n\n"
            "⭐ Points: *{points}*\n"
            "📜 Poems mastered: {mastered}\n"
            "📖 In progress: {learning}\n"
            "📚 Total attempted: {total}\n\n"
            "🏅 Leaderboard rank: #{rank}"
        ),
    },

    "points_earned": {
        "ru": "\n\n⭐ +{pts} очков! (Всего: {total})",
        "en": "\n\n⭐ +{pts} points! (Total: {total})",
    },

    "leaderboard": {
        "ru": "🏆 *Топ-10 учеников:*\n\n{rows}",
        "en": "🏆 *Top 10 Learners:*\n\n{rows}",
    },
    "leaderboard_empty": {
        "ru": "🏆 Пока нет учеников. Стань первым — /learn",
        "en": "🏆 No learners yet. Be the first — /learn",
    },
    "setname_prompt": {
        "ru": "Напиши своё имя для рейтинга (до 20 символов):",
        "en": "Type your display name for the leaderboard (max 20 chars):",
    },
    "setname_done": {
        "ru": "✅ Имя: *{name}*",
        "en": "✅ Name set: *{name}*",
    },

    # Fallback
    "fallback_chat": {
        "ru": "Привет! Чем могу помочь?\n\n📚 /library — библиотека\n🎯 /learn — учить стих\n🔄 /review — повторить",
        "en": "Hi! How can I help?\n\n📚 /library — browse poems\n🎯 /learn — learn a poem\n🔄 /review — review",
    },
}

# Localized button sets
_BUTTONS = {
    "main_menu": {
        "ru": ["/library", "/learn", "/review"],
        "en": ["/library", "/learn", "/review"],
    },
    "learning": {
        "ru": ["/дальше", "/повторить", "/стоп"],
        "en": ["/next", "/repeat", "/stop"],
    },
    "testing": {
        "ru": ["/подсказка", "/пропустить"],
        "en": ["/hint", "/skip"],
    },
    "review": {
        "ru": ["/подсказка", "/не_помню"],
        "en": ["/hint", "/skip"],
    },
    "after_complete": {
        "ru": ["/review", "/library", "/learn"],
        "en": ["/review", "/library", "/learn"],
    },
    "resume": {
        "ru": ["/дальше", "/сначала", "/стоп"],
        "en": ["/next", "/restart", "/stop"],
    },
}


def t(key: str, lang: str = "ru", **kwargs) -> str:
    """Get localized string. Falls back to Russian if not found."""
    strings = _STRINGS.get(key, {})
    # For 'mix' language, default to Russian UI
    effective_lang = lang if lang in ("en", "ru") else "ru"
    text = strings.get(effective_lang, strings.get("ru", f"[{key}]"))
    if kwargs:
        text = text.format(**kwargs)
    return text


def buttons(key: str, lang: str = "ru") -> list[str]:
    """Get localized button set. Falls back to Russian if not found."""
    btn_set = _BUTTONS.get(key, {})
    effective_lang = lang if lang in ("en", "ru") else "ru"
    return btn_set.get(effective_lang, btn_set.get("ru", []))
