import uuid

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Deck, Flashcard
from .serializers import (
    DeckSerializer,
    FlashcardSerializer,
    ImproveFlashcardSerializer,
    PracticeSerializer,
)
from .services import StudioAIError, generate_illustration, improve_flashcard


def _ai_error_status(code: str) -> int:
    if code == "authentication_error":
        return status.HTTP_503_SERVICE_UNAVAILABLE
    if code == "configuration_error":
        return status.HTTP_500_INTERNAL_SERVER_ERROR
    return status.HTTP_502_BAD_GATEWAY


class DeckViewSet(viewsets.ModelViewSet):
    serializer_class = DeckSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    pagination_class = None

    def get_queryset(self):
        return Deck.objects.annotate(
            card_count=Count("flashcards", distinct=True),
            difficult_count=Count(
                "flashcards", filter=Q(flashcards__need_more_practice=True), distinct=True
            ),
        )

    @action(detail=True, methods=["get", "post"], url_path="cards")
    def cards(self, request, pk=None):
        deck = self.get_object()
        if request.method == "GET":
            cards = deck.flashcards.all()
            if request.query_params.get("difficult", "").lower() in {"1", "true", "yes"}:
                cards = cards.filter(need_more_practice=True)
            return Response(FlashcardSerializer(cards, many=True, context={"request": request}).data)

        serializer = FlashcardSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        card = serializer.save(deck=deck)
        return Response(
            FlashcardSerializer(card, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class FlashcardViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Flashcard.objects.select_related("deck")
    serializer_class = FlashcardSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    pagination_class = None

    @action(detail=True, methods=["post"], url_path="practice")
    def practice(self, request, pk=None):
        card = self.get_object()
        serializer = PracticeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        card.need_more_practice = serializer.validated_data["need_more_practice"]
        card.save(update_fields=["need_more_practice", "updated_at"])
        return Response(FlashcardSerializer(card, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="illustration")
    def illustration(self, request, pk=None):
        card = self.get_object()
        if card.illustration:
            return Response(FlashcardSerializer(card, context={"request": request}).data)

        with transaction.atomic():
            locked = Flashcard.objects.select_for_update().get(pk=card.pk)
            if locked.illustration:
                return Response(FlashcardSerializer(locked, context={"request": request}).data)
            if locked.illustration_status == Flashcard.IllustrationStatus.GENERATING:
                return Response(
                    {"error": "Illustration generation is already in progress."},
                    status=status.HTTP_409_CONFLICT,
                )
            locked.illustration_status = Flashcard.IllustrationStatus.GENERATING
            locked.illustration_error = ""
            locked.save(update_fields=["illustration_status", "illustration_error", "updated_at"])

        try:
            image_bytes = generate_illustration(card.question, card.answer)
        except StudioAIError as exc:
            Flashcard.objects.filter(pk=card.pk).update(
                illustration_status=Flashcard.IllustrationStatus.FAILED,
                illustration_error=exc.detail[:300],
            )
            return Response(
                {"error": exc.code, "detail": exc.detail},
                status=_ai_error_status(exc.code),
            )

        card.refresh_from_db()
        card.illustration.save(f"{uuid.uuid4()}.png", ContentFile(image_bytes), save=False)
        card.illustration_status = Flashcard.IllustrationStatus.READY
        card.illustration_error = ""
        card.save()
        return Response(FlashcardSerializer(card, context={"request": request}).data)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def improve_flashcard_view(request):
    serializer = ImproveFlashcardSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        suggestion = improve_flashcard(**serializer.validated_data)
    except StudioAIError as exc:
        return Response(
            {"error": exc.code, "detail": exc.detail},
            status=_ai_error_status(exc.code),
        )
    return Response(suggestion)
