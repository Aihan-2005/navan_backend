from django.urls import path

from apps.listening.api.views import (
    ListeningContentDetailAPIView,
    ListeningContentListAPIView,
)

app_name = "listening"

urlpatterns = [
    path(
        "contents",
        ListeningContentListAPIView.as_view(),
        name="content-list",
    ),
    path(
        "contents/<uuid:content_id>",
        ListeningContentDetailAPIView.as_view(),
        name="content-detail",
    ),
]
