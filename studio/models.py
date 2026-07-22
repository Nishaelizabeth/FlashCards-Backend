import uuid

from django.core.validators import MaxLengthValidator
from django.db import models


class Deck(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "name"]

    def __str__(self) -> str:
        return self.name


class Flashcard(models.Model):
    class Theme(models.TextChoices):
        BLUE = "blue", "Blue"
        GREEN = "green", "Green"
        PURPLE = "purple", "Purple"
        YELLOW = "yellow", "Yellow"
        PINK = "pink", "Pink"

    class IllustrationStatus(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        GENERATING = "generating", "Generating"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deck = models.ForeignKey(Deck, related_name="flashcards", on_delete=models.CASCADE)
    question = models.TextField(validators=[MaxLengthValidator(1000)])
    answer = models.TextField(validators=[MaxLengthValidator(4000)])
    theme = models.CharField(max_length=12, choices=Theme.choices, default=Theme.BLUE)
    ai_improved_question = models.TextField(blank=True, validators=[MaxLengthValidator(1000)])
    ai_improved_answer = models.TextField(blank=True, validators=[MaxLengthValidator(4000)])
    ai_improvement_accepted = models.BooleanField(default=False)
    illustration = models.ImageField(upload_to="studio/illustrations/", blank=True)
    illustration_status = models.CharField(
        max_length=16,
        choices=IllustrationStatus.choices,
        default=IllustrationStatus.NOT_STARTED,
    )
    illustration_error = models.CharField(max_length=300, blank=True)
    need_more_practice = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["deck", "need_more_practice"])]

    def __str__(self) -> str:
        return self.question[:80]
