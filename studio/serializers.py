from rest_framework import serializers

from .models import Deck, Flashcard


class DeckSerializer(serializers.ModelSerializer):
    card_count = serializers.SerializerMethodField()
    difficult_count = serializers.SerializerMethodField()

    class Meta:
        model = Deck
        fields = (
            "id", "name", "card_count", "difficult_count", "created_at", "updated_at"
        )
        read_only_fields = ("id", "card_count", "difficult_count", "created_at", "updated_at")

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Deck name cannot be empty.")
        return value

    def get_card_count(self, obj: Deck) -> int:
        annotated = getattr(obj, "card_count", None)
        return annotated if annotated is not None else obj.flashcards.count()

    def get_difficult_count(self, obj: Deck) -> int:
        annotated = getattr(obj, "difficult_count", None)
        return (
            annotated
            if annotated is not None
            else obj.flashcards.filter(need_more_practice=True).count()
        )


class FlashcardSerializer(serializers.ModelSerializer):
    deck_id = serializers.UUIDField(source="deck.id", read_only=True)
    illustration_url = serializers.SerializerMethodField()

    class Meta:
        model = Flashcard
        fields = (
            "id", "deck_id", "question", "answer", "theme",
            "ai_improved_question", "ai_improved_answer", "ai_improvement_accepted",
            "illustration_url", "illustration_status", "illustration_error",
            "need_more_practice", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "deck_id", "illustration_url", "illustration_status",
            "illustration_error", "created_at", "updated_at",
        )

    def get_illustration_url(self, obj: Flashcard) -> str | None:
        if not obj.illustration:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.illustration.url) if request else obj.illustration.url

    def validate_question(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Question cannot be empty.")
        return value

    def validate_answer(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Answer cannot be empty.")
        return value

    def validate(self, attrs):
        accepted = attrs.get(
            "ai_improvement_accepted",
            getattr(self.instance, "ai_improvement_accepted", False),
        )
        if accepted:
            question = attrs.get(
                "ai_improved_question", getattr(self.instance, "ai_improved_question", "")
            )
            answer = attrs.get(
                "ai_improved_answer", getattr(self.instance, "ai_improved_answer", "")
            )
            if not str(question).strip() or not str(answer).strip():
                raise serializers.ValidationError(
                    "Accepted AI improvements require both improved question and answer."
                )
        return attrs


class PracticeSerializer(serializers.Serializer):
    need_more_practice = serializers.BooleanField()


class ImproveFlashcardSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=1000, trim_whitespace=True)
    answer = serializers.CharField(max_length=4000, trim_whitespace=True)
