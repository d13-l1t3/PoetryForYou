from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import Session, select

from app.db import Interaction, LearningItem, Poem, User
from app.llm import classify_intent


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _decode_newlines(s: str) -> str:
    return s.replace("\\n", "\n")


def _find_poem_by_query(session: Session, query: str, lang_pref: str) -> Poem | None:
    q = _normalize(query)
    if len(q) < 4:
        return None

    poem_query = select(Poem)
    if lang_pref in ("en", "ru"):
        poem_query = poem_query.where(Poem.language == lang_pref)

    poems = session.exec(poem_query).all()
    best_score = 0
    best_poem: Poem | None = None

    tokens = q.split()
    for p in poems:
        hay = _normalize(f"{p.title} {p.author} {_decode_newlines(p.text)}")
        score = sum(1 for t in tokens if t in hay)
        if score > best_score:
            best_score = score
            best_poem = p

    return best_poem if best_score > 0 else None


def get_or_create_user(session: Session, telegram_id: int) -> User:
    user = session.exec(select(User).where(User.telegram_id == telegram_id)).first()
    if user is None:
        user = User(telegram_id=telegram_id)
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def _set_stage(session: Session, user: User, stage: str) -> None:
    user.stage = stage
    session.add(user)
    session.commit()


def _pick_recommendation(session: Session, user: User) -> Poem:
    # Prioritize due reviews
    now = datetime.utcnow()
    due_item = session.exec(
        select(LearningItem)
        .where(LearningItem.user_id == user.id)
        .where(LearningItem.due_at <= now)
        .order_by(LearningItem.due_at.asc())
    ).first()
    if due_item is not None:
        poem = session.get(Poem, due_item.poem_id)
        if poem is not None:
            return poem

    # Otherwise pick a new poem that matches language preference and not yet learned
    learned_poem_ids = session.exec(
        select(LearningItem.poem_id).where(LearningItem.user_id == user.id)
    ).all()
    learned_poem_ids_set = set(learned_poem_ids)

    poem_query = select(Poem)
    if user.language_pref in ("en", "ru"):
        poem_query = poem_query.where(Poem.language == user.language_pref)

    candidates = [
        p for p in session.exec(poem_query).all() if (p.id or -1) not in learned_poem_ids_set
    ]
    if not candidates:
        # fallback: anything in preferred language
        candidates = session.exec(poem_query).all()

    return random.choice(candidates)


def _ensure_learning_item(session: Session, user: User, poem: Poem) -> LearningItem:
    item = session.exec(
        select(LearningItem)
        .where(LearningItem.user_id == user.id)
        .where(LearningItem.poem_id == poem.id)
    ).first()
    if item is None:
        item = LearningItem(user_id=user.id, poem_id=poem.id, status="learning")
        session.add(item)
        session.commit()
        session.refresh(item)
    return item


def _make_cloze(text: str, every_n: int = 6) -> str:
    words = text.split()
    if len(words) < 12:
        every_n = 4
    out = []
    for i, w in enumerate(words):
        if i != 0 and i % every_n == 0 and len(w) > 2:
            out.append("____")
        else:
            out.append(w)
    return " ".join(out)


def _score_answer(expected: str, answer: str) -> float:
    # MVP: token overlap ratio (simple, language-agnostic, explainable)
    exp = set(_normalize(expected).split())
    ans = set(_normalize(answer).split())
    if not exp:
        return 0.0
    return len(exp & ans) / len(exp)


def _update_spaced_repetition(item: LearningItem, score: float) -> None:
    # Tiny SM-2-inspired update
    if score >= 0.75:
        item.reps += 1
        item.ease = min(2.7, item.ease + 0.05)
        item.interval_days = 1 if item.interval_days == 0 else int(item.interval_days * item.ease)
        if item.interval_days < 1:
            item.interval_days = 1
        item.status = "mastered" if item.reps >= 4 else "learning"
    else:
        item.ease = max(1.3, item.ease - 0.1)
        item.interval_days = 1
        item.status = "learning"

    item.last_score = score
    item.due_at = datetime.utcnow() + timedelta(days=item.interval_days)


def handle_message(session: Session, telegram_id: int, text: Optional[str]) -> tuple[str, list[str], str]:
    user = get_or_create_user(session, telegram_id)
    raw = (text or "").strip()
    incoming = _normalize(text or "")

    # Slash commands – highest priority, work in any stage
    if raw.startswith("/"):
        cmd = raw.split()[0].lower()

        if cmd == "/start":
            _set_stage(session, user, "onboarding_language")
            return (
                "Hi! I help you memorize classic poems through short daily practice.\n\n"
                "Choose your language preference: en / ru / mix",
                ["en", "ru", "mix"],
                "onboarding",
            )

        if cmd in ("/lang_en", "/lang_ru", "/lang_mix"):
            lang_map = {"/lang_en": "en", "/lang_ru": "ru", "/lang_mix": "mix"}
            user.language_pref = lang_map[cmd]
            user.stage = "idle"
            session.add(user)
            session.commit()
            return (
                f"Language set to {user.language_pref}. Say “/recommend” or “/review”.",
                ["/recommend", "/review"],
                "settings",
            )

        if cmd in ("/beginner", "/intermediate", "/advanced"):
            level = cmd.removeprefix("/")
            user.level = level
            user.stage = "idle"
            session.add(user)
            session.commit()
            return (
                f"Level set to {user.level}. Say “/recommend” or “/review”.",
                ["/recommend", "/review"],
                "settings",
            )

        if cmd in ("/recommend", "/review", "/cloze", "/help"):
            # Re-route to the same logic as text commands but with leading slash stripped
            incoming = cmd.removeprefix("/")
            raw = incoming
            # and fall through to the rest of the handler

    if user.stage == "onboarding_language":
        if incoming in ("en", "ru", "mix"):
            user.language_pref = incoming
            user.stage = "onboarding_level"
            session.add(user)
            session.commit()
            return (
                "Nice. Pick your level: beginner / intermediate / advanced",
                ["beginner", "intermediate", "advanced"],
                "onboarding",
            )
        return ("Please reply with: en / ru / mix", ["en", "ru", "mix"], "onboarding")

    if user.stage == "onboarding_level":
        if incoming in ("beginner", "intermediate", "advanced"):
            user.level = incoming
            user.stage = "idle"
            session.add(user)
            session.commit()
            return (
                "Great. Say “recommend” for a new poem or “review” to revise what’s due.",
                ["recommend", "review"],
                "onboarding",
            )
        return (
            "Please reply with: beginner / intermediate / advanced",
            ["beginner", "intermediate", "advanced"],
            "onboarding",
        )

    # Memorization check flow
    if user.stage == "awaiting_check" and user.active_poem_id is not None:
        # Treat control words as commands even without slash
        if incoming in ("review", "recommend", "cloze", "start", "/start"):
            # Cancel current check and re-handle as a fresh command
            user.active_poem_id = None
            user.stage = "idle"
            session.add(user)
            session.commit()
            # Re-enter handler as idle
            return handle_message(session, telegram_id, incoming if incoming != "/start" else "/start")

        # If user asks to learn a specific poem, switch to it instead of scoring 0%
        if any(k in incoming for k in ("помоги", "выуч", "learn", "help me", "стих", "poem")):
            poem = _find_poem_by_query(session, raw, user.language_pref)
            if poem is not None:
                _ensure_learning_item(session, user, poem)
                user.active_poem_id = poem.id
                user.stage = "awaiting_check"
                session.add(user)
                session.commit()
                return (
                    f"Sure — let’s learn this one.\n\n📜 {poem.title} — {poem.author}\n\n{_decode_newlines(poem.text)}\n\n"
                    "Now a quick check: reply with the full poem (or as much as you can). "
                    "If you want an easier check, reply “cloze”.",
                    ["cloze", "review", "recommend"],
                    "recommendation",
                )

        poem = session.get(Poem, user.active_poem_id)
        if poem is None:
            user.active_poem_id = None
            user.stage = "idle"
            session.add(user)
            session.commit()
            return ("Something went wrong; try “recommend”.", ["recommend"], "error")

        # If user sends a control word while we wait for an answer, don't treat it as an answer.
        # They can always use slash-commands to change mode explicitly.
        if raw.startswith("/"):
            # Cancel current check and re-handle as a fresh command.
            user.active_poem_id = None
            user.stage = "idle"
            session.add(user)
            session.commit()
            # Re-enter handler with the same text but idle stage.
            return handle_message(session, telegram_id, text)

        score = _score_answer(_decode_newlines(poem.text), text or "")
        item = _ensure_learning_item(session, user, poem)
        _update_spaced_repetition(item, score)
        session.add(item)

        user.stage = "idle"
        user.active_poem_id = None
        session.add(user)
        session.commit()

        if score >= 0.75:
            return (
                f"Good job — score {score:.0%}. Next review is scheduled in {item.interval_days} day(s).\n"
                "Want another recommendation?",
                ["recommend", "review"],
                "check_result",
            )
        return (
            f"Not bad — score {score:.0%}. I’ll schedule a quick review tomorrow.\n\n"
            "Tip: try reading it once more and remember 2 key images.\n"
            "Want a different poem or try again?",
            ["recommend", "try again", "review"],
            "check_result",
        )

    # From here on, we only allow LLM / free-form intents in the idle stage
    if user.stage != "idle":
        return (
            "Finish this step first or use slash commands like /start, /recommend, /review.\n"
            "For example: /recommend",
            ["/recommend", "/review", "/start"],
            "help",
        )

    # Idle intents
    inferred = classify_intent(text or "")

    if inferred == "start":
        _set_stage(session, user, "onboarding_language")
        return (
            "Reset done. Choose your language preference: en / ru / mix",
            ["en", "ru", "mix"],
            "onboarding",
        )

    if incoming in ("recommend", "new", "give me a poem") or inferred == "recommend":
        poem = _pick_recommendation(session, user)
        _ensure_learning_item(session, user, poem)

        user.active_poem_id = poem.id
        user.stage = "awaiting_check"
        session.add(user)
        session.commit()

        cloze = _make_cloze(_decode_newlines(poem.text))
        return (
            f"📜 {poem.title} — {poem.author}\n\n{_decode_newlines(poem.text)}\n\n"
            "Now a quick check: reply with the full poem (or as much as you can). "
            "If you want an easier check, reply “cloze”.",
            ["cloze", "review"],
            "recommendation",
        )

    if incoming == "cloze":
        if user.active_poem_id is None:
            return ("Ask for a poem first: “recommend”.", ["recommend"], "help")
        poem = session.get(Poem, user.active_poem_id)
        if poem is None:
            return ("Ask for a poem first: “recommend”.", ["recommend"], "help")
        cloze = _make_cloze(_decode_newlines(poem.text))
        return (
            "Fill the blanks by replying with the missing words (you can include the whole line):\n\n"
            f"{cloze}",
            [],
            "cloze",
        )

    if incoming == "review" or inferred == "review":
        # Force recommendation logic to pick due first
        poem = _pick_recommendation(session, user)
        user.active_poem_id = poem.id
        user.stage = "awaiting_check"
        session.add(user)
        session.commit()

        return (
            f"Review time.\n\n📜 {poem.title} — {poem.author}\n\n"
            "Reply with the poem from memory (as much as you can).",
            ["cloze", "recommend"],
            "review",
        )

    # Idle: user asks to learn a specific poem / author
    if any(k in incoming for k in ("помоги", "выуч", "learn", "help me", "стих", "poem")):
        poem = _find_poem_by_query(session, raw, user.language_pref)
        if poem is not None:
            _ensure_learning_item(session, user, poem)
            user.active_poem_id = poem.id
            user.stage = "awaiting_check"
            session.add(user)
            session.commit()
            return (
                f"Sure — let’s learn this one.\n\n📜 {poem.title} — {poem.author}\n\n{_decode_newlines(poem.text)}\n\n"
                "Now a quick check: reply with the full poem (or as much as you can). "
                "If you want an easier check, reply “cloze”.",
                ["cloze", "review", "recommend"],
                "recommendation",
            )

    return (
        "Say “recommend” to get a poem, or “review” to revise. You can always “/start” to reset.",
        ["recommend", "review", "/start"],
        "help",
    )


def log_interaction(session: Session, telegram_id: int, user_text: str, bot_text: str, intent: str) -> None:
    user = get_or_create_user(session, telegram_id)
    session.add(Interaction(user_id=user.id, user_text=user_text, bot_text=bot_text, intent=intent))
    session.commit()

