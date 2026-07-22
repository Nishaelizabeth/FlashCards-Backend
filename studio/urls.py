from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DeckViewSet, FlashcardViewSet, improve_flashcard_view

router = DefaultRouter()
router.register("decks", DeckViewSet, basename="studio-deck")
router.register("cards", FlashcardViewSet, basename="studio-card")

urlpatterns = [
    path("ai/improve/", improve_flashcard_view, name="studio-ai-improve"),
    path("", include(router.urls)),
]
