from django.db.models import Count, QuerySet

from apps.reading.models import (
    ReadingAnalysis,
    ReadingSection,
)


def reading_analysis_queryset() -> QuerySet[ReadingAnalysis]:

    return ReadingAnalysis.objects.select_related(
        "system_resource",
        "user_resource",
    ).annotate(
        ready_sections_count=Count(
            "sections",
            distinct=True,
        ),
        source_chunks_count=Count(
            "source_chunks",
            distinct=True,
        ),
    )


def get_user_analysis(
    *,
    user,
    analysis_id: int,
) -> ReadingAnalysis | None:

    return (
        reading_analysis_queryset()
        .filter(
            id=analysis_id,
            user=user,
        )
        .first()
    )


def get_user_analysis_section(
    *,
    user,
    analysis_id: int,
    section_id: int,
) -> ReadingSection | None:
    """
    Return one section while enforcing analysis ownership.
    """

    return (
        ReadingSection.objects.select_related(
            "analysis",
        )
        .filter(
            id=section_id,
            analysis_id=analysis_id,
            analysis__user=user,
        )
        .first()
    )


def list_user_analysis_sections(
    *,
    user,
    analysis_id: int,
) -> QuerySet[ReadingSection]:

    return ReadingSection.objects.filter(
        analysis_id=analysis_id,
        analysis__user=user,
    ).order_by("order")
