from typing import Any

from django.db.models import QuerySet

from apps.speaking.choices import (
    PUBLIC_SPEAKING_MODES,
)
from apps.speaking.models import (
    SpeakingEvaluation,
    SpeakingExercise,
    SpeakingSession,
)


def get_public_speaking_scenarios(
    *,
    filters: dict[str, Any] | None = None,
) -> QuerySet[SpeakingExercise]:
    filters = filters or {}

    queryset = (
        SpeakingExercise.objects.filter(
            is_active=True,
            exercise_type__in=(PUBLIC_SPEAKING_MODES),
            tags__isnull=False,
        )
        .exclude(slug__isnull=True)
        .exclude(slug="")
        .exclude(prompt="")
        .exclude(ai_role="")
        .select_related()
        .prefetch_related("tags")
        .distinct()
    )

    mode = filters.get("mode")

    if mode:
        queryset = queryset.filter(exercise_type=mode)

    cefr_level = filters.get("cefrLevel")

    if cefr_level:
        queryset = queryset.filter(cefr_level=cefr_level)

    is_featured = filters.get("isFeatured")

    if is_featured is not None:
        queryset = queryset.filter(is_recommended=is_featured)

    return queryset.order_by(
        "-is_recommended",
        "order",
        "-created_at",
    )


def get_public_speaking_scenario(
    *,
    scenario_id: str,
) -> SpeakingExercise | None:
    return get_public_speaking_scenarios().filter(slug=scenario_id).first()


def get_user_speaking_sessions(
    *,
    user: object,
) -> QuerySet[SpeakingSession]:
    return SpeakingSession.objects.filter(user=user).select_related("exercise")


def get_completed_user_sessions(
    *,
    user: object,
) -> QuerySet[SpeakingSession]:
    return get_user_speaking_sessions(user=user).filter(status=(SpeakingSession.Status.COMPLETED))


def get_completed_user_evaluations(
    *,
    user: object,
) -> QuerySet[SpeakingEvaluation]:
    return SpeakingEvaluation.objects.filter(
        session__user=user,
        status=(SpeakingEvaluation.Status.COMPLETED),
    ).select_related("session")
