"""
Library browsing and keyboard navigation service.
Handles poem browsing by authors, themes, and recommendations.
"""
from __future__ import annotations

from typing import Optional, Dict, Any
from sqlmodel import Session, select

from app.db import Poem, User, UserPoemProgress


# Localized library strings
_LIB = {
    "main_menu": {
        "ru": "📚 Библиотека стихов\n\nВыберите раздел:",
        "en": "📚 Poetry Library\n\nChoose a section:",
    },
    "btn_by_authors": {"ru": "📝 По авторам", "en": "📝 By authors"},
    "btn_by_themes": {"ru": "🎭 По темам", "en": "🎭 By themes"},
    "btn_popular": {"ru": "⭐ Популярные", "en": "⭐ Popular"},
    "btn_search": {"ru": "🔍 Поиск", "en": "🔍 Search"},
    "btn_my_poems": {"ru": "📖 Мои стихи", "en": "📖 My poems"},
    "btn_back": {"ru": "⬅️ Назад", "en": "⬅️ Back"},
    "authors_title": {
        "ru": "👤 Авторы (стр. {page}/{total}):\n\nВыберите автора:",
        "en": "👤 Authors (p. {page}/{total}):\n\nChoose an author:",
    },
    "themes_title": {
        "ru": "🎭 Темы:\n\nВыберите тему:",
        "en": "🎭 Themes:\n\nChoose a theme:",
    },
    "author_poems_title": {
        "ru": "📚 {author} (стр. {page}/{total}):\n\nВыберите стихотворение:",
        "en": "📚 {author} (p. {page}/{total}):\n\nChoose a poem:",
    },
    "theme_poems_title": {
        "ru": "🎭 Тема: {theme} (стр. {page}/{total}):\n\nВыберите стихотворение:",
        "en": "🎭 Theme: {theme} (p. {page}/{total}):\n\nChoose a poem:",
    },
    "popular_title": {
        "ru": "⭐ Рекомендуемые стихи:\n\nВыбери стихотворение:",
        "en": "⭐ Recommended poems:\n\nChoose a poem:",
    },
    "popular_empty": {
        "ru": "⭐ Пока нет доступных стихов. Попробуй позже.",
        "en": "⭐ No poems available yet. Try later.",
    },
    "popular_none": {
        "ru": "⭐ Нет рекомендаций. Попробуй /library для поиска.",
        "en": "⭐ No recommendations. Try /library to browse.",
    },
    "my_poems_title": {
        "ru": "📖 Твои стихи:\n\nПродолжи обучение:",
        "en": "📖 Your poems:\n\nContinue learning:",
    },
    "my_poems_empty": {
        "ru": "📖 Ты ещё не начал учить стихи.\n\nНачнём?",
        "en": "📖 You haven't started learning any poems yet.\n\nShall we begin?",
    },
    "page_prev": {"ru": "⬅️ Стр {page}", "en": "⬅️ P.{page}"},
    "page_next": {"ru": "Стр {page} ➡️", "en": "P.{page} ➡️"},
}


def _lt(key: str, lang: str = "ru", **kwargs) -> str:
    """Get localized library string."""
    strings = _LIB.get(key, {})
    effective_lang = lang if lang in ("en", "ru") else "ru"
    text = strings.get(effective_lang, strings.get("ru", f"[{key}]"))
    if kwargs:
        text = text.format(**kwargs)
    return text


class LibraryService:
    """Service for browsing poem library via keyboard navigation."""
    
    PAGE_SIZE = 5  # Items per page
    
    def __init__(self, session: Session, lang: str = "ru"):
        self.session = session
        self.lang = lang
    
    def get_main_menu(self) -> Dict[str, Any]:
        """Get main library menu options."""
        return {
            "text": _lt("main_menu", self.lang),
            "buttons": [
                [_lt("btn_by_authors", self.lang), _lt("btn_by_themes", self.lang)],
                [_lt("btn_popular", self.lang), _lt("btn_search", self.lang)],
                [_lt("btn_my_poems", self.lang), _lt("btn_back", self.lang)]
            ]
        }
    
    def get_authors_list(self, page: int = 0) -> Dict[str, Any]:
        """Get paginated list of authors."""
        poems = self.session.exec(select(Poem)).all()
        authors = sorted(set(p.author for p in poems if p.author))
        
        total_pages = (len(authors) + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        start = page * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        page_authors = authors[start:end]
        
        buttons = [[f"👤 {a}"] for a in page_authors]
        
        # Add navigation
        nav_buttons = []
        if page > 0:
            nav_buttons.append(_lt("page_prev", self.lang, page=page))
        if page < total_pages - 1:
            nav_buttons.append(_lt("page_next", self.lang, page=page + 2))
        nav_buttons.append(_lt("btn_back", self.lang))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        return {
            "text": _lt("authors_title", self.lang, page=page + 1, total=max(1, total_pages)),
            "buttons": buttons
        }
    
    def get_themes_list(self) -> Dict[str, Any]:
        """Get list of available themes/tags."""
        poems = self.session.exec(select(Poem)).all()
        
        all_tags = set()
        for p in poems:
            if p.tags:
                all_tags.update(t.strip() for t in p.tags.split(','))
        
        themes = sorted(all_tags)
        
        buttons = [[f"🎭 {t}"] for t in themes[:15]]
        buttons.append([_lt("btn_back", self.lang)])
        
        return {
            "text": _lt("themes_title", self.lang),
            "buttons": buttons
        }
    
    def get_poems_by_author(self, author: str, page: int = 0) -> Dict[str, Any]:
        """Get poems by a specific author."""
        clean_author = author.replace("👤 ", "").strip()
        
        poems = self.session.exec(
            select(Poem).where(Poem.author == clean_author)
        ).all()
        
        total_pages = (len(poems) + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        start = page * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        page_poems = poems[start:end]
        
        buttons = [[f"📜 {p.title}"] for p in page_poems]
        
        nav_buttons = []
        if page > 0:
            nav_buttons.append(_lt("page_prev", self.lang, page=page))
        if page < total_pages - 1:
            nav_buttons.append(_lt("page_next", self.lang, page=page + 2))
        nav_buttons.append(_lt("btn_back", self.lang))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        return {
            "text": _lt("author_poems_title", self.lang, author=clean_author, page=page + 1, total=max(1, total_pages)),
            "buttons": buttons
        }
    
    def get_poems_by_theme(self, theme: str, page: int = 0) -> Dict[str, Any]:
        """Get poems by a specific theme/tag."""
        clean_theme = theme.replace("🎭 ", "").strip()
        
        poems = self.session.exec(select(Poem)).all()
        
        matching = [
            p for p in poems 
            if p.tags and clean_theme in [t.strip() for t in p.tags.split(',')]
        ]
        
        total_pages = (len(matching) + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        start = page * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        page_poems = matching[start:end]
        
        buttons = [[f"📜 {p.title} — {p.author}"] for p in page_poems]
        
        nav_buttons = []
        if page > 0:
            nav_buttons.append(_lt("page_prev", self.lang, page=page))
        if page < total_pages - 1:
            nav_buttons.append(_lt("page_next", self.lang, page=page + 2))
        nav_buttons.append(_lt("btn_back", self.lang))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        return {
            "text": _lt("theme_poems_title", self.lang, theme=clean_theme, page=page + 1, total=max(1, total_pages)),
            "buttons": buttons
        }
    
    def get_popular_poems(self, user: User, limit: int = 10) -> Dict[str, Any]:
        """Get popular poems personalized for user."""
        learned_ids = self.session.exec(
            select(UserPoemProgress.poem_id)
            .where(UserPoemProgress.user_id == user.id)
        ).all()
        learned_ids_set = set(learned_ids)
        
        poems = self.session.exec(select(Poem)).all()
        
        if not poems:
            return {
                "text": _lt("popular_empty", self.lang),
                "buttons": [[_lt("btn_back", self.lang)]]
            }
        
        if user.language_pref in ("en", "ru"):
            poems = [p for p in poems if p.language == user.language_pref]
        
        available = [p for p in poems if p.id not in learned_ids_set]
        
        if not available:
            available = poems
        
        level_difficulty = {"beginner": 1, "intermediate": 2, "advanced": 3}
        target_difficulty = level_difficulty.get(user.level, 2)
        
        scored = []
        for p in available:
            diff_score = abs(p.difficulty - target_difficulty)
            scored.append((diff_score, p))
        
        scored.sort(key=lambda x: x[0])
        top_poems = [p for _, p in scored[:limit]]
        
        if not top_poems:
            return {
                "text": _lt("popular_none", self.lang),
                "buttons": [[_lt("btn_back", self.lang)]]
            }
        
        buttons = [[f"📜 {p.title} — {p.author}"] for p in top_poems]
        buttons.append([_lt("btn_back", self.lang)])
        
        return {
            "text": _lt("popular_title", self.lang),
            "buttons": buttons
        }
    
    def get_user_poems(self, user: User) -> Dict[str, Any]:
        """Get user's learning history."""
        progress_items = self.session.exec(
            select(UserPoemProgress, Poem)
            .join(Poem, UserPoemProgress.poem_id == Poem.id)
            .where(UserPoemProgress.user_id == user.id)
            .order_by(UserPoemProgress.last_accessed.desc())
        ).all()
        
        if not progress_items:
            return {
                "text": _lt("my_poems_empty", self.lang),
                "buttons": [[_lt("btn_by_authors", self.lang)], [_lt("btn_popular", self.lang)], [_lt("btn_back", self.lang)]]
            }
        
        buttons = []
        for progress, poem in progress_items[:10]:
            status_emoji = {
                "learning": "🔄",
                "paused": "⏸️",
                "completed": "✅",
                "mastered": "🏆"
            }.get(progress.status, "📜")
            
            buttons.append([f"{status_emoji} {poem.title} — {poem.author}"])
        
        buttons.append([_lt("btn_back", self.lang)])
        
        return {
            "text": _lt("my_poems_title", self.lang),
            "buttons": buttons
        }
    
    def parse_library_selection(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse user's library selection and return action info."""
        text = text.strip()
        
        # Main menu — match both RU and EN buttons
        if text in ["📝 По авторам", "📝 By authors", "👤 Авторы", "👤 Authors"]:
            return {"action": "show_authors"}
        
        if text in ["🎭 По темам", "🎭 By themes", "🎭 Темы", "🎭 Themes"]:
            return {"action": "show_themes"}
        
        if text in ["⭐ Популярные", "⭐ Popular", "⭐ Рекомендуемые", "⭐ Recommended"]:
            return {"action": "show_popular"}
        
        if text in ["📖 Мои стихи", "📖 My poems"]:
            return {"action": "show_my_poems"}
        
        if text in ["🔍 Поиск", "🔍 Search"]:
            return {"action": "search"}
        
        if text in ["⬅️ Назад", "⬅️ Back"]:
            return {"action": "back"}
        
        # Check for author selection
        if text.startswith("👤 "):
            return {"action": "select_author", "author": text}
        
        # Check for theme selection
        if text.startswith("🎭 "):
            return {"action": "select_theme", "theme": text}
        
        # Check for poem selection
        if text.startswith("📜 "):
            poem_text = text.replace("📜 ", "")
            return {"action": "select_poem", "poem_query": poem_text}
        
        # Check for poem with status emoji
        status_emojis = ["🔄", "⏸️", "✅", "🏆"]
        for emoji in status_emojis:
            if text.startswith(f"{emoji} "):
                poem_text = text.replace(f"{emoji} ", "")
                return {"action": "resume_poem", "poem_query": poem_text}
        
        # Pagination (both RU and EN)
        import re
        if "Стр" in text or "P." in text:
            match = re.search(r'(?:Стр|P\.)\s*(\d+)', text)
            if match:
                page = int(match.group(1)) - 1
                direction = "prev" if "⬅️" in text else "next"
                return {"action": "paginate", "page": page, "direction": direction}
        
        return None


def get_library_service(session: Session, lang: str = "ru") -> LibraryService:
    """Factory function for LibraryService."""
    return LibraryService(session, lang)
