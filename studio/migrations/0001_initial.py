import django.core.validators
import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Deck",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-updated_at", "name"]},
        ),
        migrations.CreateModel(
            name="Flashcard",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("question", models.TextField(validators=[django.core.validators.MaxLengthValidator(1000)])),
                ("answer", models.TextField(validators=[django.core.validators.MaxLengthValidator(4000)])),
                ("theme", models.CharField(choices=[("blue", "Blue"), ("green", "Green"), ("purple", "Purple"), ("yellow", "Yellow"), ("pink", "Pink")], default="blue", max_length=12)),
                ("ai_improved_question", models.TextField(blank=True, validators=[django.core.validators.MaxLengthValidator(1000)])),
                ("ai_improved_answer", models.TextField(blank=True, validators=[django.core.validators.MaxLengthValidator(4000)])),
                ("ai_improvement_accepted", models.BooleanField(default=False)),
                ("illustration", models.ImageField(blank=True, upload_to="studio/illustrations/")),
                ("illustration_status", models.CharField(choices=[("not_started", "Not started"), ("generating", "Generating"), ("ready", "Ready"), ("failed", "Failed")], default="not_started", max_length=16)),
                ("illustration_error", models.CharField(blank=True, max_length=300)),
                ("need_more_practice", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deck", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="flashcards", to="studio.deck")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddIndex(
            model_name="flashcard",
            index=models.Index(fields=["deck", "need_more_practice"], name="studio_flas_deck_id_dedf92_idx"),
        ),
    ]
