import logging
import re
from pathlib import Path
from typing import Any

import pytesseract
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import status
from rest_framework.decorators import (
	api_view,
	authentication_classes,
	parser_classes,
	permission_classes,
)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from services.ai_service import generate_flashcards as generate_ai_flashcards

logger = logging.getLogger(__name__)

import pytesseract
import os

if os.name == "nt":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
else:
    pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
MIN_OCR_DIMENSION = 1200


def _validate_uploaded_image(uploaded_file) -> str | None:
	"""Validate uploaded file type and size. Returns error message when invalid."""
	filename = getattr(uploaded_file, "name", "") or ""
	content_type = (getattr(uploaded_file, "content_type", "") or "").lower()
	file_size = int(getattr(uploaded_file, "size", 0) or 0)
	extension = Path(filename).suffix.lower()

	if file_size <= 0:
		return "Uploaded image is empty."

	if extension not in ALLOWED_IMAGE_EXTENSIONS:
		return "Invalid file type. Only JPG, JPEG, and PNG are allowed."

	if content_type and content_type not in ALLOWED_IMAGE_MIME_TYPES:
		return "Invalid file type. Only JPG, JPEG, and PNG are allowed."

	if file_size > MAX_IMAGE_SIZE_BYTES:
		return "File too large. Maximum size is 5MB."

	return None


def _extract_text_from_image(uploaded_file) -> str:
	"""Extract text from an uploaded image with basic OCR preprocessing."""
	uploaded_file.seek(0)
	with Image.open(uploaded_file) as image:
		processed_image = ImageOps.grayscale(image)
		processed_image = ImageOps.autocontrast(processed_image)

		min_dimension = min(processed_image.size)
		if min_dimension < MIN_OCR_DIMENSION:
			scale_ratio = MIN_OCR_DIMENSION / float(min_dimension)
			new_size = (
				int(processed_image.width * scale_ratio),
				int(processed_image.height * scale_ratio),
			)
			processed_image = processed_image.resize(new_size, Image.Resampling.LANCZOS)

		return pytesseract.image_to_string(processed_image, config="--oem 3 --psm 6")


def _clean_ocr_text(raw_text: str) -> str:
	"""Normalize OCR output by reducing whitespace and noise symbols."""
	if not raw_text:
		return ""

	text = raw_text.replace("\r", "\n")
	text = re.sub(r"[\x00-\x08\x0B-\x1F\x7F]", " ", text)
	text = text.replace("\n", " ")
	text = re.sub(r"[|`~^_=]{2,}", " ", text)
	text = re.sub(r"\s+", " ", text)
	return text.strip()


def _validate_flashcards_payload(payload: Any) -> tuple[bool, list[dict[str, str]], str]:
	"""Validate AI flashcard payload format and required keys."""
	if not isinstance(payload, list):
		return False, [], "AI response format is invalid."

	if not payload:
		return False, [], "AI returned no flashcards."

	validated_cards: list[dict[str, str]] = []
	for card in payload:
		if not isinstance(card, dict):
			return False, [], "AI response format is invalid."

		question = str(card.get("question", "")).strip()
		answer = str(card.get("answer", "")).strip()
		if not question or not answer:
			return False, [], "AI response is missing required flashcard fields."

		validated_cards.append(
			{
				"question": question,
				"answer": answer,
				"highlight": str(card.get("highlight", "")).strip(),
				"image_hint": str(card.get("image_hint", "")).strip(),
			}
		)

	return True, validated_cards, ""


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def generate_flashcards(request):
	"""Generate flashcards from an uploaded image via OCR and AI."""
	uploaded_image = request.FILES.get("image")
	if uploaded_image is None:
		return Response(
			{
				"success": False,
				"error": "No image uploaded. Use multipart/form-data with an 'image' field.",
			},
			status=status.HTTP_400_BAD_REQUEST,
		)

	logger.info(
		"Flashcards request received: filename=%s, size=%s, content_type=%s",
		uploaded_image.name,
		uploaded_image.size,
		uploaded_image.content_type,
	)

	validation_error = _validate_uploaded_image(uploaded_image)
	if validation_error:
		status_code = (
			status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
			if "too large" in validation_error.lower()
			else status.HTTP_400_BAD_REQUEST
		)
		logger.warning("Flashcards request validation failed: %s", validation_error)
		return Response(
			{
				"success": False,
				"error": validation_error,
			},
			status=status_code,
		)

	try:
		ocr_text = _extract_text_from_image(uploaded_image)
	except pytesseract.TesseractNotFoundError:
		logger.exception("Tesseract executable is not configured.")
		return Response(
			{
				"success": False,
				"error": "OCR engine is not configured on the server.",
			},
			status=status.HTTP_500_INTERNAL_SERVER_ERROR,
		)
	except UnidentifiedImageError:
		return Response(
			{
				"success": False,
				"error": "The uploaded file is not a valid image.",
			},
			status=status.HTTP_400_BAD_REQUEST,
		)
	except OSError:
		logger.exception("Failed to read uploaded image.")
		return Response(
			{
				"success": False,
				"error": "Could not read the uploaded image.",
			},
			status=status.HTTP_400_BAD_REQUEST,
		)
	except Exception:
		logger.exception("Unexpected OCR failure.")
		return Response(
			{
				"success": False,
				"error": "OCR processing failed.",
			},
			status=status.HTTP_500_INTERNAL_SERVER_ERROR,
		)

	logger.info("OCR extracted text preview: %s", (ocr_text or "")[:100])

	cleaned_text = _clean_ocr_text(ocr_text)
	if not cleaned_text:
		logger.warning("OCR produced no readable text after cleaning.")
		return Response(
			{
				"success": False,
				"error": "No readable text detected in the uploaded image.",
			},
			status=status.HTTP_422_UNPROCESSABLE_ENTITY,
		)

	flashcards = generate_ai_flashcards(cleaned_text)
	is_valid, validated_flashcards, ai_validation_error = _validate_flashcards_payload(
		flashcards
	)

	if not is_valid:
		logger.error("AI flashcard response failed validation: %s", ai_validation_error)
		return Response(
			{
				"success": False,
				"error": "AI generated an invalid flashcards format.",
			},
			status=status.HTTP_502_BAD_GATEWAY,
		)

	logger.info("AI flashcard generation succeeded: count=%s", len(validated_flashcards))
	return Response(
		{
			"success": True,
			"flashcards": validated_flashcards,
		},
		status=status.HTTP_200_OK,
	)
