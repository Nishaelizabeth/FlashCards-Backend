from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from .models import Deck, Flashcard
from .services import StudioAIError


class StudioAPITests(APITestCase):
    def setUp(self):
        self.deck = Deck.objects.create(name="Science Revision")
        self.cards_url = f"/api/studio/decks/{self.deck.id}/cards/"

    def create_card(self, **overrides):
        payload = {
            "question": "What is photosynthesis?",
            "answer": "Plants use light to make food.",
            "theme": "green",
            **overrides,
        }
        return self.client.post(self.cards_url, payload, format="json")

    def test_deck_crud_and_counts(self):
        created = self.client.post(
            "/api/studio/decks/", {"name": "  English Vocabulary  "}, format="json"
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["name"], "English Vocabulary")
        self.assertEqual(created.data["card_count"], 0)
        self.assertEqual(created.data["difficult_count"], 0)

        deck_url = f"/api/studio/decks/{created.data['id']}/"
        updated = self.client.patch(deck_url, {"name": "Exam Words"}, format="json")
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.data["name"], "Exam Words")

        listed = self.client.get("/api/studio/decks/")
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertIsInstance(listed.data, list)
        self.assertIn("card_count", listed.data[0])

        deleted = self.client.delete(deck_url)
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)

    def test_creates_unlimited_style_cards_without_pagination(self):
        for index in range(25):
            response = self.create_card(question=f"Question {index}")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        listed = self.client.get(self.cards_url)
        self.assertEqual(len(listed.data), 25)

    def test_validates_card_content_and_theme(self):
        empty = self.create_card(question="   ")
        invalid_theme = self.create_card(theme="orange")
        self.assertEqual(empty.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid_theme.status_code, status.HTTP_400_BAD_REQUEST)

    def test_card_update_delete_and_difficult_filter(self):
        first = self.create_card().data
        second = self.create_card(question="What is evaporation?").data

        card_url = f"/api/studio/cards/{first['id']}/"
        updated = self.client.patch(card_url, {"theme": "purple"}, format="json")
        self.assertEqual(updated.data["theme"], "purple")

        practice = self.client.post(
            f"{card_url}practice/", {"need_more_practice": True}, format="json"
        )
        self.assertTrue(practice.data["need_more_practice"])

        difficult = self.client.get(f"{self.cards_url}?difficult=true")
        self.assertEqual(len(difficult.data), 1)
        self.assertEqual(difficult.data[0]["id"], first["id"])

        deleted = self.client.delete(f"/api/studio/cards/{second['id']}/")
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)

    @patch("studio.views.improve_flashcard")
    def test_ai_improvement_is_a_non_destructive_suggestion(self, mock_improve):
        mock_improve.return_value = {
            "question": "What is photosynthesis?",
            "answer": "Photosynthesis is how plants use light to make food.",
        }
        response = self.client.post(
            "/api/studio/ai/improve/",
            {"question": "what photosynthesis", "answer": "plant make food"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Flashcard.objects.count(), 0)

    @patch("studio.views.generate_illustration", return_value=b"png-bytes")
    def test_illustration_is_generated_once_and_reused(self, mock_generate):
        card_id = self.create_card().data["id"]
        url = f"/api/studio/cards/{card_id}/illustration/"
        first = self.client.post(url, {}, format="json")
        second = self.client.post(url, {}, format="json")

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["illustration_status"], "ready")
        mock_generate.assert_called_once()

    @patch("studio.views.generate_illustration")
    def test_illustration_failure_keeps_saved_card(self, mock_generate):
        mock_generate.side_effect = StudioAIError(
            "authentication_error", "OpenAI rejected OPENAI_API_KEY."
        )
        card_id = self.create_card().data["id"]
        response = self.client.post(
            f"/api/studio/cards/{card_id}/illustration/", {}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertTrue(Flashcard.objects.filter(pk=card_id).exists())
        self.assertEqual(
            Flashcard.objects.get(pk=card_id).illustration_status,
            Flashcard.IllustrationStatus.FAILED,
        )
