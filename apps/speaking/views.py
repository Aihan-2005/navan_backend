from datetime import timedelta

from django.db.models import Avg, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.speaking.models import SpeakingEvaluation, SpeakingExercise, SpeakingSession, SpeakingTurn
from apps.speaking.serializers import (
    SpeakingEvaluationSerializer,
    SpeakingExerciseListSerializer,
    SpeakingSessionCreateSerializer,
    SpeakingSessionDetailSerializer,
    SpeakingSessionListSerializer,
    SpeakingStatsSerializer,
    SpeakingTurnCreateSerializer,
    SpeakingTurnSerializer,
)
from apps.speaking.services.dialogue import get_dialogue_provider
from apps.speaking.tasks import evaluate_session_task, transcribe_turn_task


class SpeakingExerciseListView(generics.ListAPIView):
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
    """GET: session history. POST: start a session, backend seeds the opening AI turn."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SpeakingSession.objects.filter(user=self.request.user).select_related("exercise")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SpeakingSessionCreateSerializer
        return SpeakingSessionListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = serializer.save(user=request.user)

        dialogue = get_dialogue_provider()
        opening = dialogue.generate_opening_turn(session.exercise)
        SpeakingTurn.objects.create(
            session=session,
            speaker=SpeakingTurn.Speaker.AI,
            order=0,
            text=opening.text,
            transcription_status=SpeakingTurn.TranscriptionStatus.NOT_APPLICABLE,
            transcription_raw=opening.raw,
        )

        return Response(
            SpeakingSessionDetailSerializer(session).data, status=status.HTTP_201_CREATED
        )


class SpeakingSessionDetailView(generics.RetrieveAPIView):
    serializer_class = SpeakingSessionDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            SpeakingSession.objects.filter(user=self.request.user)
            .select_related("exercise")
            .prefetch_related("turns")
        )


class SpeakingTurnCreateView(generics.CreateAPIView):
    """POST /sessions/{session_id}/turns/ — accepts audio, returns 202 immediately
    with a queued status. Transcription + AI reply happen in the background."""

    serializer_class = SpeakingTurnCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_session(self):
        return get_object_or_404(
            SpeakingSession,
            id=self.kwargs["session_id"],
            user=self.request.user,
            status=SpeakingSession.Status.IN_PROGRESS,
        )

    def create(self, request, *args, **kwargs):
        session = self.get_session()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        audio_file = serializer.validated_data["audio_file"]
        next_order = session.turns.count()

        turn = SpeakingTurn.objects.create(
            session=session,
            speaker=SpeakingTurn.Speaker.USER,
            order=next_order,
            audio_file=audio_file,
            audio_format=audio_file.name.rsplit(".", 1)[-1].lower()
            if "." in audio_file.name
            else "",
            audio_size_bytes=audio_file.size,
            audio_duration_seconds=serializer.validated_data["audio_duration_seconds"],
            transcription_status=SpeakingTurn.TranscriptionStatus.QUEUED,
        )

        transcribe_turn_task.delay(str(turn.id))

        return Response(SpeakingTurnSerializer(turn).data, status=status.HTTP_202_ACCEPTED)


class SpeakingTurnDetailView(generics.RetrieveAPIView):
    """GET /sessions/{session_id}/turns/{pk}/ — frontend polls this until
    transcription_status is 'completed' (and can then also poll for the next
    AI turn appearing via the session detail endpoint)."""

    serializer_class = SpeakingTurnSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SpeakingTurn.objects.filter(
            session__id=self.kwargs["session_id"], session__user=self.request.user
        )


class SpeakingSessionCompleteView(APIView):
    """POST /sessions/{session_id}/complete/ — manual 'End Conversation' action.
    Returns 202 with a queued evaluation; frontend polls SpeakingEvaluationDetailView."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(
            SpeakingSession,
            id=session_id,
            user=request.user,
            status=SpeakingSession.Status.IN_PROGRESS,
        )

        user_turn_count = session.turns.filter(speaker=SpeakingTurn.Speaker.USER).count()
        if user_turn_count == 0:
            return Response(
                {
                    "error": {
                        "code": "no_user_turns",
                        "message": "Can't complete a session with no user responses. Submit at least one turn first.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )

        session.status = SpeakingSession.Status.COMPLETED
        session.completed_at = timezone.now()
        session.duration_seconds = int((session.completed_at - session.started_at).total_seconds())
        session.save(update_fields=["status", "completed_at", "duration_seconds"])

        evaluation = SpeakingEvaluation.objects.create(session=session)
        evaluate_session_task.delay(str(evaluation.id))

        return Response(
            SpeakingEvaluationSerializer(evaluation).data, status=status.HTTP_202_ACCEPTED
        )


class SpeakingEvaluationDetailView(generics.RetrieveAPIView):
    """GET /sessions/{session_id}/evaluation/ — poll until status is 'completed'."""

    serializer_class = SpeakingEvaluationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return get_object_or_404(
            SpeakingEvaluation,
            session__id=self.kwargs["session_id"],
            session__user=self.request.user,
        )


class SpeakingStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sessions = SpeakingSession.objects.filter(
            user=request.user, status=SpeakingSession.Status.COMPLETED
        )
        week_ago = timezone.now() - timedelta(days=7)
        minutes_this_week = (
            sessions.filter(completed_at__gte=week_ago).aggregate(total=Sum("duration_seconds"))[
                "total"
            ]
            or 0
        ) / 60

        evaluations = SpeakingEvaluation.objects.filter(
            session__user=request.user, status=SpeakingEvaluation.Status.COMPLETED
        )

        data = {
            "current_streak_days": self._calculate_streak(sessions),
            "average_fluency": evaluations.aggregate(avg=Avg("score"))["avg"],
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
