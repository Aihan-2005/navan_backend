from django.urls import path

from apps.speaking import views

app_name = "speaking"

urlpatterns = [
    path("exercises/", views.SpeakingExerciseListView.as_view(), name="exercise-list"),
    path("sessions/", views.SpeakingSessionListCreateView.as_view(), name="session-list-create"),
    path("sessions/<uuid:pk>/", views.SpeakingSessionDetailView.as_view(), name="session-detail"),
    path("sessions/<uuid:session_id>/turns/", views.SpeakingTurnCreateView.as_view(), name="turn-create"),
    path("sessions/<uuid:session_id>/complete/", views.SpeakingSessionCompleteView.as_view(), name="session-complete"),
    path("stats/", views.SpeakingStatsView.as_view(), name="stats"),
]