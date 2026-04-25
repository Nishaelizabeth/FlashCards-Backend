"""Public exports for the services package."""

from .ai_service import (
	call_ai,
	generate_chinese_composition,
	generate_english_composition,
	generate_flashcards,
)
from .prompts import (
	CHINESE_SYSTEM_PROMPT,
	ENGLISH_SYSTEM_PROMPT,
	FLASHCARD_SYSTEM_PROMPT,
)

__all__ = [
	"call_ai",
	"generate_flashcards",
	"generate_english_composition",
	"generate_chinese_composition",
	"ENGLISH_SYSTEM_PROMPT",
	"CHINESE_SYSTEM_PROMPT",
	"FLASHCARD_SYSTEM_PROMPT",
]
