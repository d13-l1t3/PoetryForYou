from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class IncomingMessage(BaseModel):
    telegram_id: int
    text: Optional[str] = None
    # Phase B uses a separate /voice endpoint (multipart upload).


class BotReply(BaseModel):
    text: str
    # Simple UI hints for Telegram bot (optional)
    suggested_replies: list[str] = Field(default_factory=list)


class MessageResponse(BaseModel):
    reply: BotReply
    intent: str
    stage: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

