# Create your views here.
from datetime import timedelta

from django.db.models import Avg, Sum
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.speaking.models import SpeakingExercise, SpeakingSession, SpeakingTurn
from apps.speaking.serializers import (
    SpeakingExerciseListSerializer,
    SpeakingSessionCreateSerializer,
    SpeakingSessionDetailSerializer,
    SpeakingSessionListSerializer,
    SpeakingStatsSerializer,
    SpeakingTurnCreateSerializer,
    SpeakingTurnSerializer,
)

from apps.speaking.services.assessment import get_assessment_provider
from apps.speaking.services.transcription import get_transcription_provider


class SpeakingExerciseListView(generics.ListAPIView):
    """GET /api/v1/speaking/exercises/?type=roleplay&level=B1"""

    serializer_class = SpeakingExerciseListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = SpeakingExercise.objects.filter(is_active=True).prefetch_related("tags")
        exercise_type = self.request.query_params.get("type")
        cefr_level = self.request.query_params.get("level")
        if exercise_type:
            qs = qs.filter(exercise_type=exercise_type)
        if cefr_level:
            qs = qs.filter(cefr_level=cefr_level)
        return qs


class SpeakingSessionListCreateView(generics.ListCreateAPIView):
    """GET: user's session history. POST: start a new session for an exercise."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SpeakingSession.objects.filter(user=self.request.user).select_related("exercise")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SpeakingSessionCreateSerializer
        return SpeakingSessionListSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SpeakingSessionDetailView(generics.RetrieveAPIView):
    """GET /api/v1/speaking/sessions/{id}/ — full session with turns."""

    serializer_class = SpeakingSessionDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            SpeakingSession.objects.filter(user=self.request.user)
            .select_related("exercise")
            .prefetch_related("turns")
        )


class SpeakingTurnCreateView(generics.CreateAPIView):
    """POST /api/v1/speaking/sessions/{session_id}/turns/ — user uploads audio for their turn."""

    serializer_class = SpeakingTurnCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_session(self):
        return SpeakingSession.objects.get(
            id=self.kwargs["session_id"],
            user=self.request.user,
            status=SpeakingSession.Status.IN_PROGRESS,
        )

    def perform_create(self, serializer):
        session = self.get_session()
        next_order = session.turns.count()

        turn = serializer.save(
            session=session,
            speaker=SpeakingTurn.Speaker.USER,
            order=next_order,
            transcription_status=SpeakingTurn.TranscriptionStatus.PROCESSING,
        )

        # NOTE: synchronous for now. Once Celery is wired in, replace this block
        # with a `.delay()` call and flip transcription_status to PENDING above instead.
        provider = get_transcription_provider()
        result = provider.transcribe(turn.audio_file)
        turn.text = result.text
        turn.transcription_raw = result.raw
        turn.transcription_status = SpeakingTurn.TranscriptionStatus.COMPLETED
        turn.save(update_fields=["text", "transcription_raw", "transcription_status"])

        self._created_turn = turn

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data = SpeakingTurnSerializer(self._created_turn).data
        return response


class SpeakingSessionCompleteView(APIView):
    """POST /api/v1/speaking/sessions/{session_id}/complete/ — ends session, runs assessment."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        try:
            session = SpeakingSession.objects.prefetch_related("turns").get(
                id=session_id, user=request.user, status=SpeakingSession.Status.IN_PROGRESS
            )
        except SpeakingSession.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Active session not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        provider = get_assessment_provider()
        result = provider.assess_session(session)

        session.status = SpeakingSession.Status.COMPLETED
        session.completed_at = timezone.now()
        session.duration_seconds = int((session.completed_at - session.started_at).total_seconds())
        session.fluency_score = result.fluency_score
        session.pronunciation_score = result.pronunciation_score
        session.grammar_score = result.grammar_score
        session.feedback = result.feedback
        session.save()

        return Response(SpeakingSessionDetailSerializer(session).data)


class SpeakingStatsView(APIView):
    """GET /api/v1/speaking/stats/ — powers the stat cards at the top of the page."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sessions = SpeakingSession.objects.filter(
            user=request.user, status=SpeakingSession.Status.COMPLETED
        )

        week_ago = timezone.now() - timedelta(days=7)
        minutes_this_week = (
            sessions.filter(completed_at__gte=week_ago).aggregate(total=Sum("duration_seconds"))["total"] or 0
        ) / 60

        data = {
            "current_streak_days": self._calculate_streak(sessions),
            "average_fluency": sessions.aggregate(avg=Avg("fluency_score"))["avg"],
            "minutes_this_week": round(minutes_this_week, 1),
            "total_sessions": sessions.count(),
        }
        return Response(SpeakingStatsSerializer(data).data)

    def _calculate_streak(self, sessions):
        dates = sorted({s.completed_at.date() for s in sessions.only("completed_at")}, reverse=True)
        if not dates:
            return 0

        today = timezone.now().date()
        if dates[0] not in (today, today - timedelta(days=1)):
            return 0

        streak = 1
        for i in range(len(dates) - 1):
            if (dates[i] - dates[i + 1]).days == 1:
                streak += 1
            else:
                break
        return streak