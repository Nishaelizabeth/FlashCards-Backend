import base64
import json
import os

from openai import AuthenticationError, BadRequestError, OpenAI

from services.ai_service import call_ai


IMPROVE_FLASHCARD_PROMPT = """
You help Secondary 1 students improve a flashcard. Correct grammar and improve
clarity while preserving the student's original meaning and language. Keep the
question concise and the answer age-appropriate. Do not add facts that were not
already present.

Return strict JSON only with exactly these keys:
{"question": "...", "answer": "..."}
""".strip()


class StudioAIError(Exception):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def improve_flashcard(question: str, answer: str) -> dict[str, str]:
    payload = call_ai(
        IMPROVE_FLASHCARD_PROMPT,
        json.dumps({"question": question, "answer": answer}, ensure_ascii=False),
    )
    if "error" in payload:
        raise StudioAIError(payload["error"], payload.get("detail", "AI improvement failed."))

    improved_question = str(payload.get("question", "")).strip()
    improved_answer = str(payload.get("answer", "")).strip()
    if not improved_question or not improved_answer:
        raise StudioAIError("invalid_json_response", "AI returned an incomplete suggestion.")
    return {"question": improved_question, "answer": improved_answer}


def generate_illustration(question: str, answer: str) -> bytes:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise StudioAIError("configuration_error", "OPENAI_API_KEY is not configured.")

    prompt = f"""
Create one child-friendly educational cartoon illustration for a Secondary 1
flashcard.

Question: {question}
Answer context: {answer}

Style and safety rules:
- cute, colorful, cheerful 2D educational cartoon
- one clear central idea, simple background, rounded friendly shapes
- no written words, letters, captions, logos, or watermarks
- no photorealism, violence, scary imagery, weapons, or unsafe behavior
- suitable for children and directly helpful for remembering the concept
""".strip()

    try:
        response = OpenAI(api_key=api_key).images.generate(
            model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2"),
            prompt=prompt,
            size="1024x1024",
            quality="low",
        )
    except AuthenticationError as exc:
        raise StudioAIError("authentication_error", "OpenAI rejected OPENAI_API_KEY.") from exc
    except BadRequestError as exc:
        code = getattr(exc, "code", None) or "image_request_failed"
        raise StudioAIError(str(code), "The illustration request was rejected.") from exc
    except Exception as exc:
        raise StudioAIError("image_request_failed", "Illustration generation failed.") from exc

    encoded = response.data[0].b64_json if response.data else None
    if not encoded:
        raise StudioAIError("empty_image_response", "OpenAI returned no illustration.")
    return base64.b64decode(encoded)
