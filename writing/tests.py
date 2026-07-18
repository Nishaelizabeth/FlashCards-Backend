from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class TranslateChinesePageTests(APITestCase):
	@patch("writing.views.translate_chinese_page")
	def test_translates_topic_and_structured_guidance(self, mock_translate):
		mock_translate.return_value = {
			"topic": "My School",
			"guidance": {
				"introduction": "Introduce the school.",
				"body": ["Describe the classrooms."],
				"conclusion": "Share your feelings.",
				"vocabulary": ["lively"],
				"outline": ["Paragraph one"],
				"tips": ["Use descriptive words."],
			},
		}

		response = self.client.post(
			reverse("api_translate_chinese_page_alias"),
			{
				"topic": "我的学校",
				"guidance": {"开头": "介绍学校", "内容": ["描写课室"]},
			},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["topic"], "My School")
		self.assertEqual(response.data["guidance"]["body"], ["Describe the classrooms."])
		mock_translate.assert_called_once_with(
			"我的学校", {"开头": "介绍学校", "内容": ["描写课室"]}
		)

	def test_rejects_an_empty_translation_request(self):
		response = self.client.post(
			reverse("api_translate_chinese_page_alias"), {}, format="json"
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	@patch("writing.views.translate_chinese_page")
	def test_returns_service_unavailable_for_invalid_api_key(self, mock_translate):
		mock_translate.return_value = {
			"error": "authentication_error",
			"detail": "OpenAI rejected OPENAI_API_KEY.",
		}

		response = self.client.post(
			reverse("api_translate_chinese_page_alias"),
			{"topic": "我的学校"},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
		self.assertEqual(response.data["error"], "authentication_error")
