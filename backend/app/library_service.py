"""
Library browsing and keyboard navigation service.
Handles poem browsing by authors, themes, and recommendations.
"""
from __future__ import annotations

from typing import Optional, Dict, Any
from sqlmodel import Session, select

from app.db import Poem, User, UserPoemProgress


class LibraryService:
    """Service for browsing poem library via keyboard navigation."""
    
    PAGE_SIZE = 5  # Items per page
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_main_menu(self) -> Dict[str, Any]:
        """Get main library menu options."""
        return {
            "text": "📚 Библиотека стихов\n\nВыберите раздел:",
            "buttons": [
                ["📝 По авторам", "🎭 По темам"],
                ["⭐ Популярные", "🔍 Поиск"],
                ["📖 Мои стихи", "⬅️ Назад"]
            ]
        }
    
    def get_authors_list(self, page: int = 0) -> Dict[str, Any]:
        """Get paginated list of authors."""
        # Get distinct authors from poems
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
            nav_buttons.append(f"⬅️ Стр {page}")
        if page < total_pages - 1:
            nav_buttons.append(f"Стр {page + 2} ➡️")
        nav_buttons.append("⬅️ Назад")
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        return {
            "text": f"👤 Авторы (стр. {page + 1}/{max(1, total_pages)}):\n\nВыберите автора:",
            "buttons": buttons
        }
    
    def get_themes_list(self) -> Dict[str, Any]:
        """Get list of available themes/tags."""
        poems = self.session.exec(select(Poem)).all()
        
        # Extract all tags
        all_tags = set()
        for p in poems:
            if p.tags:
                all_tags.update(t.strip() for t in p.tags.split(','))
        
        themes = sorted(all_tags)
        
        buttons = [[f"🎭 {t}"] for t in themes[:15]]  # Limit to 15 themes
        buttons.append(["⬅️ Назад"])
        
        return {
            "text": "🎭 Темы:\n\nВыберите тему:",
            "buttons": buttons
        }
    
    def get_poems_by_author(self, author: str, page: int = 0) -> Dict[str, Any]:
        """Get poems by a specific author."""
        # Clean author name (remove emoji)
        clean_author = author.replace("👤 ", "").strip()
        
        poems = self.session.exec(
            select(Poem).where(Poem.author == clean_author)
        ).all()
        
        total_pages = (len(poems) + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        start = page * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        page_poems = poems[start:end]
        
        buttons = [[f"📜 {p.title}"] for p in page_poems]
        
        # Add navigation
        nav_buttons = []
        if page > 0:
            nav_buttons.append(f"⬅️ Стр {page}")
        if page < total_pages - 1:
            nav_buttons.append(f"Стр {page + 2} ➡️")
        nav_buttons.append("⬅️ Назад")
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        return {
            "text": f"📚 {clean_author} (стр. {page + 1}/{max(1, total_pages)}):\n\nВыберите стихотворение:",
            "buttons": buttons
        }
    
    def get_poems_by_theme(self, theme: str, page: int = 0) -> Dict[str, Any]:
        """Get poems by a specific theme/tag."""
        # Clean theme name (remove emoji)
        clean_theme = theme.replace("🎭 ", "").strip()
        
        poems = self.session.exec(select(Poem)).all()
        
        # Filter by theme
        matching = [
            p for p in poems 
            if p.tags and clean_theme in [t.strip() for t in p.tags.split(',')]
        ]
        
        total_pages = (len(matching) + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        start = page * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        page_poems = matching[start:end]
        
        buttons = [[f"📜 {p.title} — {p.author}"] for p in page_poems]
        
        # Add navigation
        nav_buttons = []
        if page > 0:
            nav_buttons.append(f"⬅️ Стр {page}")
        if page < total_pages - 1:
            nav_buttons.append(f"Стр {page + 2} ➡️")
        nav_buttons.append("⬅️ Назад")
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        return {
            "text": f"🎭 Тема: {clean_theme} (стр. {page + 1}/{max(1, total_pages)}):\n\nВыберите стихотворение:",
            "buttons": buttons
        }
    
    def get_popular_poems(self, user: User, limit: int = 10) -> Dict[str, Any]:
        """Get popular poems personalized for user."""
        # Get user's learning history
        learned_ids = self.session.exec(
            select(UserPoemProgress.poem_id)
            .where(UserPoemProgress.user_id == user.id)
        ).all()
        learned_ids_set = set(learned_ids)
        
        # Get poems matching user preferences
        poems = self.session.exec(select(Poem)).all()
        
        if not poems:
            return {
                "text": "⭐ Пока нет доступных стихов. Попробуй позже.",
                "buttons": [["⬅️ Назад"]]
            }
        
        # Filter by language preference
        if user.language_pref in ("en", "ru"):
            poems = [p for p in poems if p.language == user.language_pref]
        
        # Exclude already learned
        available = [p for p in poems if p.id not in learned_ids_set]
        
        # If all learned, show all
        if not available:
            available = poems
        
        # Sort by difficulty matching user's level
        level_difficulty = {"beginner": 1, "intermediate": 2, "advanced": 3}
        target_difficulty = level_difficulty.get(user.level, 2)
        
        # Score poems by difficulty match
        scored = []
        for p in available:
            diff_score = abs(p.difficulty - target_difficulty)
            scored.append((diff_score, p))
        
        scored.sort(key=lambda x: x[0])
        top_poems = [p for _, p in scored[:limit]]
        
        if not top_poems:
            return {
                "text": "⭐ Нет рекомендаций. Попробуй /library для поиска.",
                "buttons": [["⬅️ Назад"]]
            }
        
        buttons = [[f"📜 {p.title} — {p.author}"] for p in top_poems]
        buttons.append(["⬅️ Назад"])
        
        return {
            "text": "⭐ Рекомендуемые стихи:\n\nВыбери стихотворение:",
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
                "text": "📖 Ты ещё не начал учить стихи.\n\nНачнём?",
                "buttons": [["📝 По авторам"], ["⭐ Популярные"], ["⬅️ Назад"]]
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
        
        buttons.append(["⬅️ Назад"])
        
        return {
            "text": "📖 Твои стихи:\n\nПродолжи обучение:",
            "buttons": buttons
        }
    
    def parse_library_selection(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse user's library selection and return action info."""
        text = text.strip()
        
        # Main menu
        if text in ["📝 По авторам", "👤 Авторы"]:
            return {"action": "show_authors"}
        
        if text in ["🎭 По темам", "🎭 Темы"]:
            return {"action": "show_themes"}
        
        if text in ["⭐ Популярные", "⭐ Рекомендуемые"]:
            return {"action": "show_popular"}
        
        if text == "📖 Мои стихи":
            return {"action": "show_my_poems"}
        
        if text == "🔍 Поиск":
            return {"action": "search"}
        
        if text == "⬅️ Назад":
            return {"action": "back"}
        
        # Check for author selection
        if text.startswith("👤 "):
            return {"action": "select_author", "author": text}
        
        # Check for theme selection
        if text.startswith("🎭 "):
            return {"action": "select_theme", "theme": text}
        
        # Check for poem selection
        if text.startswith("📜 "):
            # Parse "📜 Title — Author" or "📜 Title"
            poem_text = text.replace("📜 ", "")
            return {"action": "select_poem", "poem_query": poem_text}
        
        # Check for poem with status emoji
        status_emojis = ["🔄", "⏸️", "✅", "🏆"]
        for emoji in status_emojis:
            if text.startswith(f"{emoji} "):
                poem_text = text.replace(f"{emoji} ", "")
                return {"action": "resume_poem", "poem_query": poem_text}
        
        # Pagination
        if "Стр" in text:
            import re
            match = re.search(r'Стр\s*(\d+)', text)
            if match:
                page = int(match.group(1)) - 1
                direction = "prev" if "⬅️" in text else "next"
                return {"action": "paginate", "page": page, "direction": direction}
        
        return None


def get_library_service(session: Session) -> LibraryService:
    """Factory function for LibraryService."""
    return LibraryService(session)
