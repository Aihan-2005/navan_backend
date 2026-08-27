from django.urls import path

from .views import (
    ReadingAnalysisCreateAPIView,
    ReadingAnalysisDetailAPIView,
    ReadingAnalysisRetryAPIView,
    ReadingAnalysisSectionDetailAPIView,
    ReadingAnalysisSectionListAPIView,
)

app_name = "reading"


urlpatterns = [
    path(
        "analyses",
        ReadingAnalysisCreateAPIView.as_view(),
        name="analysis-create",
    ),
    path(
        "analyses/<int:analysis_id>",
        ReadingAnalysisDetailAPIView.as_view(),
        name="analysis-detail",
    ),
    path(
        "analyses/<int:analysis_id>/sections",
        ReadingAnalysisSectionListAPIView.as_view(),
        name="analysis-section-list",
    ),
    path(
        ("analyses/<int:analysis_id>/sections/<int:section_id>"),
        ReadingAnalysisSectionDetailAPIView.as_view(),
        name="analysis-section-detail",
    ),
    path(
        "analyses/<int:analysis_id>/retry",
        ReadingAnalysisRetryAPIView.as_view(),
        name="analysis-retry",
    ),
]
