from datetime import timedelta
from math import ceil
from typing import Any

from django.db.models import (
    Avg,
    Sum,
)
from django.utils import timezone

from apps.speaking.selectors import (
    get_completed_user_evaluations,
    get_completed_user_sessions,
    get_public_speaking_scenarios,
)

OVERVIEW_SCENARIO_LIMIT = 6


def _calculate_current_streak(
    *,
    sessions,
) -> int:
    completed_datetimes = sessions.exclude(completed_at__isnull=True).values_list(
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


def build_speaking_stats(
    *,
    user: object,
) -> dict[str, int | float]:
    sessions = get_completed_user_sessions(user=user)

    evaluations = get_completed_user_evaluations(user=user)

    week_ago = timezone.now() - timedelta(days=7)

    weekly_seconds = (
        sessions.filter(completed_at__gte=week_ago).aggregate(total=Sum("duration_seconds"))[
            "total"
        ]
        or 0
    )

    averages = evaluations.aggregate(
        average_fluency=Avg("fluency_score"),
        average_pronunciation=Avg("pronunciation_score"),
    )

    average_fluency = averages["average_fluency"]

    average_pronunciation = averages["average_pronunciation"]

    return {
        "totalSessions": (sessions.count()),
        "weeklyMinutes": (ceil(weekly_seconds / 60) if weekly_seconds else 0),
        "averageFluencyScore": round(
            float(average_fluency or 0),
            2,
        ),
        "pronunciationScore": round(
            float(average_pronunciation or 0),
            2,
        ),
        "currentStreak": (_calculate_current_streak(sessions=sessions)),
    }


def build_speaking_overview(
    *,
    user: object,
) -> dict[str, Any]:
    scenarios = list(get_public_speaking_scenarios()[:OVERVIEW_SCENARIO_LIMIT])

    return {
        "stats": build_speaking_stats(user=user),
        "scenarios": scenarios,
    }
