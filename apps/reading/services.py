from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

from .exceptions import (
    ActiveReadingConflictError,
    ReadingResourceAccessDeniedError,
    ReadingResourceNotFoundError,
    ReadingRetryNotAllowedError,
)
from .models import (
    ReadingAnalysis,
    ReadingResource,
    UserReadingResource,
)
from .tasks import prepare_reading_analysis

ACTIVE_STATUSES = [
    ReadingAnalysis.STATUS_PENDING,
    ReadingAnalysis.STATUS_PROCESSING,
]


def _resource_lookup(resource):
    """
    Convert a resource instance into the correct ReadingAnalysis FK.
    """

    if isinstance(resource, ReadingResource):
        return (
            "system_resource",
            {"system_resource": resource},
        )

    if isinstance(resource, UserReadingResource):
        return (
            "user_resource",
            {"user_resource": resource},
        )

    raise ReadingResourceNotFoundError("Invalid reading resource.")


def resolve_reading_resource(
    *,
    user,
    resource_type: str,
    resource_id: int,
):
    """
    Resolve API input into an actual resource.

    Important:
    UserReadingResource is always scoped by the authenticated user,
    so IDs belonging to another user are not exposed.
    """

    if resource_type == "system":
        resource = ReadingResource.objects.filter(pk=resource_id).first()

        if resource is None:
            raise ReadingResourceNotFoundError("System reading resource not found.")

        return resource

    if resource_type == "user":
        resource = UserReadingResource.objects.filter(
            pk=resource_id,
            user=user,
        ).first()

        if resource is None:
            raise ReadingResourceNotFoundError("User reading resource not found.")

        return resource

    raise ReadingResourceNotFoundError("Unsupported reading resource type.")


def _create_analysis(
    *,
    user,
    resource,
    target_level: str,
) -> ReadingAnalysis:
    """
    Internal helper for creating and queueing an analysis.

    Must be called inside transaction.atomic().
    """

    _, resource_filter = _resource_lookup(resource)

    analysis = ReadingAnalysis.objects.create(
        user=user,
        status=ReadingAnalysis.STATUS_PENDING,
        target_level=target_level,
        provider=settings.READING_AI_PROVIDER,
        model_name=settings.READING_AI_MODEL,
        prompt_version=settings.READING_AI_PROMPT_VERSION,
        schema_version=settings.READING_AI_SCHEMA_VERSION,
        **resource_filter,
    )

    transaction.on_commit(
        lambda analysis_id=analysis.id: prepare_reading_analysis.delay(analysis_id)
    )

    return analysis


def get_or_create_reading_analysis(
    *,
    user,
    resource,
):
    """
    Main entry point for opening a reading resource.

    Rules:
    - One active analysis per user.
    - Same active resource is reused.
    - Completed compatible analysis is cached/reused.
    - Otherwise a new analysis is queued.
    """

    resource_field, resource_filter = _resource_lookup(resource)

    if isinstance(resource, UserReadingResource) and resource.user_id != user.id:
        raise ReadingResourceAccessDeniedError("You do not have access to this reading resource.")

    User = get_user_model()

    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)

        learner_level = locked_user.level or "B1"

        active_analysis = (
            ReadingAnalysis.objects.select_for_update()
            .filter(
                user=locked_user,
                status__in=ACTIVE_STATUSES,
            )
            .first()
        )

        if active_analysis:
            active_resource_id = getattr(
                active_analysis,
                f"{resource_field}_id",
            )

            if active_resource_id == resource.id:
                return active_analysis, False

            raise ActiveReadingConflictError(
                ("You already have another reading analysis in progress."),
                analysis_id=active_analysis.id,
            )

        cached_analysis = (
            ReadingAnalysis.objects.filter(
                user=locked_user,
                status=ReadingAnalysis.STATUS_COMPLETED,
                target_level=learner_level,
                provider=settings.READING_AI_PROVIDER,
                model_name=settings.READING_AI_MODEL,
                prompt_version=(settings.READING_AI_PROMPT_VERSION),
                schema_version=(settings.READING_AI_SCHEMA_VERSION),
                **resource_filter,
            )
            .order_by("-completed_at")
            .first()
        )

        if cached_analysis:
            return cached_analysis, False

        analysis = _create_analysis(
            user=locked_user,
            resource=resource,
            target_level=learner_level,
        )

    return analysis, True


def retry_failed_reading_analysis(
    *,
    user,
    analysis: ReadingAnalysis,
) -> ReadingAnalysis:
    """
    Retry creates a NEW analysis instead of mutating the failed row.

    This preserves history:
        failed analysis #10
            ↓ retry
        new analysis #11

    That is much better for observability/debugging.
    """

    if analysis.user_id != user.id:
        raise ReadingResourceAccessDeniedError("You do not have access to this reading analysis.")

    if analysis.status != ReadingAnalysis.STATUS_FAILED:
        raise ReadingRetryNotAllowedError("Only failed reading analyses can be retried.")

    resource = analysis.resource

    if resource is None:
        raise ReadingResourceNotFoundError(
            "The resource for this reading analysis no longer exists."
        )

    if isinstance(resource, UserReadingResource) and resource.user_id != user.id:
        raise ReadingResourceAccessDeniedError("You do not have access to this reading resource.")

    User = get_user_model()

    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)

        active_analysis = (
            ReadingAnalysis.objects.select_for_update()
            .filter(
                user=locked_user,
                status__in=ACTIVE_STATUSES,
            )
            .first()
        )

        if active_analysis:
            raise ActiveReadingConflictError(
                ("Another reading analysis is already in progress."),
                analysis_id=active_analysis.id,
            )

        target_level = locked_user.level or analysis.target_level or "B1"

        new_analysis = _create_analysis(
            user=locked_user,
            resource=resource,
            target_level=target_level,
        )

    return new_analysis
