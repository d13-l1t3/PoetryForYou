from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class IncomingMessage(BaseModel):
    telegram_id: int
    text: Optional[str] = Field(default=None, max_length=2000)
    # Phase B uses a separate /voice endpoint (multipart upload).


class BotReply(BaseModel):
    text: str
    # Simple UI hints for Telegram bot (optional)
    suggested_replies: list[str] = Field(default_factory=list)


class MessageResponse(BaseModel):
    reply: BotReply
    intent: str
    stage: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

