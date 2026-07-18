"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from writing.views import (
    generate_chinese,
    generate_english,
    translate_chinese_page_content,
    translate_chinese_text,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/flashcards/", include("flashcards.urls")),
    path("api/writing/", include("writing.urls")),
    path("api/english/", generate_english, name="api_english_alias"),
    path("api/chinese/", generate_chinese, name="api_chinese_alias"),
    path("api/translate/", translate_chinese_text, name="api_translate_alias"),
    path(
        "api/translate/chinese-page/",
        translate_chinese_page_content,
        name="api_translate_chinese_page_alias",
    ),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
