from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.db import (
    IntegrityError,
    transaction,
)

from apps.listening.choices import (
    LISTENING_ATTEMPT_EDITABLE_STATUSES,
)
from apps.listening.models import (
    ListeningAttempt,
    ListeningContent,
)


class ListeningDomainError(Exception):
    code = "listening_domain_error"


class ListeningPracticeModeUnavailableError(
    ListeningDomainError,
):
    code = "practice_mode_unavailable"


class ListeningAttemptNotEditableError(
    ListeningDomainError,
):
    code = "attempt_not_editable"


class ListeningPositionOutOfRangeError(
    ListeningDomainError,
):
    code = "position_out_of_range"


@transaction.atomic
def start_or_resume_listening_attempt(
    *,
    user: object,
    content: ListeningContent,
    practice_mode: str,
    answer_source: str,
) -> tuple[ListeningAttempt, bool]:
    if practice_mode not in content.available_practice_modes:
        raise (
            ListeningPracticeModeUnavailableError(
                "This practice mode is not available for the selected content."
            )
        )

    lookup = {
        "user": user,
        "content": content,
        "practice_mode": practice_mode,
        "status__in": (LISTENING_ATTEMPT_EDITABLE_STATUSES),
    }

    existing_attempt = (
        ListeningAttempt.objects.select_for_update()
        .filter(**lookup)
        .order_by("-updated_at")
        .first()
    )

    if existing_attempt is not None:
        return existing_attempt, False

    try:
        with transaction.atomic():
            attempt = ListeningAttempt.objects.create(
                user=user,
                content=content,
                practice_mode=practice_mode,
                answer_source=answer_source,
            )
    except IntegrityError:
        attempt = ListeningAttempt.objects.filter(**lookup).order_by("-updated_at").first()

        if attempt is None:
            raise

        return attempt, False

    return attempt, True


@transaction.atomic
def update_listening_attempt_draft(
    *,
    user: object,
    attempt_id: UUID,
    updates: Mapping[str, Any],
) -> ListeningAttempt:
    attempt = (
        ListeningAttempt.objects.select_for_update()
        .select_related("content")
        .get(
            id=attempt_id,
            user=user,
        )
    )

    if not attempt.is_editable:
        raise ListeningAttemptNotEditableError("This listening attempt can no longer be edited.")

    current_position = updates.get("current_position_seconds")

    if current_position is not None and current_position > attempt.content.duration_seconds:
        raise (
            ListeningPositionOutOfRangeError(
                "Playback position cannot be greater than the content duration."
            )
        )

    updated_fields: list[str] = []

    for field_name, value in updates.items():
        setattr(
            attempt,
            field_name,
            value,
        )
        updated_fields.append(field_name)

    attempt.save(
        update_fields=[
            *updated_fields,
            "updated_at",
        ]
    )

    return attempt
