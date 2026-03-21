import os

import httpx
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters


BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000").rstrip("/")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def call_backend(telegram_id: int, text: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{BACKEND_BASE_URL}/message",
            json={"telegram_id": telegram_id, "text": text},
        )
        resp.raise_for_status()
        return resp.json()

async def call_backend_voice(telegram_id: int, filename: str, audio_bytes: bytes) -> dict:
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{BACKEND_BASE_URL}/voice",
            data={"telegram_id": str(telegram_id)},
            files={"audio": (filename, audio_bytes)},
        )
        resp.raise_for_status()
        return resp.json()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or update.message is None:
        return
    data = await call_backend(user.id, "/start")
    await send_reply(update, context, data)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or update.message is None:
        return
    help_text = (
        "📖 *Как пользоваться ботом:*\n\n"
        "🎯 /learn — выучить новый стих\n"
        "📚 /library — открыть библиотеку\n"
        "🔄 /review — повторить выученное\n"
        "📊 /progress — мой прогресс\n"
        "🔄 /start — начать заново\n\n"
        "💡 *Во время обучения:*\n"
        "• /дальше — следующая часть\n"
        "• /повторить — показать часть снова\n"
        "• /стоп — остановить обучение\n\n"
        "🎤 Можешь отправлять голосовые сообщения!"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or update.message is None or update.message.text is None:
        return
    data = await call_backend(user.id, update.message.text)
    await send_reply(update, context, data)

async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or update.message is None or update.message.voice is None:
        return

    voice = update.message.voice
    tg_file = await context.bot.get_file(voice.file_id)
    audio_bytes = await tg_file.download_as_bytearray()
    data = await call_backend_voice(user.id, "voice.ogg", bytes(audio_bytes))
    await send_reply(update, context, data)


def _build_keyboard(suggested: list[str]) -> ReplyKeyboardMarkup:
    """Build a clean keyboard layout from suggested replies."""
    keyboard = []
    row = []

    for btn in suggested:
        # Emoji buttons or long text get their own row
        if any(emoji in btn for emoji in ['📚', '📝', '🎭', '⭐', '📖', '👤', '📜', '⬅️', '🔄', '🏆', '✅', '⏸️', '🔍', '🎯', '📊']):
            if row:
                keyboard.append(row)
                row = []
            keyboard.append([btn])
        else:
            row.append(btn)
            if len(row) >= 2:
                keyboard.append(row)
                row = []

    if row:
        keyboard.append(row)

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Напиши или скажи ответ...",
    )


async def send_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict) -> None:
    if update.message is None:
        return

    reply = data.get("reply", {}) or {}
    text = reply.get("text", "")
    suggested = reply.get("suggested_replies", []) or []

    if not text:
        text = "🤔 Что-то пошло не так. Попробуй /help"

    if suggested:
        kb = _build_keyboard(suggested)
        await update.message.reply_text(text, reply_markup=kb)
    else:
        await update.message.reply_text(text)


async def on_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all slash commands."""
    user = update.effective_user
    if user is None or update.message is None or update.message.text is None:
        return
    data = await call_backend(user.id, update.message.text)
    await send_reply(update, context, data)


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    # Handle all other commands
    app.add_handler(MessageHandler(filters.COMMAND, on_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_handler(MessageHandler(filters.VOICE, on_voice))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
