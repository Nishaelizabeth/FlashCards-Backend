from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from services.ai_service import (
	generate_chinese_composition,
	generate_english_composition,
)


def _topic_from_request(request) -> str:
	"""Extract and normalize topic from JSON/form payloads."""
	topic = request.data.get("topic", "") if hasattr(request, "data") else ""
	return str(topic).strip()


def _error_status_from_code(error_code: str) -> int:
	"""Map service-layer error codes to HTTP status codes."""
	if error_code == "configuration_error":
		return status.HTTP_500_INTERNAL_SERVER_ERROR
	if error_code in {"request_failed", "invalid_json_response"}:
		return status.HTTP_502_BAD_GATEWAY
	return status.HTTP_500_INTERNAL_SERVER_ERROR


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def generate_english(request):
	"""Generate English composition guidance from a topic."""
	topic = _topic_from_request(request)
	essay_type = request.data.get("essay_type", "") if hasattr(request, "data") else ""
	if not topic:
		return Response(
			{"error": "Topic is required."},
			status=status.HTTP_400_BAD_REQUEST,
		)

	payload = generate_english_composition(topic, essay_type)
	if isinstance(payload, dict) and "error" in payload:
		return Response(payload, status=_error_status_from_code(payload["error"]))

	return Response(payload, status=status.HTTP_200_OK)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def generate_chinese(request):
	"""Generate Chinese composition guidance from a topic."""
	topic = _topic_from_request(request)
	if not topic:
		return Response(
			{"error": "Topic is required."},
			status=status.HTTP_400_BAD_REQUEST,
		)

	payload = generate_chinese_composition(topic)
	if isinstance(payload, dict) and "error" in payload:
		return Response(payload, status=_error_status_from_code(payload["error"]))

	return Response(payload, status=status.HTTP_200_OK)
