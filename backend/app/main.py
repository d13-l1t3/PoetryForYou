from __future__ import annotations

import os
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from sqlmodel import select

from app.db import User, create_db_and_tables, get_session
from app.schemas import MessageResponse, IncomingMessage
from app.seed import seed_poems_if_empty
from app.service_enhanced import handle_message, log_interaction, cleanup_expired_sessions
from app.stt import transcribe_audio


app = FastAPI(title="Poetry Conversational Recommender")


@app.on_event("startup")
def _startup() -> None:
    create_db_and_tables()
    seed_poems_if_empty()


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/message", response_model=MessageResponse)
def message(payload: IncomingMessage) -> MessageResponse:
    if payload.text is None:
        raise HTTPException(status_code=400, detail="text is required for MVP (Phase A)")

    with get_session() as session:
        reply_text, suggested, intent = handle_message(session, payload.telegram_id, payload.text)
        log_interaction(session, payload.telegram_id, payload.text, reply_text, intent)

        # Re-read user stage for the response
        user = session.exec(select(User).where(User.telegram_id == payload.telegram_id)).first()
        stage = user.stage if user else "unknown"

    return MessageResponse(
        reply={"text": reply_text, "suggested_replies": suggested},
        intent=intent,
        stage=stage,
    )


@app.post("/voice", response_model=MessageResponse)
async def voice(
    telegram_id: int = Form(...),
    audio: UploadFile = File(...),
) -> MessageResponse:
    model_name = os.getenv("WHISPER_MODEL", "small")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    # Look up user's language preference for better STT accuracy
    with get_session() as session:
        user = session.exec(select(User).where(User.telegram_id == telegram_id)).first()
        lang_hint = user.language_pref if user and user.language_pref in ("ru", "en") else None

    try:
        text = transcribe_audio(tmp_path, model_name=model_name, language=lang_hint)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    with get_session() as session:
        reply_text, suggested, intent = handle_message(session, telegram_id, text)
        log_interaction(session, telegram_id, f"[voice]{text}", reply_text, intent)

        user = session.exec(select(User).where(User.telegram_id == telegram_id)).first()
        stage = user.stage if user else "unknown"

    return MessageResponse(
        reply={"text": reply_text, "suggested_replies": suggested},
        intent=intent,
        stage=stage,
    )


@app.post("/cleanup")
def cleanup_sessions() -> dict:
    """Cleanup expired temporary sessions and persist progress."""
    with get_session() as session:
        count = cleanup_expired_sessions(session)
    return {"cleaned_up": count}

