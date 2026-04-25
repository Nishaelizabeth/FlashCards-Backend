"""Reusable AI service layer for flashcards and writing guidance."""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from .prompts import (
    CHINESE_SYSTEM_PROMPT,
    ENGLISH_SYSTEM_PROMPT,
    FLASHCARD_SYSTEM_PROMPT,
    TRANSLATE_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


def _resolve_base_dir() -> Path:
    """Resolve BASE_DIR from Django settings, with a local fallback."""
    try:
        from django.conf import settings

        configured_base_dir = getattr(settings, "BASE_DIR", None)
        if configured_base_dir:
            return Path(configured_base_dir)
    except Exception:
        pass

    return Path(__file__).resolve().parents[1]


BASE_DIR = _resolve_base_dir()
load_dotenv(BASE_DIR / ".env")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _get_openai_client() -> OpenAI:
    """Build an OpenAI client from environment configuration."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    return OpenAI(api_key=api_key)


def _coerce_content_to_text(content: Any) -> str:
    """Normalize OpenAI message content into plain text."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict):
                text_part = part.get("text", "")
            else:
                text_part = getattr(part, "text", "")
            if text_part:
                parts.append(str(text_part))
        return "".join(parts)

    return str(content or "")


def _extract_json_candidate(raw_text: str) -> str | None:
    """Extract the most likely JSON snippet from a raw AI response."""
    text = raw_text.strip()
    if not text:
        return None

    code_fence_match = re.search(
        r"```(?:json)?\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL
    )
    if code_fence_match:
        text = code_fence_match.group(1).strip()

    if text.startswith("{") or text.startswith("["):
        return text

    first_object = text.find("{")
    first_array = text.find("[")
    starts = [index for index in (first_object, first_array) if index != -1]
    if not starts:
        return None

    start = min(starts)
    opening = text[start]
    closing = "}" if opening == "{" else "]"
    end = text.rfind(closing)
    if end == -1 or end <= start:
        return None

    return text[start : end + 1]


def _parse_json_response(raw_text: str) -> Any | None:
    """Parse JSON safely from raw model output."""
    candidate = _extract_json_candidate(raw_text)
    if not candidate:
        return None

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        logger.exception("Failed to parse model response as JSON.")
        return None


def _as_string_list(value: Any) -> list[str]:
    """Return a cleaned list of non-empty string items."""
    if not isinstance(value, list):
        return []

    cleaned: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            cleaned.append(text)
    return cleaned


def call_ai(system_prompt: str, user_input: str) -> dict[str, Any]:
    """Call OpenAI with system and user messages and return parsed JSON."""
    try:
        client = _get_openai_client()
    except RuntimeError as exc:
        logger.error("AI service configuration error: %s", exc)
        return {"error": "configuration_error", "detail": str(exc)}

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
        )
    except Exception as exc:
        logger.exception("OpenAI request failed.")
        return {"error": "request_failed", "detail": str(exc)}

    message_content = response.choices[0].message.content if response.choices else ""
    raw_response = _coerce_content_to_text(message_content)
    parsed_json = _parse_json_response(raw_response)

    if parsed_json is None:
        logger.error("AI JSON parse failed. Raw response: %s", raw_response)
        return {"error": "invalid_json_response", "raw_response": raw_response}

    if isinstance(parsed_json, list):
        return {"items": parsed_json}

    if isinstance(parsed_json, dict):
        return parsed_json

    return {"value": parsed_json}


def _normalize_flashcards(items: Any) -> list[dict[str, str]]:
    """Normalize model output to a clean flashcard list."""
    if isinstance(items, dict):
        items = [items]

    if not isinstance(items, list):
        return []

    normalized_cards: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        card = {
            "question": str(item.get("question", "")).strip(),
            "answer": str(item.get("answer", "")).strip(),
            "highlight": str(item.get("highlight", "")).strip(),
            "image_hint": str(item.get("image_hint", "")).strip(),
        }

        if card["question"] and card["answer"]:
            normalized_cards.append(card)

    return normalized_cards


def _normalize_english_guidance(payload: dict[str, Any]) -> dict[str, Any]:
    """Enforce stable English guidance schema for callers."""
    return {
        "intro": str(payload.get("intro", "")).strip(),
        "body": _as_string_list(payload.get("body")),
        "conclusion": str(payload.get("conclusion", "")).strip(),
        "vocabulary": _as_string_list(payload.get("vocabulary")),
        "outline": _as_string_list(payload.get("outline")),
        "tips": _as_string_list(payload.get("tips")),
    }


def _normalize_chinese_guidance(payload: dict[str, Any]) -> dict[str, Any]:
    """Enforce stable Chinese guidance schema for callers."""
    return {
        "开头": str(payload.get("开头", "")).strip(),
        "内容": _as_string_list(payload.get("内容")),
        "结尾": str(payload.get("结尾", "")).strip(),
        "好词好句": _as_string_list(payload.get("好词好句")),
        "写作提纲": _as_string_list(payload.get("写作提纲")),
        "写作建议": _as_string_list(payload.get("写作建议")),
    }


def generate_flashcards(text: str) -> list[dict[str, str]]:
    """Generate student-friendly flashcards from raw OCR text."""
    if not text or not text.strip():
        return []

    payload = call_ai(FLASHCARD_SYSTEM_PROMPT, text)
    if "error" in payload:
        logger.error("Flashcard generation failed: %s", payload)
        return []

    card_items = payload.get("items", payload.get("flashcards", []))
    return _normalize_flashcards(card_items)


def generate_english_composition(topic: str, essay_type: str = "") -> dict[str, Any]:
    """Generate structured English composition guidance for Sec 1."""
    if not topic or not topic.strip():
        return _normalize_english_guidance({})

    user_input = f"Topic: {topic}"
    if essay_type:
        user_input += f"\nEssay Type: {essay_type}"

    payload = call_ai(ENGLISH_SYSTEM_PROMPT, user_input)
    if "error" in payload:
        return payload

    return _normalize_english_guidance(payload)


def generate_chinese_composition(topic: str) -> dict[str, Any]:
    """Generate structured Chinese composition guidance for Sec 1."""
    if not topic or not topic.strip():
        return _normalize_chinese_guidance({})

    payload = call_ai(CHINESE_SYSTEM_PROMPT, topic)
    if "error" in payload:
        return payload

    return _normalize_chinese_guidance(payload)


def translate_text(text: str) -> dict[str, Any]:
    """Translate Chinese text into simple English."""
    if not text or not text.strip():
        return {"translated": ""}

    payload = call_ai(TRANSLATE_SYSTEM_PROMPT, text)
    if "error" in payload:
        return payload

    return {"translated": str(payload.get("translated", "")).strip()}
