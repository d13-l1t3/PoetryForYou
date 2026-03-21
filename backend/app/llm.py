from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from app.i18n import t as t_i18n


def llm_enabled() -> bool:
    """Check if OpenRouter (or any OpenAI-compatible endpoint) is configured."""
    return bool(os.getenv("OPENROUTER_API_KEY"))


@lru_cache(maxsize=1)
def _client():
    from openai import OpenAI  # type: ignore

    api_key = os.getenv("OPENROUTER_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")

    return OpenAI(base_url=base_url, api_key=api_key)


def _get_llm_response(prompt: str, system_prompt: str = "", max_tokens: int = 100) -> str:
    """Get response from LLM via OpenRouter."""
    if not llm_enabled():
        return ""

    model = os.getenv("LLM_MODEL", "google/gemini-2.0-flash-001")

    try:
        client = _client()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt or "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"LLM error: {e}")
        return ""


def classify_intent(text: str) -> str:
    """
    Returns one of: recommend|review|start|help|chat
    All non-command text goes through LLM classification.
    """
    t = (text or "").strip().lower()
    if not t:
        return "help"

    # Slash commands are handled directly without LLM
    if t.startswith("/"):
        if t.startswith("/start"):
            return "start"
        if t in ("/дальше", "/next", "/continue"):
            return "next"
        if t in ("/стоп", "/stop", "/выйти"):
            return "stop"
        if t in ("/сначала", "/restart"):
            return "restart"
        if t in ("/повторить", "/repeat", "/подсказка", "/hint"):
            return "hint"
        if t in ("/не_помню", "/непомню", "/забыл"):
            return "forgot"
        return "help"

    # Everything else goes through LLM
    if not llm_enabled():
        print(f"[DEBUG] LLM disabled, using fallback classification for: {text!r}")
        # Fallback heuristics only when LLM is disabled
        if any(k in t for k in ("recommend", "new poem", "give me", "хочу стих", "выуч", "стих", "рекоменд", "поэма", "учить", "learn")):
            return "recommend"
        if any(k in t for k in ("review", "revise", "repeat", "повтор", "повтори", "провер")):
            return "review"
        if any(k in t for k in ("привет", "hello", "hi", "здравств", "добрый", "как дела")):
            return "chat"
        return "help"

    try:
        print(f"[DEBUG] Calling LLM classify_intent for: {text!r}")
        prompt = (
            "Classify the user's message into exactly one intent token:\n"
            "- recommend: user wants to learn a new poem (e.g., 'хочу стих', 'выучить', 'новый')\n"
            "- review: user wants to revise / repeat / be tested (e.g., 'повторить', 'проверь меня')\n"
            "- start: user wants to reset / start over\n"
            "- chat: greetings, small talk, questions (e.g., 'привет', 'как дела', 'что ты думаешь')\n"
            "- help: anything else / general questions\n\n"
            f"User message: {text!r}\n\n"
            "Return ONLY the token."
        )

        out = _get_llm_response(
            prompt,
            system_prompt="You output only one token: recommend|review|start|chat|help.",
            max_tokens=5
        ).lower().strip()

        print(f"[DEBUG] LLM classified '{text!r}' as: {out}")

        if out in ("recommend", "review", "start", "chat", "help"):
            return out
        return "help"
    except Exception as e:
        print(f"[DEBUG] LLM classification error: {e}")
        # Fallback to keyword heuristics on LLM error
        if any(k in t for k in ("recommend", "new poem", "give me", "хочу стих", "выуч", "стих", "рекоменд", "поэма", "учить", "learn")):
            return "recommend"
        if any(k in t for k in ("review", "revise", "repeat", "повтор", "повтори", "провер")):
            return "review"
        if any(k in t for k in ("привет", "hello", "hi", "здравств", "добрый", "как дела")):
            return "chat"
        return "help"


def generate_chat_response(text: str, lang: str = "ru") -> str:
    """Generate a conversational response using LLM."""
    if not llm_enabled():
        return t_i18n("fallback_chat", lang)

    try:
        if lang == "en":
            prompt = (
                "You are a friendly poetry learning assistant. "
                "Reply to the user's message briefly and warmly. "
                "You can ask if they want to learn poems or something else.\n\n"
                f"Message: {text}\n\n"
                "Reply:"
            )
            system = "You are a friendly assistant. Reply briefly (1-2 sentences) and politely. Answer in English."
        else:
            prompt = (
                "Ты - дружелюбный помощник для изучения стихов. "
                "Ответь на сообщение пользователя кратко и дружелюбно. "
                "Можешь спросить, хочет ли он учить стихи или что-то еще.\n\n"
                f"Сообщение: {text}\n\n"
                "Ответ:"
            )
            system = "Ты - дружелюбный помощник. Отвечай кратко (1-2 предложения) и вежливо."

        response = _get_llm_response(prompt, system_prompt=system, max_tokens=100)

        if not response:
            return t_i18n("fallback_chat", lang)

        return response
    except Exception as e:
        print(f"[DEBUG] Chat response error: {e}")
        return t_i18n("fallback_chat", lang)


def generate_poem_explanation(poem_title: str, poem_author: str, poem_text: str, language: str = "ru") -> str:
    """Generate explanation/analysis of a poem using LLM."""
    if not llm_enabled():
        return ""

    try:
        if language == "ru":
            prompt = (
                f"Проанализируй это стихотворение кратко (2-3 предложения):\n\n"
                f"Название: {poem_title}\n"
                f"Автор: {poem_author}\n"
                f"Текст:\n{poem_text[:500]}\n\n"
                f"Опиши главную мысль и настроение стиха."
            )
            system = "Ты - литературный критик. Отвечай кратко и понятно."
        else:
            prompt = (
                f"Analyze this poem briefly (2-3 sentences):\n\n"
                f"Title: {poem_title}\n"
                f"Author: {poem_author}\n"
                f"Text:\n{poem_text[:500]}\n\n"
                f"Describe the main theme and mood."
            )
            system = "You are a literary critic. Be concise and clear."

        return _get_llm_response(prompt, system, max_tokens=200)
    except Exception as e:
        print(f"Error generating explanation: {e}")
        return ""


def extract_search_keywords(query: str) -> str:
    """Extract search keywords from user query using LLM for better search."""
    if not llm_enabled():
        # Fallback: return original query without common phrases
        q = query.lower()
        for phrase in ["я хочу выучить", "стих", "поэма", "автор", "про", "который", "найди", "поищи"]:
            q = q.replace(phrase, "")
        return q.strip(' "«»')

    try:
        prompt = (
            f"Пользователь ищет стихотворение. Извлеки из запроса ключевые слова для поиска.\n\n"
            f"Запрос: \"{query}\"\n\n"
            f"Верни ТОЛЬКО ключевые слова для поиска (название, автора, или уникальные слова из стиха). "
            f"Не добавляй пояснений, только строку поиска."
        )

        result = _get_llm_response(
            prompt,
            "Ты помогаешь найти стихи. Верни только строку для поиска, без кавычек и пояснений.",
            max_tokens=50
        )

        # Clean up the result
        result = result.strip(' "«»„"\'')
        return result if result else query
    except Exception as e:
        print(f"Error extracting keywords: {e}")
        return query
