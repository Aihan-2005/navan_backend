from rest_framework import serializers

from apps.listening.api.serializers import (
    ListeningContentSummarySerializer,
)
from apps.listening.choices import (
    ListeningContentType,
    ListeningPracticeMode,
)


class ListeningStatsSerializer(
    serializers.Serializer,
):
    totalSessions = serializers.IntegerField(
        min_value=0,
    )

    weeklyMinutes = serializers.IntegerField(
        min_value=0,
    )

    averageAccuracyScore = serializers.FloatField(
        min_value=0,
        max_value=100,
    )

    bestAccuracyScore = serializers.FloatField(
        min_value=0,
        max_value=100,
    )

    currentStreakDays = serializers.IntegerField(
        min_value=0,
    )


class ContinueListeningSerializer(
    serializers.Serializer,
):
    attemptId = serializers.UUIDField()
    contentId = serializers.UUIDField()

    title = serializers.CharField()

    description = serializers.CharField(
        allow_null=True,
    )

    practiceMode = serializers.ChoiceField(
        choices=(ListeningPracticeMode.choices),
    )

    progressPercent = serializers.FloatField(
        min_value=0,
        max_value=100,
    )

    currentPositionSeconds = serializers.IntegerField(
        min_value=0,
    )

    durationSeconds = serializers.IntegerField(
        min_value=1,
    )

    updatedAt = serializers.DateTimeField()


class ListeningInsightSerializer(
    serializers.Serializer,
):
    id = serializers.CharField()

    type = serializers.ChoiceField(
        choices=(
            "strength",
            "weakness",
            "recommendation",
            "achievement",
        ),
    )

    title = serializers.CharField()
    description = serializers.CharField()

    actionLabel = serializers.CharField(
        allow_null=True,
    )

    actionHref = serializers.CharField(
        allow_null=True,
    )

    createdAt = serializers.DateTimeField()


class RecentListeningActivitySerializer(
    serializers.Serializer,
):
    id = serializers.UUIDField()
    contentId = serializers.UUIDField()

    title = serializers.CharField()

    contentType = serializers.ChoiceField(
        choices=(ListeningContentType.choices),
    )

    practiceMode = serializers.ChoiceField(
        choices=(ListeningPracticeMode.choices),
    )

    durationMinutes = serializers.IntegerField(
        min_value=0,
    )

    accuracyScore = serializers.FloatField(
        min_value=0,
        max_value=100,
    )

    completedAt = serializers.DateTimeField()


class ListeningOverviewSerializer(
    serializers.Serializer,
):
    stats = ListeningStatsSerializer()

    continueListening = ContinueListeningSerializer(
        allow_null=True,
    )

    featuredContents = ListeningContentSummarySerializer(
        many=True,
    )

    recommendedContents = ListeningContentSummarySerializer(
        many=True,
    )

    primaryInsight = ListeningInsightSerializer(
        allow_null=True,
    )

    recentActivities = RecentListeningActivitySerializer(
        many=True,
    )
