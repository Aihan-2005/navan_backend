from collections.abc import Mapping
from typing import Any

from django.db.models import Q, QuerySet

from apps.listening.choices import (
    ListeningContentStatus,
)
from apps.listening.models import ListeningContent
from apps.listening.validators import (
    MAX_PRACTICE_MODES,
)

LISTENING_ORDERING_FIELDS = {
    "featured": (
        "-is_featured",
        "cefr_level",
        "title",
        "id",
    ),
    "newest": (
        "-created_at",
        "title",
        "id",
    ),
    "title": (
        "title",
        "id",
    ),
    "shortest": (
        "duration_seconds",
        "title",
        "id",
    ),
    "longest": (
        "-duration_seconds",
        "title",
        "id",
    ),
}


def _filter_by_practice_mode(
    queryset: QuerySet[ListeningContent],
    practice_mode: str,
) -> QuerySet[ListeningContent]:
    practice_mode_filter = Q()

    for index in range(MAX_PRACTICE_MODES):
        practice_mode_filter |= Q(**{(f"available_practice_modes__{index}"): practice_mode})

    return queryset.filter(
        practice_mode_filter,
    )


def get_listening_contents(
    *,
    user: object,
    filters: Mapping[str, Any],
) -> QuerySet[ListeningContent]:
    queryset = ListeningContent.objects.visible_to(user).defer("reference_transcript")

    content_type = filters.get(
        "contentType",
    )

    if content_type:
        queryset = queryset.filter(
            content_type=content_type,
        )

    source_type = filters.get(
        "sourceType",
    )

    if source_type:
        queryset = queryset.filter(
            source_type=source_type,
        )

    cefr_level = filters.get(
        "cefrLevel",
    )

    if cefr_level:
        queryset = queryset.filter(
            cefr_level=cefr_level,
        )

    accent = filters.get("accent")

    if accent:
        queryset = queryset.filter(
            accent=accent,
        )

    content_status = filters.get(
        "status",
    )

    if content_status:
        queryset = queryset.filter(
            status=content_status,
        )

    if "isFeatured" in filters:
        queryset = queryset.filter(
            is_featured=filters["isFeatured"],
        )

    search = filters.get("search")

    if search:
        queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))

    practice_mode = filters.get(
        "practiceMode",
    )

    if practice_mode:
        queryset = _filter_by_practice_mode(
            queryset,
            practice_mode,
        )

    ordering = filters.get(
        "ordering",
        "featured",
    )

    ordering_fields = LISTENING_ORDERING_FIELDS[ordering]

    return queryset.order_by(
        *ordering_fields,
    )


def get_listening_content_details(
    *,
    user: object,
) -> QuerySet[ListeningContent]:
    return (
        ListeningContent.objects.visible_to(user)
        .filter(
            status=ListeningContentStatus.READY,
        )
        .exclude(
            audio_file="",
            audio_stream_url="",
        )
    )
