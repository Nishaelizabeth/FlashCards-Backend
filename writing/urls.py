from django.urls import path

from .views import (
    generate_chinese,
    generate_english,
    translate_chinese_page_content,
    translate_chinese_text,
)

app_name = "writing"

urlpatterns = [
    path("english/", generate_english, name="generate_english"),
    path("chinese/", generate_chinese, name="generate_chinese"),
    path("translate/", translate_chinese_text, name="translate_chinese_text"),
    path(
        "translate/chinese-page/",
        translate_chinese_page_content,
        name="translate_chinese_page_content",
    ),
]
