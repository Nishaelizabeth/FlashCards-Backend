import io
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase


class FlashcardsAPITests(APITestCase):
	endpoint = "/api/flashcards/"

	def _build_image_file(self) -> SimpleUploadedFile:
		"""Create an in-memory PNG image for upload testing."""
		image = Image.new("RGB", (320, 120), color="white")
		buffer = io.BytesIO()
		image.save(buffer, format="PNG")
		return SimpleUploadedFile(
			name="notes.png",
			content=buffer.getvalue(),
			content_type="image/png",
		)

	@patch("flashcards.views.generate_ai_flashcards")
	@patch("flashcards.views._extract_text_from_image")
	def test_returns_200_for_valid_image(self, mock_extract_text, mock_ai):
		mock_extract_text.return_value = "Photosynthesis is how plants make food."
		mock_ai.return_value = [
			{
				"question": "What is photosynthesis?",
				"answer": "It is how plants make food with sunlight.",
				"highlight": "Plants use sunlight to make food.",
				"image_hint": "cartoon leaf with sun rays",
			}
		]

		response = self.client.post(
			self.endpoint,
			{"image": self._build_image_file()},
			format="multipart",
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertTrue(response.data["success"])
		self.assertIsInstance(response.data["flashcards"], list)
		self.assertEqual(len(response.data["flashcards"]), 1)

	def test_returns_400_for_missing_image(self):
		response = self.client.post(self.endpoint, {}, format="multipart")

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertFalse(response.data["success"])
		self.assertIn("No image uploaded", response.data["error"])

	def test_returns_400_for_invalid_file_type(self):
		bad_file = SimpleUploadedFile(
			name="notes.txt",
			content=b"not-an-image",
			content_type="text/plain",
		)

		response = self.client.post(
			self.endpoint,
			{"image": bad_file},
			format="multipart",
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertFalse(response.data["success"])
		self.assertIn("Invalid file type", response.data["error"])

	def test_returns_413_for_file_too_large(self):
		oversized_file = SimpleUploadedFile(
			name="notes.png",
			content=b"0" * (5 * 1024 * 1024 + 1),
			content_type="image/png",
		)

		response = self.client.post(
			self.endpoint,
			{"image": oversized_file},
			format="multipart",
		)

		self.assertEqual(response.status_code, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
		self.assertFalse(response.data["success"])
		self.assertIn("Maximum size is 5MB", response.data["error"])
