from django.urls import path

from .views import generate_chinese, generate_english

app_name = "writing"

urlpatterns = [
    path("english/", generate_english, name="generate_english"),
    path("chinese/", generate_chinese, name="generate_chinese"),
]
