from django.contrib import admin

from .models import Deck, Flashcard


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")
    search_fields = ("name",)


@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ("question", "deck", "theme", "need_more_practice", "created_at")
    list_filter = ("theme", "need_more_practice", "illustration_status")
    search_fields = ("question", "answer", "deck__name")
