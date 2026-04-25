from django.urls import path

from .views import generate_chinese, generate_english, translate_chinese_text

app_name = "writing"

urlpatterns = [
    path("english/", generate_english, name="generate_english"),
    path("chinese/", generate_chinese, name="generate_chinese"),
    path("translate/", translate_chinese_text, name="translate_chinese_text"),
]
