from datetime import timedelta
from math import ceil
from typing import Any

from django.db.models import Sum
from django.utils import timezone

from apps.listening.choices import (
    ListeningAttemptStatus,
    ListeningContentStatus,
)
from apps.listening.models import (
    ListeningAttempt,
)
from apps.listening.selectors import (
    get_listening_attempts_for_user,
    get_listening_contents,
)

OVERVIEW_CONTENT_LIMIT = 4


def _calculate_current_streak(
    *,
    attempts,
) -> int:
    completed_datetimes = attempts.exclude(completed_at__isnull=True).values_list(
        "completed_at",
        flat=True,
    )

    completed_dates = {
        timezone.localtime(completed_at).date() for completed_at in completed_datetimes
    }

    if not completed_dates:
        return 0

    today = timezone.localdate()
    yesterday = today - timedelta(days=1)

    if today in completed_dates:
        cursor = today
    elif yesterday in completed_dates:
        cursor = yesterday
    else:
        return 0

    streak = 0

    while cursor in completed_dates:
        streak += 1
        cursor -= timedelta(days=1)

    return streak


def _build_stats(
    *,
    user: object,
) -> dict[str, int | float]:
    completed_attempts = ListeningAttempt.objects.for_user(user).filter(
        status=(ListeningAttemptStatus.COMPLETED),
    )

    total_sessions = completed_attempts.count()

    seven_days_ago = timezone.now() - timedelta(days=7)

    weekly_attempts = completed_attempts.filter(
        completed_at__gte=(seven_days_ago),
    )

    weekly_seconds = (
        weekly_attempts.aggregate(total_seconds=Sum("content__duration_seconds"))["total_seconds"]
        or 0
    )

    weekly_minutes = ceil(weekly_seconds / 60) if weekly_seconds else 0

    return {
        "totalSessions": total_sessions,
        "weeklyMinutes": weekly_minutes,
        # These two values become real
        # in the Analysis phase.
        "averageAccuracyScore": 0.0,
        "bestAccuracyScore": 0.0,
        "currentStreakDays": (
            _calculate_current_streak(
                attempts=(completed_attempts),
            )
        ),
    }


def _build_continue_listening(
    *,
    user: object,
) -> dict[str, Any] | None:
    attempt = (
        get_listening_attempts_for_user(
            user=user,
        )
        .editable()
        .order_by("-updated_at")
        .first()
    )

    if attempt is None:
        return None

    duration_seconds = attempt.content.duration_seconds

    current_position = min(
        float(attempt.current_position_seconds),
        float(duration_seconds),
    )

    if duration_seconds > 0:
        progress_percent = round(
            (current_position / duration_seconds) * 100,
            2,
        )
    else:
        progress_percent = 0.0

    description = attempt.content.description.strip()

    return {
        "attemptId": str(attempt.id),
        "contentId": str(attempt.content_id),
        "title": attempt.content.title,
        "description": (description or None),
        "practiceMode": (attempt.practice_mode),
        "progressPercent": (progress_percent),
        "currentPositionSeconds": int(current_position),
        "durationSeconds": (duration_seconds),
        "updatedAt": (attempt.updated_at),
    }


def _get_featured_contents(
    *,
    user: object,
):
    return list(
        get_listening_contents(
            user=user,
            filters={
                "status": (ListeningContentStatus.READY),
                "isFeatured": True,
                "ordering": "featured",
            },
        )[:OVERVIEW_CONTENT_LIMIT]
    )


def _get_recommended_contents(
    *,
    user: object,
    excluded_content_ids: list,
):
    queryset = get_listening_contents(
        user=user,
        filters={
            "status": (ListeningContentStatus.READY),
            "ordering": "newest",
        },
    )

    if excluded_content_ids:
        queryset = queryset.exclude(
            id__in=excluded_content_ids,
        )

    return list(queryset[:OVERVIEW_CONTENT_LIMIT])


def build_listening_overview(
    *,
    user: object,
) -> dict[str, Any]:
    featured_contents = _get_featured_contents(
        user=user,
    )

    featured_ids = [content.id for content in featured_contents]

    recommended_contents = _get_recommended_contents(
        user=user,
        excluded_content_ids=(featured_ids),
    )

    return {
        "stats": _build_stats(
            user=user,
        ),
        "continueListening": (
            _build_continue_listening(
                user=user,
            )
        ),
        "featuredContents": (featured_contents),
        "recommendedContents": (recommended_contents),
        # Analysis/insight phase.
        "primaryInsight": None,
        # Until scoring exists we do not
        # fabricate accuracyScore.
        "recentActivities": [],
    }
