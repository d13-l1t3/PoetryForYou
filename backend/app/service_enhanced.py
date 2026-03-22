"""
Enhanced poem learning service with temporary memory and chunk-based learning.
"""
from __future__ import annotations

import re
import random
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple

from sqlmodel import Session, select

from app.db import Interaction, Poem, User, UserPoemProgress, UserPreferences
from app.temp_memory import get_temp_memory, ActivePoemSession
from app.library_service import get_library_service
from app.llm import classify_intent, extract_search_keywords, generate_chat_response
from app.poem_source import fetch_poems_for_user
from app.i18n import t, buttons


def _normalize(text: str) -> str:
    # Remove quotes and special chars, keep only letters, numbers and spaces
    cleaned = re.sub(r'["\'«»„"]', '', text.lower())
    cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
    return " ".join(cleaned.split())


def _extract_poem_title(query: str) -> str:
    """Extract poem title from user query like 'я хочу выучить "Название"' or 'стих: Название'."""
    # Try to extract text in quotes
    quote_patterns = [
        r'["«»„"]([^"«»„"]+)["«»„"]',  # "text" or «text»
        r':\s*([^,.]+)$',  # text after colon at end
        r'стих\s+["\']?([^"\',.]+)["\']?',  # "стих Название"
    ]
    
    for pattern in quote_patterns:
        match = re.search(pattern, query.lower())
        if match:
            return match.group(1).strip()
    
    # If no pattern matched, return full query cleaned
    return query.strip()


def _decode_newlines(s: str) -> str:
    return s.replace("\\n", "\n")


def _get_first_lines(text: str, lines_count: int = 2) -> str:
    """Get first N lines of poem text for preview."""
    decoded = _decode_newlines(text)
    lines = [line.strip() for line in decoded.split('\n') if line.strip()]
    return ' / '.join(lines[:lines_count]) if lines else "..."


def _find_poem_by_query(session: Session, query: str, lang_pref: str) -> Optional[Poem]:
    """Find poem by query with title priority matching."""
    # Extract poem title from query if it's wrapped in quotes or after colon
    extracted_title = _extract_poem_title(query)
    if extracted_title and extracted_title != query:
        print(f"[DEBUG] Extracted title from query: '{extracted_title}' (original: '{query}')")
        query = extracted_title
    
    q = _normalize(query)
    print(f"[DEBUG] Searching for normalized query: '{q}' (lang: {lang_pref})")
    
    if len(q) < 2:
        return None

    # Get all poems
    poem_query = select(Poem)
    if lang_pref in ("en", "ru"):
        poem_query = poem_query.where(Poem.language == lang_pref)

    poems = session.exec(poem_query).all()
    print(f"[DEBUG] Found {len(poems)} poems in local DB")
    
    if not poems:
        return None
    
    # PRIORITY 1: Exact match in title
    for p in poems:
        title_normalized = _normalize(p.title)
        if q == title_normalized or q in title_normalized:
            print(f"[DEBUG] Found exact title match: {p.title}")
            return p
    
    # PRIORITY 2: Check each word from query is in title
    query_words = q.split()
    for p in poems:
        title_normalized = _normalize(p.title)
        title_words = title_normalized.split()
        matches = sum(1 for w in query_words if w in title_words)
        if matches == len(query_words) or (len(query_words) > 2 and matches >= len(query_words) - 1):
            print(f"[DEBUG] Found word match in title: {p.title} ({matches} matches)")
            return p
    
    # PRIORITY 3: Author match
    for p in poems:
        author_normalized = _normalize(p.author)
        if q in author_normalized:
            print(f"[DEBUG] Found author match: {p.author}")
            return p
    
    # PRIORITY 4: Fuzzy search with scoring
    best_score = 0
    best_poem: Optional[Poem] = None
    
    for p in poems:
        score = 0
        title_normalized = _normalize(p.title)
        query_words = q.split()
        title_words = title_normalized.split()
        
        for qw in query_words:
            if qw in title_words:
                score += 10
            elif qw in _normalize(p.author):
                score += 5
            elif qw in _normalize(_decode_newlines(p.text)):
                score += 1
        
        if q in title_normalized:
            score += 20
        
        if score > best_score:
            best_score = score
            best_poem = p

    if best_poem and best_score >= 5:
        print(f"[DEBUG] Found fuzzy match (score {best_score}): {best_poem.title}")
        return best_poem

    # Last resort: try external source if not found locally
    print("[DEBUG] No local match found, trying external source (rupoem.ru)")
    try:
        external_poems = fetch_poems_for_user(query, limit=1)
        external_poem = external_poems[0] if external_poems else None
        if external_poem:
            print(f"[DEBUG] Found external poem: {external_poem.title} by {external_poem.author}")
            poem = Poem(
                language=external_poem.language,
                title=external_poem.title,
                author=external_poem.author,
                text=external_poem.text,
                tags=external_poem.tags,
                difficulty=external_poem.difficulty
            )
            session.add(poem)
            session.commit()
            session.refresh(poem)
            return poem
        else:
            print("[DEBUG] External source returned no results")
    except Exception as e:
        print(f"[DEBUG] External source error: {e}")

    return None


def get_or_create_user(session: Session, telegram_id: int) -> User:
    user = session.exec(select(User).where(User.telegram_id == telegram_id)).first()
    if user is None:
        user = User(telegram_id=telegram_id)
        session.add(user)
        session.commit()
        session.refresh(user)
        
        # Create default preferences
        prefs = UserPreferences(user_id=user.id)
        session.add(prefs)
        session.commit()
    return user


def _set_stage(session: Session, user: User, stage: str) -> None:
    user.stage = stage
    session.add(user)
    session.commit()


def _get_or_create_progress(session: Session, user_id: int, poem_id: int, total_chunks: int = 0) -> UserPoemProgress:
    """Get or create user's progress record for a poem."""
    progress = session.exec(
        select(UserPoemProgress)
        .where(UserPoemProgress.user_id == user_id)
        .where(UserPoemProgress.poem_id == poem_id)
    ).first()
    
    if progress is None:
        progress = UserPoemProgress(
            user_id=user_id,
            poem_id=poem_id,
            total_chunks=total_chunks
        )
        session.add(progress)
        session.commit()
        session.refresh(progress)
    
    return progress


def _save_progress_from_session(session: Session, temp_session: ActivePoemSession) -> None:
    """Save progress from temporary session to persistent storage."""
    progress = _get_or_create_progress(
        session, 
        temp_session.user_id, 
        temp_session.poem_id,
        len(temp_session.chunks)
    )
    
    progress.last_chunk_index = temp_session.current_chunk_index
    progress.total_chunks = len(temp_session.chunks)
    progress.learned_chunks = ",".join(map(str, temp_session.learned_chunks))
    progress.last_accessed = datetime.now(timezone.utc)
    
    # Save last learned text for context
    if temp_session.learned_chunks:
        last_chunk_idx = temp_session.learned_chunks[-1]
        progress.last_session_text = temp_session.chunks[last_chunk_idx][:200]
    
    # Update status
    if temp_session.current_chunk_index >= len(temp_session.chunks):
        progress.status = "completed"
        progress.completed_at = datetime.now(timezone.utc)
    else:
        progress.status = "paused"
    
    session.add(progress)
    session.commit()


def _restore_progress_to_session(session: Session, user_id: int, poem: Poem, temp_memory) -> Optional[ActivePoemSession]:
    """Restore user's progress from DB to temporary session."""
    progress = session.exec(
        select(UserPoemProgress)
        .where(UserPoemProgress.user_id == user_id)
        .where(UserPoemProgress.poem_id == poem.id)
    ).first()
    
    if not progress:
        return None
    
    # Create new session with restored state
    chunk_size = 4
    lines = _decode_newlines(poem.text).split('\n')
    chunks = []
    
    for i in range(0, len(lines), chunk_size):
        chunk_lines = lines[i:i + chunk_size]
        chunk_text = '\n'.join(chunk_lines).strip()
        if chunk_text:
            chunks.append(chunk_text)
    
    if progress.learned_chunks:
        learned_chunks = [int(x) for x in progress.learned_chunks.split(',') if x.strip()]
    else:
        learned_chunks = []
    
    temp_session = ActivePoemSession(
        user_id=user_id,
        poem_id=poem.id,
        poem_title=poem.title,
        poem_author=poem.author,
        full_text=_decode_newlines(poem.text),
        chunks=chunks,
        current_chunk_index=progress.last_chunk_index,
        learned_chunks=learned_chunks
    )
    
    temp_memory._sessions[user_id] = temp_session
    return temp_session


def _pick_recommendation(session: Session, user: User, temp_memory) -> Poem:
    """Pick a poem recommendation considering user preferences and history."""
    # First check if there's a restored session
    if user.active_poem_id:
        existing_session = temp_memory.get_session(user.id)
        if existing_session:
            poem = session.get(Poem, user.active_poem_id)
            if poem:
                return poem
    
    # Get user preferences
    prefs = session.exec(
        select(UserPreferences).where(UserPreferences.user_id == user.id)
    ).first()
    
    # Get user's learning history
    learned_ids = session.exec(
        select(UserPoemProgress.poem_id).where(UserPoemProgress.user_id == user.id)
    ).all()
    learned_ids_set = set(learned_ids)
    
    # Build query based on preferences
    poem_query = select(Poem)
    
    # Language filter
    if user.language_pref in ("en", "ru"):
        poem_query = poem_query.where(Poem.language == user.language_pref)
    
    poems = session.exec(poem_query).all()
    
    # Score poems based on user preferences
    scored_poems = []
    for p in poems:
        if p.id in learned_ids_set:
            continue
        
        score = 0
        
        # Difficulty match
        level_difficulty = {"beginner": 1, "intermediate": 2, "advanced": 3}
        target_diff = level_difficulty.get(user.level, 2)
        diff_distance = abs(p.difficulty - target_diff)
        score += max(0, 3 - diff_distance)
        
        # Theme preference match
        if prefs and prefs.preferred_themes and p.tags:
            user_themes = [t.strip() for t in prefs.preferred_themes.split(',')]
            poem_tags = [t.strip() for t in p.tags.split(',')]
            matches = len(set(user_themes) & set(poem_tags))
            score += matches * 2
        
        # Poet preference match
        if prefs and prefs.favorite_poets:
            favorite_poets = [poet.strip().lower() for poet in prefs.favorite_poets.split(',')]
            if p.author.lower() in favorite_poets:
                score += 3
        
        scored_poems.append((score, p))
    
    # Sort by score and pick top
    scored_poems.sort(key=lambda x: x[0], reverse=True)
    
    if scored_poems:
        # Pick from top 5 with some randomness for variety
        top_n = min(5, len(scored_poems))
        return random.choice([p for _, p in scored_poems[:top_n]])
    
    # Fallback: any available poem
    available = [p for p in poems if p.id not in learned_ids_set]
    if available:
        return random.choice(available)
    
    # Last resort: fetch from external source
    externals = fetch_poems_for_user(limit=1)
    external = externals[0] if externals else None
    if external:
        poem = Poem(
            language=external.language,
            title=external.title,
            author=external.author,
            text=external.text,
            tags=external.tags,
            difficulty=external.difficulty
        )
        session.add(poem)
        session.commit()
        session.refresh(poem)
        return poem
    
    # Ultimate fallback: return any poem from DB
    all_poems = session.exec(select(Poem)).all()
    if all_poems:
        return random.choice(all_poems)
    
    raise RuntimeError("No poems available")


def _score_answer(expected: str, answer: str) -> float:
    """Score user's answer against expected text.
    
    Uses two scoring methods and picks the best:
    1. Word overlap (bag-of-words) — tolerant of word order changes
    2. Sequence similarity — rewards correct word order
    
    Also normalizes ё→е and strips punctuation for fairer voice comparison.
    """
    def _clean(s: str) -> str:
        # Normalize ё→е (Whisper often transcribes ё as е)
        s = s.replace('ё', 'е').replace('Ё', 'Е')
        # Remove all punctuation
        s = re.sub(r'[^\w\s]', '', s)
        return _normalize(s)
    
    exp_clean = _clean(expected)
    ans_clean = _clean(answer)
    
    if not exp_clean:
        return 0.0
    
    exp_words = exp_clean.split()
    ans_words = ans_clean.split()
    
    if not exp_words:
        return 0.0
    
    # Method 1: Word overlap (bag-of-words)
    exp_set = set(exp_words)
    ans_set = set(ans_words)
    overlap_score = len(exp_set & ans_set) / len(exp_set) if exp_set else 0.0
    
    # Method 2: Sequence similarity (order-aware)
    from difflib import SequenceMatcher
    seq_score = SequenceMatcher(None, exp_clean, ans_clean).ratio()
    
    raw_score = max(overlap_score, seq_score)
    
    # Length ratio penalty: if user wrote much less than expected,
    # scale the score down proportionally. This prevents 2-line answers
    # from getting 90%+ on a 30-line poem.
    length_ratio = min(1.0, len(ans_words) / max(len(exp_words), 1))
    if length_ratio < 0.5:
        # Severe penalty for very short answers
        raw_score *= length_ratio * 1.5  # e.g. 10% of words → 15% of score
    elif length_ratio < 0.8:
        # Moderate penalty
        raw_score *= (0.5 + length_ratio * 0.5)  # e.g. 60% of words → 80% of score
    
    return min(1.0, raw_score)


def _update_spaced_repetition(progress: UserPoemProgress, score: float) -> None:
    """Update spaced repetition schedule based on quiz score."""
    if score >= 0.75:
        progress.reps += 1
        progress.ease = min(2.7, progress.ease + 0.05)
        progress.interval_days = 1 if progress.interval_days == 0 else int(progress.interval_days * progress.ease)
        if progress.interval_days < 1:
            progress.interval_days = 1
        if progress.reps >= 4:
            progress.status = "mastered"
    else:
        progress.ease = max(1.3, progress.ease - 0.1)
        progress.interval_days = 1
        progress.status = "learning"
    
    progress.last_score = score
    progress.due_at = datetime.now(timezone.utc) + timedelta(days=progress.interval_days)


def _make_library_response(library_result: Dict[str, Any]) -> Tuple[str, List[str], str]:
    """Convert library service result to response format."""
    text = library_result.get("text", "")
    btn_rows = library_result.get("buttons", [])
    # Flatten ALL buttons from all rows (not just first per row)
    suggested = [b for row in btn_rows for b in row] if btn_rows else []
    return text, suggested, "library"


# ────────────────────  GAMIFICATION  ──────────────────── #

def _calc_points(poem_text: str) -> int:
    """Calculate points for a poem: word_count ÷ 10, minimum 1."""
    word_count = len(poem_text.split())
    return max(1, word_count // 10)


def _award_points(session: Session, user: User, poem_text: str) -> int:
    """Award points to user for completing a poem. Returns points earned."""
    pts = _calc_points(poem_text)
    user.total_points = (user.total_points or 0) + pts
    session.add(user)
    session.commit()
    return pts


def _get_user_rank(session: Session, user_id: int) -> int:
    """Get user's rank in the leaderboard (1-indexed)."""
    all_users = session.exec(
        select(User).where(User.total_points >= 0).order_by(User.total_points.desc())
    ).all()
    # Filter to users who have progress records
    ranked = [u for u in all_users if session.exec(
        select(UserPoemProgress).where(UserPoemProgress.user_id == u.id)
    ).first() is not None]
    for i, u in enumerate(ranked, 1):
        if u.id == user_id:
            return i
    return len(ranked) + 1


def _get_profile_response(session: Session, user: User) -> Tuple[str, List[str], str]:
    """Build /profile response with points, poems, rank."""
    lang = user.language_pref

    # Count poems by status
    progresses = session.exec(
        select(UserPoemProgress).where(UserPoemProgress.user_id == user.id)
    ).all()
    mastered = sum(1 for p in progresses if p.status in ("completed", "mastered"))
    learning = sum(1 for p in progresses if p.status in ("learning", "paused"))
    total = len(progresses)

    rank = _get_user_rank(session, user.id)
    name = user.display_name or f"User #{user.telegram_id}"

    return (
        t("profile", lang,
          name=name,
          points=user.total_points or 0,
          mastered=mastered,
          learning=learning,
          total=total,
          rank=rank),
        ["/leaderboard", "/library", "/learn"],
        "profile"
    )


def _get_leaderboard_response(session: Session, user: User) -> Tuple[str, List[str], str]:
    """Build /leaderboard response with top 10 users."""
    lang = user.language_pref

    top_users = session.exec(
        select(User).where(User.total_points >= 0).order_by(User.total_points.desc())
    ).all()
    
    # Filter to users who have actually attempted poems
    top_users = [u for u in top_users if session.exec(
        select(UserPoemProgress).where(UserPoemProgress.user_id == u.id)
    ).first() is not None][:10]

    if not top_users:
        return (t("leaderboard_empty", lang), ["/learn", "/library"], "leaderboard")

    rows = []
    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(top_users[:10], 1):
        medal = medals[i - 1] if i <= 3 else f"{i}."
        name = u.display_name or f"User #{u.telegram_id}"
        marker = " ← you" if lang == "en" and u.id == user.id else (" ← ты" if u.id == user.id else "")
        rows.append(f"{medal} *{name}* — {u.total_points} ⭐{marker}")

    return (
        t("leaderboard", lang, rows="\n".join(rows)),
        ["/profile", "/library", "/learn"],
        "leaderboard"
    )


def _get_progress_response(session: Session, user: User, temp_memory) -> Tuple[str, List[str], str]:
    """Build /progress response showing learning stats."""
    lang = user.language_pref

    progresses = session.exec(
        select(UserPoemProgress).where(UserPoemProgress.user_id == user.id)
    ).all()

    if not progresses:
        text = "📊 " + ("No progress yet. Start with /learn!" if lang == "en" else "Прогресса пока нет. Начни с /learn!")
        return (text, ["/learn", "/library"], "progress")

    mastered = [p for p in progresses if p.status in ("completed", "mastered")]
    learning = [p for p in progresses if p.status in ("learning", "paused")]
    points = user.total_points or 0

    lines = [
        "📊 " + ("*My progress:*" if lang == "en" else "*Мой прогресс:*"),
        "",
        "⭐ " + (f"Points: *{points}*" if lang == "en" else f"Очки: *{points}*"),
        "✅ " + (f"Mastered: {len(mastered)}" if lang == "en" else f"Выучено: {len(mastered)}"),
        "📖 " + (f"In progress: {len(learning)}" if lang == "en" else f"В процессе: {len(learning)}"),
    ]

    if mastered:
        lines.append("")
        lines.append("🏆 " + ("*Mastered:*" if lang == "en" else "*Выученные:*"))
        for p in mastered[:5]:
            poem = session.get(Poem, p.poem_id)
            if poem:
                lines.append(f"  📜 {poem.title} — {poem.author}")

    if learning:
        lines.append("")
        lines.append("📖 " + ("*In progress:*" if lang == "en" else "*В процессе:*"))
        for p in learning[:5]:
            poem = session.get(Poem, p.poem_id)
            if poem:
                pct = int(len(p.learned_chunks.split(",")) / max(p.total_chunks, 1) * 100) if p.learned_chunks else 0
                lines.append(f"  📜 {poem.title} — {pct}%")

    return ("\n".join(lines), ["/profile", "/leaderboard", "/library"], "progress")


def handle_message(
    session: Session, 
    telegram_id: int, 
    text: Optional[str]
) -> Tuple[str, List[str], str]:
    """
    Main message handler with support for:
    - Chunk-based poem learning with temporary memory
    - Library browsing via keyboard navigation
    - Auto-save after 5 minutes of inactivity
    """
    user = get_or_create_user(session, telegram_id)
    raw = (text or "").strip()
    incoming = _normalize(text or "")
    
    # Get temporary memory
    temp_memory = get_temp_memory()
    
    # Check for active temporary session
    active_session = temp_memory.get_session(user.id)
    
    # === POEM SELECTION MODE (highest priority) ===
    if user.stage == "choosing_poem":
        print(f"[DEBUG] In choosing_poem mode, raw={repr(raw)}")
        poem_selections = getattr(temp_memory, '_poem_selections', {})
        print(f"[DEBUG] Available keys in _poem_selections: {list(poem_selections.keys())}")
        print(f"[DEBUG] User telegram_id: {user.telegram_id}")
        
        # Check if user wants to cancel
        if raw in ("❌ /отмена", "/отмена", "❌ /cancel", "/cancel"):
            print("[DEBUG] User cancelled selection")
            # Clean up selection data
            if hasattr(temp_memory, '_poem_selections'):
                temp_memory._poem_selections.pop(user.telegram_id, None)
            user.stage = "idle"
            session.add(user)
            session.commit()
            lang = user.language_pref
            return (
                t("cancelled", lang),
                buttons("main_menu", lang),
                "menu"
            )
        
        # Try to parse selection number FIRST (before LLM classification)
        try:
            selection = int(raw.strip())
            print(f"[DEBUG] Parsed selection: {selection}")
            selection_data = poem_selections.get(user.telegram_id)
            print(f"[DEBUG] Selection data exists: {selection_data is not None}")
            
            if selection_data:
                options = selection_data.get("options", [])
                print(f"[DEBUG] Options available: {len(options)}")
                
                if 1 <= selection <= len(options):
                    selected_poem = options[selection - 1]
                    print(f"[DEBUG] Selected poem: {selected_poem.title}")
                    
                    # Clean up selection data
                    poem_selections.pop(user.telegram_id, None)
                    
                    # Check if poem already exists in DB (avoid duplicates)
                    existing = session.exec(
                        select(Poem).where(
                            Poem.title == selected_poem.title,
                            Poem.author == selected_poem.author
                        )
                    ).first()
                    
                    if existing:
                        poem = existing
                    else:
                        poem = Poem(
                            language=selected_poem.language,
                            title=selected_poem.title,
                            author=selected_poem.author,
                            text=selected_poem.text,
                            tags=selected_poem.tags,
                            difficulty=selected_poem.difficulty
                        )
                        session.add(poem)
                        session.commit()
                        session.refresh(poem)
                    
                    print("[DEBUG] Calling _start_specific_poem_learning")
                    # Start learning this poem
                    result = _start_specific_poem_learning(session, user, poem, temp_memory)
                    print(f"[DEBUG] Result stage: {result[2]}")
                    return result
                else:
                    lang = user.language_pref
                    return (
                        t("invalid_number", lang, max=len(options)),
                        [str(i+1) for i in range(len(options))] + ["❌ /отмена" if lang != "en" else "❌ /cancel"],
                        "choosing"
                    )
        except (ValueError, IndexError):
            print(f"[DEBUG] Failed to parse selection: {raw}")
            pass
        
        # If invalid input, show options again
        selection_data = poem_selections.get(user.telegram_id)
        if selection_data:
            options = selection_data.get("options", [])
            cancel_text = "❌ /cancel" if user.language_pref == "en" else "❌ /отмена"
            btn_list = [str(i+1) for i in range(len(options))] + [cancel_text]
            print("[DEBUG] Showing options again")
            lang = user.language_pref
            return (
                t("choose_poem_prompt", lang),
                btn_list,
                "choosing"
            )
    
    # === ONBOARDING: LANGUAGE SELECTION ===
    if user.stage == "onboarding_language":
        if incoming in ("ru", "en", "mix"):
            user.language_pref = incoming
            user.stage = "idle"
            session.add(user)
            session.commit()
            lang = user.language_pref
            return (
                t("lang_set", lang, language=lang.upper()) + "\n" +
                t("menu_library", lang) + "\n" +
                t("menu_learn", lang) + "\n" +
                t("menu_review", lang),
                buttons("main_menu", lang),
                "settings"
            )
        return (
            t("choose_lang", user.language_pref),
            ["ru", "en", "mix"],
            "onboarding"
        )
    
    # === SLASH COMMANDS ===
    if raw.startswith("/"):
        cmd = raw.split()[0].lower()
        
        if cmd == "/start":
            _set_stage(session, user, "onboarding_language")
            return (
                t("start_greeting", user.language_pref),
                ["ru", "en", "mix"],
                "onboarding"
            )
        
        if cmd in ("/lang_en", "/lang_ru", "/lang_mix"):
            lang_map = {"/lang_en": "en", "/lang_ru": "ru", "/lang_mix": "mix"}
            user.language_pref = lang_map[cmd]
            user.stage = "idle"
            session.add(user)
            session.commit()
            lang = user.language_pref
            return (
                t("lang_changed", lang, language=lang.upper()) + "\n" +
                t("menu_library", lang) + "\n" +
                t("menu_learn", lang) + "\n" +
                t("menu_review", lang),
                buttons("main_menu", lang),
                "settings"
            )
        
        if cmd == "/library":
            user.stage = "library_menu"
            session.add(user)
            session.commit()
            
            library = get_library_service(session)
            result = library.get_main_menu()
            return _make_library_response(result)
        
        if cmd in ("/search", "/поиск", "/найти"):
            user.stage = "searching"
            session.add(user)
            session.commit()
            lang = user.language_pref
            return (
                ("🔍 Type what you're looking for:\n\n"
                 "• Poem title or first line\n"
                 "• Author name\n"
                 "• Or describe what kind of poem you want"
                 if lang == "en" else
                 "🔍 Напиши или скажи голосом, что ищешь:\n\n"
                 "• Название или первую строку стиха\n"
                 "• Имя автора\n"
                 "• Или опиши, какой стих хочешь"),
                ["/library", "/review"],
                "search"
            )
        
        if cmd in ("/learn", "/recommend"):
            return _start_poem_learning(session, user, temp_memory)
        
        if cmd == "/review":
            return _start_review(session, user, temp_memory)
        
        # Commands that interact with active session or review
        if cmd in ("/next", "/дальше", "/следующий", "/продолжить"):
            if active_session:
                if user.stage == "learning_chunk":
                    # Don't call get_next_chunk() here! The chunk was already
                    # consumed when it was displayed. Just switch to testing.
                    user.stage = "testing_chunk"
                    session.add(user)
                    session.commit()
                    lang = user.language_pref
                    return (
                        f"👂\n\n{t('test_prompt', lang)}",
                        buttons("testing", lang),
                        "testing"
                    )
                elif user.stage == "testing_chunk":
                    user.stage = "learning_chunk"
                    session.add(user)
                    session.commit()
                    return _get_next_chunk_response(session, user, active_session)
                else:
                    return _get_next_chunk_response(session, user, active_session)
            else:
                lang = user.language_pref
                return (
                    ("No active poem. Start with /learn" if lang == "en" else
                     "Нет активного стиха. Начни с /learn"),
                    ["/learn", "/library"],
                    "help"
                )
        
        if cmd in ("/повторить", "/repeat", "/подсказка", "/hint", "/не_помню", "/забыл", "/не_знаю"):
            # In review mode — show full poem hint
            if user.stage == "reviewing" and user.active_poem_id:
                poem = session.get(Poem, user.active_poem_id)
                if poem:
                    lang = user.language_pref
                    return (
                        t("review_hint_full", lang,
                          title=poem.title,
                          author=poem.author,
                          preview=_decode_newlines(poem.text)[:200]),
                        buttons("review", lang),
                        "review"
                    )
            # In active learning session — show current chunk hint
            if active_session:
                current = active_session.get_current_chunk()
                if current:
                    lang = user.language_pref
                    if user.stage == "testing_chunk":
                        return (
                            t("hint", lang, chunk=current),
                            buttons("testing", lang),
                            "testing"
                        )
                    else:
                        return (
                            t("hint", lang, chunk=current),
                            buttons("learning", lang),
                            "learning"
                        )
            else:
                lang = user.language_pref
                return (
                    ("No active poem. Start with /learn" if lang == "en" else
                     "Нет активного стиха. Начни с /learn"),
                    ["/learn", "/library"],
                    "help"
                )
        
        if cmd in ("/пропустить", "/skip"):
            if active_session and user.stage == "testing_chunk":
                user.stage = "learning_chunk"
                session.add(user)
                session.commit()
                return _get_next_chunk_response(session, user, active_session)
        
        if cmd in ("/стоп", "/stop", "/выйти"):
            if active_session:
                _save_progress_from_session(session, active_session)
                temp_memory.remove_session(user.id)
            user.active_poem_id = None
            user.stage = "idle"
            session.add(user)
            session.commit()
            lang = user.language_pref
            return (
                ("Stopped. What's next?" if lang == "en" else
                 "Остановлено. Что делаем дальше?"),
                buttons("main_menu", lang),
                "paused"
            )
        
        if cmd == "/progress":
            return _get_progress_response(session, user, temp_memory)
        
        if cmd == "/help":
            return (
                t("help", user.language_pref),
                buttons("main_menu", user.language_pref),
                "help"
            )
        
        if cmd == "/profile":
            return _get_profile_response(session, user)
        
        if cmd == "/leaderboard":
            return _get_leaderboard_response(session, user)
        
        if cmd == "/setname":
            user.stage = "setting_name"
            session.add(user)
            session.commit()
            return (
                t("setname_prompt", user.language_pref),
                buttons("main_menu", user.language_pref),
                "setname"
            )
    
    # === SETTING NAME STAGE ===
    if user.stage == "setting_name" and raw and not raw.startswith("/"):
        name = raw.strip()[:20]
        user.display_name = name
        user.stage = "idle"
        session.add(user)
        session.commit()
        return (
            t("setname_done", user.language_pref, name=name),
            buttons("main_menu", user.language_pref),
            "setname"
        )

    # === LIBRARY NAVIGATION ===
    # Check raw text for emoji buttons (not normalized, emojis removed in normalize)
    if user.stage.startswith("library") or raw.startswith(("📝", "🎭", "⭐", "📖", "👤", "📜", "⬅️", "🔍")):
        library = get_library_service(session)
        action = library.parse_library_selection(raw)
        
        if action:
            return _handle_library_action(session, user, library, action, temp_memory)
        
        # If we're in library stage but action is None (unrecognized input like voice),
        # reset stage to idle so intent classification can handle it below
        if user.stage.startswith("library") and raw and not raw.startswith("/"):
            user.stage = "idle"
            session.add(user)
            session.commit()
            # Fall through to intent classification below
    
    # === SEARCHING MODE (user typed /search and now sends query) ===
    if user.stage == "searching" and raw and not raw.startswith("/"):
        # Treat any text (including voice transcription) as a search query
        # directly — skip LLM intent classification
        user.stage = "idle"
        session.add(user)
        session.commit()
        
        # Extract search keywords and search
        search_query = extract_search_keywords(raw)
        print(f"[DEBUG] Search mode: extracted keywords '{search_query}' from '{raw}'")
        
        external_poems = fetch_poems_for_user(search_query, limit=10)
        
        if external_poems and len(external_poems) > 0:
            temp_memory._poem_selections = getattr(temp_memory, '_poem_selections', {})
            temp_memory._poem_selections[user.telegram_id] = {
                "options": external_poems,
                "query": search_query
            }
            user.stage = "choosing_poem"
            session.add(user)
            session.commit()
            
            lang = user.language_pref
            message_lines = [t("search_found", lang, query=search_query)]
            btn_list = []
            
            for i, ext_poem in enumerate(external_poems[:10], 1):
                preview = _get_first_lines(ext_poem.text, 2)
                message_lines.append(
                    f"\n{i}. 📜 {ext_poem.title} — {ext_poem.author}\n"
                    f"   \"{preview}\""
                )
                btn_list.append(str(i))
            
            message_lines.append(t("search_choose", lang))
            btn_list.append("❌ /cancel" if lang == "en" else "❌ /отмена")
            
            return (
                "\n".join(message_lines),
                btn_list,
                "choosing"
            )
        
        lang = user.language_pref
        return (
            t("search_not_found", lang, query=search_query),
            ["/library", "/learn"],
            "not_found"
        )
    
    # === REVIEW MODE ===
    if user.stage == "reviewing" and user.active_poem_id:
        # Check user's answer (any non-command text)
        if raw and not raw.startswith("/"):
            return _check_review_answer(session, user, temp_memory, raw)
    
    # === ACTIVE CHUNK LEARNING SESSION ===
    if active_session:
        # Check if user is trying to reproduce the chunk (testing phase)
        if user.stage == "testing_chunk" and raw and not raw.startswith("/"):
            return _check_chunk_reproduction(session, user, active_session, raw)
        
        # AUTO-TEST: If user sends free text/voice during learning phase,
        # treat it as a reproduction attempt (auto-enter testing)
        if user.stage == "learning_chunk" and raw and not raw.startswith("/"):
            # Don't call get_next_chunk() — the chunk is already consumed
            # when it was displayed. Just switch to testing and check.
            user.stage = "testing_chunk"
            session.add(user)
            session.commit()
            return _check_chunk_reproduction(session, user, active_session, raw)
    
    # === IDLE INTENTS: NEW POEM SEARCH (check first before resume) ===
    # Skip LLM classification for single digits (poem selection)
    if not (user.stage == "choosing_poem" and raw.strip().isdigit()):
        inferred = classify_intent(text or "")
    else:
        inferred = None
    
    # Handle ALL chat intents (greetings, small talk, general questions)
    if inferred == "chat":
        lang = user.language_pref
        response = generate_chat_response(text or "", lang)
        return (response, buttons("main_menu", lang), "chat")
    
    # Handle help intent with LLM response too
    if inferred == "help":
        lang = user.language_pref
        response = generate_chat_response(text or "", lang)
        return (response, buttons("main_menu", lang), "help")
    
    # If user explicitly wants to learn a specific poem, search for it first
    if inferred and (inferred in ("recommend", "learn", "start") or any(k in incoming for k in ("выуч", "учить", "стих", "поэма"))):
        # Check if this is a specific poem search (with quotes or long query)
        has_quotes = any(c in raw for c in '"«"')
        is_specific_search = has_quotes or len(raw) > 15
        
        # Only check local DB for exact matches if it looks like a specific search
        if is_specific_search:
            # Try exact match ONLY - no fuzzy fallback
            extracted_title = _extract_poem_title(raw)
            if extracted_title:
                q = _normalize(extracted_title)
                # Look for exact match in local DB only
                poem_query = select(Poem).where(Poem.language == user.language_pref) if user.language_pref in ("en", "ru") else select(Poem)
                poems = session.exec(poem_query).all()
                for p in poems:
                    if q == _normalize(p.title):
                        print(f"[DEBUG] Found exact local match: {p.title}")
                        return _start_specific_poem_learning(session, user, p, temp_memory)
            # No exact local match - go directly to external search
            print(f"[DEBUG] No exact local match for '{raw}', going to external search")
        else:
            # For short/generic queries, try local fuzzy search first
            poem = _find_poem_by_query(session, raw, user.language_pref)
            if poem:
                return _start_specific_poem_learning(session, user, poem, temp_memory)
        
        # Use LLM to extract search keywords and search on rupoem.ru
        search_query = extract_search_keywords(raw)
        print(f"[DEBUG] LLM extracted search keywords: '{search_query}' from '{raw}'")
        
        # Search for multiple poems across all sources
        external_poems = fetch_poems_for_user(search_query, limit=10)
        
        if external_poems and len(external_poems) > 0:
            # Store options in temp_memory for user to choose
            temp_memory._poem_selections = getattr(temp_memory, '_poem_selections', {})
            temp_memory._poem_selections[user.telegram_id] = {
                "options": external_poems,
                "query": search_query
            }
            user.stage = "choosing_poem"
            session.add(user)
            session.commit()
            
            # Build message with options showing first 2 lines of each
            lang = user.language_pref
            message_lines = [t("search_found", lang, query=search_query)]
            btn_list = []
            
            for i, ext_poem in enumerate(external_poems[:10], 1):
                preview = _get_first_lines(ext_poem.text, 2)
                message_lines.append(
                    f"\n{i}. 📜 {ext_poem.title} — {ext_poem.author}\n"
                    f"   \"{preview}\""
                )
                btn_list.append(str(i))
            
            message_lines.append(t("search_choose", lang))
            btn_list.append("❌ /cancel" if lang == "en" else "❌ /отмена")
            
            return (
                "\n".join(message_lines),
                btn_list,
                "choosing"
            )
        
        # If external search also found nothing
        lang = user.language_pref
        return (
            t("search_not_found", lang, query=search_query),
            ["/library", "/learn"],
            "not_found"
        )
    
    # === RESUME PREVIOUS POEM (only if user is not asking for something else) ===
    # Check if user is referring to a poem they were learning
    # Only resume if: no active session, has active_poem_id, and intent suggests continuation
    if user.active_poem_id and not active_session and inferred in ("recommend", "review", "start"):
        # Try to restore from DB
        poem = session.get(Poem, user.active_poem_id)
        if poem:
            restored = _restore_progress_to_session(session, user.id, poem, temp_memory)
            if restored:
                progress_info = restored.get_progress()
                last_text = progress_info.get('last_learned_text', '')
                lang = user.language_pref
                return (
                    t("resume_poem", lang,
                      title=poem.title,
                      author=poem.author,
                      part=restored.current_chunk_index + 1,
                      total=len(restored.chunks),
                      last_text=last_text),
                    buttons("resume", lang),
                    "resume"
                )
    
    if inferred == "review" or any(k in incoming for k in ("повтор", "повтори", "провер")):
        return _start_review(session, user, temp_memory)
    
    # Library intents
    if any(k in incoming for k in ("библиотек", "каталог", "автор", "тем", "поиск")):
        user.stage = "library_menu"
        session.add(user)
        session.commit()
        
        library = get_library_service(session)
        result = library.get_main_menu()
        return _make_library_response(result)
    
    # Default: LLM handles everything else
    response = generate_chat_response(text or "")
    return (response, ["/library", "/learn", "/review"], "default")


def _start_poem_learning(session: Session, user: User, temp_memory) -> Tuple[str, List[str], str]:
    """Start a new poem learning session with chunking."""
    # Get recommendation
    poem = _pick_recommendation(session, user, temp_memory)
    
    # Create temporary learning session
    active_session = temp_memory.create_session(
        user_id=user.id,
        poem_id=poem.id,
        poem_title=poem.title,
        poem_author=poem.author,
        full_text=_decode_newlines(poem.text),
        chunk_size=4
    )
    
    # Update user state
    user.active_poem_id = poem.id
    user.stage = "learning_chunk"
    session.add(user)
    session.commit()
    
    # Create or update progress record
    _get_or_create_progress(session, user.id, poem.id, len(active_session.chunks))
    
    # Consume first chunk (advances pointer to 1, so get_current_chunk returns chunk 0)
    first_chunk = active_session.get_next_chunk()
    total_chunks = len(active_session.chunks)
    
    lang = user.language_pref
    return (
        f"📜 {poem.title} — {poem.author}\n\n"
        f"{t('chunk_part', lang, current=1, total=total_chunks)}\n\n"
        f"{first_chunk}\n\n"
        f"{t('memorize_prompt', lang)}",
        buttons("learning", lang),
        "learning"
    )


def _get_next_chunk_response(session: Session, user: User, active_session: ActivePoemSession) -> Tuple[str, List[str], str]:
    """Get response for advancing to next chunk."""
    next_chunk = active_session.get_next_chunk()
    
    if next_chunk is None:
        # All chunks completed
        _save_progress_from_session(session, active_session)
        _temp_memory = get_temp_memory()
        _temp_memory.remove_session(user.id)
        user.active_poem_id = None
        user.stage = "idle"
        session.add(user)
        session.commit()
        
        lang = user.language_pref
        return (
            t("completed_all", lang,
              title=active_session.poem_title,
              author=active_session.poem_author),
            buttons("after_complete", lang),
            "completed"
        )
    
    current_idx = active_session.current_chunk_index
    total = len(active_session.chunks)
    
    lang = user.language_pref
    return (
        f"{t('chunk_part', lang, current=current_idx, total=total)}\n\n"
        f"{next_chunk}\n\n"
        f"{t('ready_next', lang)}",
        buttons("learning", lang),
        "learning"
    )


def _start_review(session: Session, user: User, temp_memory) -> Tuple[str, List[str], str]:
    """Start a review session for due poems or last learned."""
    lang = user.language_pref
    
    # PRIORITY 1: If user has an active poem, review that one
    # But skip if the poem was just completed (status=completed and no due_at yet)
    if user.active_poem_id:
        progress = session.exec(
            select(UserPoemProgress)
            .where(UserPoemProgress.user_id == user.id)
            .where(UserPoemProgress.poem_id == user.active_poem_id)
        ).first()
        # Only review if there's progress and it's not freshly completed
        just_completed = (progress and progress.status in ("completed", "mastered")
                         and progress.due_at and progress.due_at > datetime.now(timezone.utc))
        if not just_completed:
            poem = session.get(Poem, user.active_poem_id)
            if poem:
                user.stage = "reviewing"
                session.add(user)
                session.commit()
                return (
                    t("review_time", lang, title=poem.title, author=poem.author),
                    buttons("review", lang),
                    "review"
                )
    
    # PRIORITY 2: Check for due reviews
    now = datetime.now(timezone.utc)
    due_progress = session.exec(
        select(UserPoemProgress)
        .where(UserPoemProgress.user_id == user.id)
        .where(UserPoemProgress.due_at <= now)
        .where(UserPoemProgress.status != "mastered")
        .order_by(UserPoemProgress.due_at.asc())
    ).first()
    
    if due_progress:
        poem = session.get(Poem, due_progress.poem_id)
        if poem:
            # Restore session
            restored = _restore_progress_to_session(session, user.id, poem, temp_memory)
            user.active_poem_id = poem.id
            user.stage = "reviewing"
            session.add(user)
            session.commit()
            
            return (
                t("review_time", lang, title=poem.title, author=poem.author),
                buttons("review", lang),
                "review"
            )
    
    # If no due items, check for in-progress poems
    in_progress = session.exec(
        select(UserPoemProgress, Poem)
        .join(Poem, UserPoemProgress.poem_id == Poem.id)
        .where(UserPoemProgress.user_id == user.id)
        .where(UserPoemProgress.status == "paused")
        .order_by(UserPoemProgress.last_accessed.desc())
    ).first()
    
    if in_progress:
        progress, poem = in_progress
        restored = _restore_progress_to_session(session, user.id, poem, temp_memory)
        user.active_poem_id = poem.id
        user.stage = "learning_chunk"
        session.add(user)
        session.commit()
        
        last_text = progress.last_session_text[:150] if progress.last_session_text else "..."
        return (
            ("📖 Let's continue!\n\n" if lang == "en" else "📖 Продолжим обучение!\n\n") +
            f"📜 {poem.title} — {poem.author}\n" +
            (f"Stopped at part {restored.current_chunk_index + 1} of {len(restored.chunks)}\n\n" if lang == "en" else
             f"Остановился на части {restored.current_chunk_index + 1} из {len(restored.chunks)}\n\n") +
            (f"Last learned:\n{last_text}...\n\n" if lang == "en" else
             f"Последнее что учил:\n{last_text}...\n\n") +
            ("Continue?" if lang == "en" else "Продолжим?"),
            buttons("resume", lang),
            "learning"
        )
    
    # Nothing to review
    return (
        t("no_review", lang),
        ["/library", "/learn"],
        "help"
    )


def _check_chunk_reproduction(session: Session, user: User, active_session: ActivePoemSession, user_text: str) -> Tuple[str, List[str], str]:
    """Check if user correctly reproduced the current chunk."""
    test_idx = active_session.current_chunk_index - 1
    if test_idx >= 0 and test_idx < len(active_session.chunks):
        current_chunk = active_session.chunks[test_idx]
    else:
        current_chunk = active_session.get_current_chunk()
    if not current_chunk:
        return ("Error", ["/stop"], "error")
    
    lang = user.language_pref
    score = _score_answer(current_chunk, user_text)
    
    if score >= 0.7:
        # Good enough! Mark as learned and move to next chunk
        active_session.mark_current_chunk_learned()
        user.stage = "learning_chunk"
        session.add(user)
        session.commit()
        
        if active_session.current_chunk_index >= len(active_session.chunks):
            # All chunks completed
            _save_progress_from_session(session, active_session)
            _temp_memory = get_temp_memory()
            _temp_memory.remove_session(user.id)
            
            # Award points
            poem = session.get(Poem, user.active_poem_id)
            poem_text = _decode_newlines(poem.text) if poem else ""
            pts = _award_points(session, user, poem_text)
            
            user.active_poem_id = None
            user.stage = "idle"
            session.add(user)
            session.commit()
            
            msg = (
                t("score_great", lang, score=f"{score:.0%}") + "\n\n" +
                t("completed", lang,
                  title=active_session.poem_title,
                  author=active_session.poem_author) +
                t("points_earned", lang, pts=pts, total=user.total_points)
            )
            return (msg, buttons("after_complete", lang), "completed")
        else:
            next_chunk = active_session.get_next_chunk()
            current_idx = active_session.current_chunk_index
            total = len(active_session.chunks)
            
            return (
                t("score_great", lang, score=f"{score:.0%}") + "\n\n" +
                t("chunk_part", lang, current=current_idx, total=total) + "\n\n" +
                f"{next_chunk}\n\n" +
                t("memorize_prompt", lang),
                buttons("learning", lang),
                "learning"
            )
    else:
        return (
            t("score_hint", lang, score=f"{score:.0%}", chunk=current_chunk),
            buttons("testing", lang),
            "testing"
        )


def _check_review_answer(session: Session, user: User, temp_memory, user_answer: str) -> Tuple[str, List[str], str]:
    """Check user's answer during review and update progress."""
    if not user.active_poem_id:
        return (t("error_no_poem", user.language_pref), ["/library"], "error")
    
    poem = session.get(Poem, user.active_poem_id)
    if not poem:
        user.active_poem_id = None
        user.stage = "idle"
        session.add(user)
        session.commit()
        return (t("error_poem_missing", user.language_pref), ["/library"], "error")
    
    # Score the answer
    expected = _decode_newlines(poem.text)
    score = _score_answer(expected, user_answer)
    
    # Update progress
    progress = _get_or_create_progress(session, user.id, poem.id)
    progress.last_score = score
    progress.last_accessed = datetime.now(timezone.utc)
    
    # Update spaced repetition
    _update_spaced_repetition(progress, score)
    session.add(progress)
    
    # Reset user stage
    user.stage = "idle"
    user.active_poem_id = None
    session.add(user)
    session.commit()
    
    lang = user.language_pref
    
    if score >= 0.8:
        # Award points for successful review
        poem_text = _decode_newlines(poem.text)
        pts = _award_points(session, user, poem_text)
        
        pts_msg = ""
        if pts > 0:
            pts_msg = "\n" + t("points_earned", lang, pts=pts, total=user.total_points)
        
        return (
            t("score_great", lang, score=f"{score:.0%}") + "\n\n" +
            f"📜 {poem.title} — {poem.author}\n\n" +
            (f"Next review in {progress.interval_days} days." if lang == "en" else
             f"Следующий повтор через {progress.interval_days} дн.") +
            pts_msg,
            buttons("after_complete", lang),
            "review_complete"
        )
    elif score >= 0.5:
        return (
            f"👍 {f'Not bad! Match: {score:.0%}' if lang == 'en' else f'Неплохо! Совпадение: {score:.0%}'}\n\n"
            f"📜 {poem.title} — {poem.author}\n\n" +
            ("Keep learning! Try again with /review" if lang == "en" else
             "Продолжай учить! Попробуй ещё раз через /review"),
            buttons("after_complete", lang),
            "review_partial"
        )
    else:
        return (
            f"📚 {f'Match: {score:.0%}' if lang == 'en' else f'Совпадение: {score:.0%}'}\n\n" +
            ("Correct text:\n\n" if lang == "en" else "Правильный текст:\n\n") +
            f"{expected[:200]}...\n\n" +
            ("Try to memorize better and review with /review" if lang == "en" else
             "Попробуй выучить лучше и повтори через /review"),
            buttons("after_complete", lang),
            "review_fail"
        )



def _handle_library_action(
    session: Session, 
    user: User, 
    library, 
    action: Dict[str, Any],
    temp_memory
) -> Tuple[str, List[str], str]:
    """Handle library navigation actions."""
    action_type = action.get("action")
    
    if action_type == "show_authors":
        user.stage = "library_authors"
        session.add(user)
        session.commit()
        result = library.get_authors_list()
        return _make_library_response(result)
    
    if action_type == "show_themes":
        user.stage = "library_themes"
        session.add(user)
        session.commit()
        result = library.get_themes_list()
        return _make_library_response(result)
    
    if action_type == "show_popular":
        user.stage = "library_popular"
        session.add(user)
        session.commit()
        result = library.get_popular_poems(user)
        return _make_library_response(result)
    
    if action_type == "show_my_poems":
        user.stage = "library_my_poems"
        session.add(user)
        session.commit()
        result = library.get_user_poems(user)
        return _make_library_response(result)
    
    if action_type == "select_author":
        author = action.get("author", "")
        user.stage = f"library_author_poems:{author}"
        session.add(user)
        session.commit()
        result = library.get_poems_by_author(author)
        return _make_library_response(result)
    
    if action_type == "select_theme":
        theme = action.get("theme", "")
        user.stage = f"library_theme_poems:{theme}"
        session.add(user)
        session.commit()
        result = library.get_poems_by_theme(theme)
        return _make_library_response(result)
    
    if action_type == "select_poem":
        query = action.get("poem_query", "")
        # Extract poem title (remove author if present)
        title = query.split(" — ")[0] if " — " in query else query
        
        poem = _find_poem_by_query(session, title, user.language_pref)
        if poem:
            # Start learning this poem
            return _start_specific_poem_learning(session, user, poem, temp_memory)
        lang = user.language_pref
        return (t("error_poem_missing", lang), ["/library"], "error")
    
    if action_type == "resume_poem":
        query = action.get("poem_query", "")
        title = query.split(" — ")[0] if " — " in query else query
        
        poem = _find_poem_by_query(session, title, user.language_pref)
        if poem:
            # Restore and resume
            restored = _restore_progress_to_session(session, user.id, poem, temp_memory)
            if restored:
                user.active_poem_id = poem.id
                user.stage = "learning_chunk"
                session.add(user)
                session.commit()
                
                lang = user.language_pref
                return (
                    ("📖 Let's continue!\n\n" if lang == "en" else "📖 Продолжаем!\n\n") +
                    f"📜 {poem.title} — {poem.author}\n" +
                    (f"Part {restored.current_chunk_index + 1} of {len(restored.chunks)}\n\n" if lang == "en" else
                     f"Часть {restored.current_chunk_index + 1} из {len(restored.chunks)}\n\n") +
                    ("Ready?" if lang == "en" else "Готов?"),
                    buttons("resume", lang),
                    "learning"
                )
            # No progress found, start fresh
            return _start_specific_poem_learning(session, user, poem, temp_memory)
        lang = user.language_pref
        return (t("error_poem_missing", lang), ["/library"], "error")
    
    if action_type == "back":
        user.stage = "idle"
        session.add(user)
        session.commit()
        lang = user.language_pref
        return (
            ("Main menu:" if lang == "en" else "Главное меню:") + "\n\n" +
            t("menu_library", lang) + "\n" +
            t("menu_learn", lang) + "\n" +
            t("menu_review", lang),
            buttons("main_menu", lang),
            "menu"
        )
    
    if action_type == "search":
        user.stage = "idle"  # Exit library; the user's next message will go to search
        session.add(user)
        session.commit()
        lang = user.language_pref
        return (
            ("🔍 Type what you're looking for:\n\n"
             "• Poem title or first line\n"
             "• Author name\n"
             "• Or describe what kind of poem you want"
             if lang == "en" else
             "🔍 Напиши, что ищешь:\n\n"
             "• Название или первую строку стиха\n"
             "• Имя автора\n"
             "• Или опиши, какой стих хочешь"),
            ["/library", "/learn"],
            "search"
        )
    
    if action_type == "paginate":
        page = action.get("page", 0)
        # Route pagination based on current library stage
        if user.stage == "library_authors":
            result = library.get_authors_list(page)
        elif user.stage.startswith("library_author_poems:"):
            author = user.stage.split(":", 1)[1]
            result = library.get_poems_by_author(author, page)
        elif user.stage == "library_themes":
            # Themes aren't paginated currently, show main
            result = library.get_themes_list()
        elif user.stage.startswith("library_theme_poems:"):
            theme = user.stage.split(":", 1)[1]
            result = library.get_poems_by_theme(theme, page)
        else:
            result = library.get_main_menu()
        return _make_library_response(result)
    
    return _make_library_response(library.get_main_menu())


def _start_specific_poem_learning(
    session: Session, 
    user: User, 
    poem: Poem, 
    temp_memory
) -> Tuple[str, List[str], str]:
    """Start learning a specific poem."""
    # Check for existing progress
    existing_progress = session.exec(
        select(UserPoemProgress)
        .where(UserPoemProgress.user_id == user.id)
        .where(UserPoemProgress.poem_id == poem.id)
    ).first()
    
    if existing_progress and existing_progress.status in ("learning", "paused"):
        # Resume from where they left off
        restored = _restore_progress_to_session(session, user.id, poem, temp_memory)
        if restored:
            user.active_poem_id = poem.id
            user.stage = "learning_chunk"
            session.add(user)
            session.commit()
            
            current_chunk = restored.get_current_chunk()
            if current_chunk:
                lang = user.language_pref
                part_num = max(1, restored.current_chunk_index)
                return (
                    ("📖 Let's continue!\n\n" if lang == "en" else "📖 Продолжаем изучение!\n\n") +
                    f"📜 {poem.title} — {poem.author}\n" +
                    t("chunk_part", lang, current=part_num, total=len(restored.chunks)) + "\n\n" +
                    f"{current_chunk}\n\n" +
                    ("Ready to continue?" if lang == "en" else "Готов продолжить?"),
                    buttons("resume", lang),
                    "learning"
                )
    
    # Start fresh
    return _start_poem_learning_from_poem(session, user, poem, temp_memory)


def _start_poem_learning_from_poem(
    session: Session, 
    user: User, 
    poem: Poem, 
    temp_memory
) -> Tuple[str, List[str], str]:
    """Start learning from a specific poem object."""
    active_session = temp_memory.create_session(
        user_id=user.id,  # user.id is the key in temp_memory
        poem_id=poem.id,
        poem_title=poem.title,
        poem_author=poem.author,
        full_text=_decode_newlines(poem.text),
        chunk_size=4
    )
    
    user.active_poem_id = poem.id
    user.stage = "learning_chunk"
    session.add(user)
    session.commit()
    
    _get_or_create_progress(session, user.id, poem.id, len(active_session.chunks))
    
    first_chunk = active_session.get_next_chunk()
    total_chunks = len(active_session.chunks)
    
    lang = user.language_pref
    return (
        f"📜 {poem.title} — {poem.author}\n\n"
        f"{t('chunk_part', lang, current=1, total=total_chunks)}\n\n"
        f"{first_chunk}\n\n"
        f"{t('memorize_prompt', lang)}",
        buttons("learning", lang),
        "learning"
    )


def log_interaction(session: Session, telegram_id: int, user_text: str, bot_text: str, intent: str) -> None:
    """Log user interaction for analytics."""
    user = get_or_create_user(session, telegram_id)
    session.add(Interaction(user_id=user.id, user_text=user_text, bot_text=bot_text, intent=intent))
    session.commit()


def cleanup_expired_sessions(session: Session) -> int:
    """
    Cleanup expired sessions and persist their progress.
    This should be called periodically (e.g., by a background task).
    """
    temp_memory = get_temp_memory()
    expired = temp_memory.cleanup_expired()
    
    count = 0
    for expired_session in expired:
        _save_progress_from_session(session, expired_session)
        count += 1
    
    return count
