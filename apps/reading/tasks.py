import logging

from celery import chord, shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .ai import analyze_reading_overview, analyze_reading_section
from .ai_client import (
    ReadingAIPermanentError,
    ReadingAITransientError,
)
from .chunking import chunk_text
from .extractors import (
    ReadingExtractionError,
    extract_reading_document,
)
from .models import (
    ReadingAnalysis,
    ReadingSection,
    ReadingSourceChunk,
    UserReadingResource,
)

logger = logging.getLogger(__name__)


def _backoff_seconds(retries: int) -> int:
    return min(2 ** max(retries, 0), 30)


def _safe_error_message(exc: Exception) -> str:
    return str(exc)[:4000]


def _mark_failed(
    *,
    analysis_id: int,
    code: str,
    message: str,
) -> None:
    ReadingAnalysis.objects.filter(pk=analysis_id).update(
        status=ReadingAnalysis.STATUS_FAILED,
        error_code=code[:64],
        error_message=message[:4000],
        completed_at=timezone.now(),
    )


def _add_usage(
    analysis_id: int,
    result,
) -> None:
    ReadingAnalysis.objects.filter(pk=analysis_id).update(
        input_tokens=(F("input_tokens") + result.usage.input_tokens),
        output_tokens=(F("output_tokens") + result.usage.output_tokens),
        total_tokens=(F("total_tokens") + result.usage.total_tokens),
    )


@shared_task(
    bind=True,
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
)
def prepare_reading_analysis(
    self,
    analysis_id: int,
):
    try:
        analysis = ReadingAnalysis.objects.select_related(
            "user",
            "system_resource",
            "user_resource",
        ).get(pk=analysis_id)

    except ReadingAnalysis.DoesNotExist:
        logger.warning(
            "Reading analysis %s no longer exists.",
            analysis_id,
        )

        return {
            "ok": False,
            "reason": "analysis_not_found",
        }

    if analysis.status == ReadingAnalysis.STATUS_COMPLETED:
        return {
            "ok": True,
            "reason": "already_completed",
        }

    if analysis.sections_dispatched_at is not None:
        return {
            "ok": True,
            "reason": ("sections_already_dispatched"),
        }

    ReadingAnalysis.objects.filter(pk=analysis_id).update(
        status=(ReadingAnalysis.STATUS_PROCESSING),
        started_at=(analysis.started_at or timezone.now()),
        progress_percent=5,
        error_code="",
        error_message="",
        completed_at=None,
    )

    resource = analysis.resource

    if resource is None or not resource.file:
        _mark_failed(
            analysis_id=analysis_id,
            code="RESOURCE_FILE_MISSING",
            message=("Reading resource has no file."),
        )

        return {
            "ok": False,
            "reason": "resource_file_missing",
        }

    try:
        document = extract_reading_document(resource.file)

        chunks = chunk_text(
            document.text,
            target_chars=(settings.READING_AI_CHUNK_TARGET_CHARS),
            max_chars=(settings.READING_AI_CHUNK_MAX_CHARS),
        )

        if not chunks:
            raise ReadingExtractionError("No analyzable text chunks were created.")

        if len(chunks) > settings.READING_AI_MAX_CHUNKS:
            raise ReadingExtractionError(
                f"Document requires {len(chunks)} "
                "chunks; maximum allowed is "
                f"{settings.READING_AI_MAX_CHUNKS}."
            )

        if (
            isinstance(
                resource,
                UserReadingResource,
            )
            and document.page_count is not None
        ):
            (
                UserReadingResource.objects.filter(pk=resource.pk).update(
                    page_count=(document.page_count)
                )
            )

        with transaction.atomic():
            (ReadingSourceChunk.objects.filter(analysis_id=analysis_id).delete())

            (
                ReadingSourceChunk.objects.bulk_create(
                    [
                        ReadingSourceChunk(
                            analysis_id=(analysis_id),
                            order=chunk.order,
                            text=chunk.text,
                            char_count=(chunk.char_count),
                        )
                        for chunk in chunks
                    ]
                )
            )

        overview_result = analyze_reading_overview(
            text=document.text,
            learner_level=(analysis.target_level),
        )

        overview = overview_result.data

        ReadingAnalysis.objects.filter(pk=analysis_id).update(
            detected_level=(overview.detected_level),
            difficulty_profile=(overview.difficulty_profile.model_dump(mode="json")),
            vocabulary_profile=(overview.vocabulary_profile.model_dump(mode="json")),
            quality_profile=(overview.quality_profile.model_dump(mode="json")),
            overview={
                "title_guess": (overview.title_guess),
                "summary_fa": (overview.summary_fa),
                "learning_objectives_fa": (overview.learning_objectives_fa),
            },
            progress_percent=15,
            first_result_at=(analysis.first_result_at or timezone.now()),
        )

        _add_usage(
            analysis_id,
            overview_result,
        )

        chunk_ids = list(
            ReadingSourceChunk.objects.filter(analysis_id=analysis_id)
            .order_by("order")
            .values_list(
                "id",
                flat=True,
            )
        )

        header = [analyze_reading_chunk.s(chunk_id) for chunk_id in chunk_ids]

        callback = finalize_reading_analysis.s(analysis_id)

        chord(header)(callback)

        ReadingAnalysis.objects.filter(pk=analysis_id).update(
            sections_dispatched_at=(timezone.now())
        )

        return {
            "ok": True,
            "chunks": len(chunk_ids),
        }

    except ReadingAITransientError as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(
                exc=exc,
                countdown=_backoff_seconds(self.request.retries),
            ) from exc

        _mark_failed(
            analysis_id=analysis_id,
            code=exc.code,
            message=_safe_error_message(exc),
        )

        logger.exception(
            ("Reading AI transient error exhausted retries for analysis %s"),
            analysis_id,
        )

        return {
            "ok": False,
            "reason": exc.code,
        }

    except ReadingAIPermanentError as exc:
        _mark_failed(
            analysis_id=analysis_id,
            code=exc.code,
            message=_safe_error_message(exc),
        )

        logger.exception(
            ("Permanent reading AI error for analysis %s"),
            analysis_id,
        )

        return {
            "ok": False,
            "reason": exc.code,
        }

    except ReadingExtractionError as exc:
        error_code = getattr(
            exc,
            "code",
            "EXTRACTION_ERROR",
        )

        _mark_failed(
            analysis_id=analysis_id,
            code=error_code,
            message=_safe_error_message(exc),
        )

        logger.exception(
            ("Reading extraction failed for analysis %s"),
            analysis_id,
        )

        return {
            "ok": False,
            "reason": error_code,
        }

    except Exception as exc:
        _mark_failed(
            analysis_id=analysis_id,
            code=("UNEXPECTED_PREPARE_ERROR"),
            message=_safe_error_message(exc),
        )

        logger.exception(
            ("Unexpected reading prepare error for analysis %s"),
            analysis_id,
        )

        raise


@shared_task(
    bind=True,
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
)
def analyze_reading_chunk(
    self,
    chunk_id: int,
):
    try:
        chunk = ReadingSourceChunk.objects.select_related(
            "analysis",
            "analysis__user",
        ).get(pk=chunk_id)

    except ReadingSourceChunk.DoesNotExist:
        return {
            "ok": False,
            "error_code": "CHUNK_NOT_FOUND",
            "error_message": (f"Reading source chunk {chunk_id} does not exist."),
        }

    analysis = chunk.analysis

    if analysis.status == ReadingAnalysis.STATUS_FAILED:
        return {
            "ok": False,
            "error_code": ("ANALYSIS_ALREADY_FAILED"),
            "error_message": ("Analysis was already marked as failed."),
        }

    existing = ReadingSection.objects.filter(
        analysis_id=analysis.id,
        order=chunk.order,
    ).first()

    if existing:
        return {
            "ok": True,
            "section_id": existing.id,
            "order": existing.order,
            "reused": True,
        }

    try:
        result = analyze_reading_section(
            text=chunk.text,
            learner_level=(analysis.target_level),
            section_order=chunk.order,
        )

        data = result.data

        section, _ = ReadingSection.objects.update_or_create(
            analysis_id=analysis.id,
            order=chunk.order,
            defaults={
                "title": (data.title[:255]),
                "summary": (data.summary_fa),
                "data": {
                    "paragraphs": [
                        (paragraph.model_dump(mode="json")) for paragraph in data.paragraphs
                    ],
                    "quiz": [item.model_dump(mode="json") for item in data.quiz],
                    "prompt_version": (analysis.prompt_version),
                    "schema_version": (analysis.schema_version),
                },
            },
        )

        _add_usage(
            analysis.id,
            result,
        )

        ReadingAnalysis.objects.filter(
            pk=analysis.id,
            first_result_at__isnull=True,
        ).update(first_result_at=timezone.now())

        total = ReadingSourceChunk.objects.filter(analysis_id=analysis.id).count()

        completed = ReadingSection.objects.filter(analysis_id=analysis.id).count()

        if total:
            progress = min(
                95,
                15 + int((completed / total) * 80),
            )

            ReadingAnalysis.objects.filter(
                pk=analysis.id,
                status=(ReadingAnalysis.STATUS_PROCESSING),
            ).update(progress_percent=progress)

        return {
            "ok": True,
            "section_id": section.id,
            "order": section.order,
            "reused": False,
        }

    except ReadingAITransientError as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(
                exc=exc,
                countdown=_backoff_seconds(self.request.retries),
            ) from exc

        logger.exception(
            ("Reading AI transient error exhausted retries for chunk %s"),
            chunk_id,
        )

        return {
            "ok": False,
            "error_code": exc.code,
            "error_message": (_safe_error_message(exc)),
            "order": chunk.order,
        }

    except ReadingAIPermanentError as exc:
        logger.exception(
            ("Permanent reading AI error for chunk %s"),
            chunk_id,
        )

        return {
            "ok": False,
            "error_code": exc.code,
            "error_message": (_safe_error_message(exc)),
            "order": chunk.order,
        }

    except Exception as exc:
        logger.exception(
            ("Unexpected reading AI error for chunk %s"),
            chunk_id,
        )

        return {
            "ok": False,
            "error_code": ("UNEXPECTED_SECTION_ERROR"),
            "error_message": (_safe_error_message(exc)),
            "order": chunk.order,
        }


@shared_task(acks_late=True)
def finalize_reading_analysis(
    results: list[dict],
    analysis_id: int,
):
    failures = [result for result in results if not result.get("ok")]

    if failures:
        first = failures[0]

        _mark_failed(
            analysis_id=analysis_id,
            code=first.get(
                "error_code",
                "SECTION_ANALYSIS_FAILED",
            ),
            message=first.get(
                "error_message",
                ("One or more sections failed."),
            ),
        )

        return {
            "ok": False,
            "failures": len(failures),
        }

    expected = ReadingSourceChunk.objects.filter(analysis_id=analysis_id).count()

    actual = ReadingSection.objects.filter(analysis_id=analysis_id).count()

    if expected == 0 or actual != expected:
        _mark_failed(
            analysis_id=analysis_id,
            code="SECTION_COUNT_MISMATCH",
            message=(f"Expected {expected} sections but found {actual}."),
        )

        return {
            "ok": False,
            "reason": ("section_count_mismatch"),
        }

    ReadingAnalysis.objects.filter(pk=analysis_id).update(
        status=(ReadingAnalysis.STATUS_COMPLETED),
        progress_percent=100,
        completed_at=timezone.now(),
        error_code="",
        error_message="",
    )

    if not settings.READING_AI_KEEP_SOURCE_CHUNKS:
        (ReadingSourceChunk.objects.filter(analysis_id=analysis_id).delete())

    return {
        "ok": True,
        "sections": actual,
    }


# Temporary backwards-compatible alias.
# Remove after all old imports are migrated.
analyze_reading = prepare_reading_analysis
