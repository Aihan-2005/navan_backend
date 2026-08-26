from django.urls import path

from apps.listening.api.overview_views import (
    ListeningOverviewAPIView,
)
from apps.listening.api.views import (
    ListeningAttemptDraftAPIView,
    ListeningAttemptStartAPIView,
    ListeningContentDetailAPIView,
    ListeningContentListAPIView,
)

app_name = "listening"


urlpatterns = [
    path(
        "overview",
        ListeningOverviewAPIView.as_view(),
        name="overview",
    ),
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
    path(
        "attempts",
        ListeningAttemptStartAPIView.as_view(),
        name="attempt-start",
    ),
    path(
        "attempts/<uuid:attempt_id>/draft",
        ListeningAttemptDraftAPIView.as_view(),
        name="attempt-draft",
    ),
]
