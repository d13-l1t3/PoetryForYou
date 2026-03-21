from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, Session, create_engine

from app.config import settings


engine = create_engine(settings.database_url, echo=False)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    language_pref: str = "mix"  # en|ru|mix
    level: str = "intermediate"  # beginner|intermediate|advanced
    stage: str = "onboarding_language"  # onboarding_language|onboarding_level|idle|awaiting_check
    active_poem_id: Optional[int] = Field(default=None, index=True)

    # Gamification
    display_name: str = ""  # Name shown in leaderboard
    total_points: int = 0  # Points accumulated from learning poems


class Interaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user_text: str
    bot_text: str
    intent: str


class Poem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    language: str = Field(index=True)  # en|ru
    title: str
    author: str
    text: str
    tags: str = ""  # comma-separated for MVP
    difficulty: int = 2  # 1..5


class LearningItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    poem_id: int = Field(index=True)

    status: str = "new"  # new|learning|mastered
    due_at: datetime = Field(default_factory=datetime.utcnow)

    reps: int = 0
    ease: float = 2.3
    interval_days: int = 0
    last_score: Optional[float] = None


class UserPoemProgress(SQLModel, table=True):
    """Tracks user's learning progress for each poem with chunk-based learning."""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    poem_id: int = Field(index=True)

    # Learning state
    status: str = "learning"  # learning|paused|completed|mastered
    last_chunk_index: int = 0  # Last chunk the user was learning
    total_chunks: int = 0
    learned_chunks: str = ""  # Comma-separated indices of learned chunks
    last_session_text: str = ""  # Last chunk text user saw (for context)

    # Timestamps
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Spaced repetition data
    due_at: datetime = Field(default_factory=datetime.utcnow)
    reps: int = 0
    ease: float = 2.3
    interval_days: int = 0
    last_score: Optional[float] = None


class UserPreferences(SQLModel, table=True):
    """User preferences for personalized recommendations."""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, unique=True)

    # Preferred poets (comma-separated)
    favorite_poets: str = ""

    # Preferred themes/tags (comma-separated)
    preferred_themes: str = ""

    # Difficulty preference
    preferred_difficulty: int = 2  # 1-5
    difficulty_range: str = "1,3"  # min,max difficulty they're comfortable with

    # Learning pace
    chunks_per_session: int = 3  # How many chunks to show per session

    updated_at: datetime = Field(default_factory=datetime.utcnow)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)

