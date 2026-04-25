from django.urls import path

from .views import generate_flashcards

app_name = "flashcards"

urlpatterns = [
    path("", generate_flashcards, name="generate_flashcards"),
]
