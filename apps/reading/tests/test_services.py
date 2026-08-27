from unittest.mock import patch

from django.test import (
    TestCase,
    override_settings,
)
from django.utils import timezone

from apps.reading.exceptions import (
    ActiveReadingConflictError,
    ReadingResourceAccessDeniedError,
    ReadingResourceNotFoundError,
    ReadingRetryNotAllowedError,
)
from apps.reading.models import (
    ReadingAnalysis,
)
from apps.reading.services import (
    get_or_create_reading_analysis,
    resolve_reading_resource,
    retry_failed_reading_analysis,
)

from .helpers import (
    TemporaryMediaMixin,
    create_analysis,
    create_system_resource,
    create_user,
    create_user_resource,
)


@override_settings(
    READING_AI_PROVIDER="openai",
    READING_AI_MODEL="test-model",
    READING_AI_PROMPT_VERSION="test-prompt-v1",
    READING_AI_SCHEMA_VERSION="test-schema-v1",
)
class ReadingServiceTests(
    TemporaryMediaMixin,
    TestCase,
):
    def setUp(self):
        self.user = create_user(
            index=1,
            level="B1",
        )

        self.system_resource = create_system_resource(index=1)

    def test_resolve_system_resource(self):
        resource = resolve_reading_resource(
            user=self.user,
            resource_type="system",
            resource_id=(self.system_resource.id),
        )

        self.assertEqual(
            resource.id,
            self.system_resource.id,
        )

    def test_missing_resource_raises_error(
        self,
    ):
        with self.assertRaises(ReadingResourceNotFoundError):
            resolve_reading_resource(
                user=self.user,
                resource_type="system",
                resource_id=999999,
            )

    def test_other_users_resource_is_hidden(
        self,
    ):
        other_user = create_user(index=2)

        other_resource = create_user_resource(
            user=other_user,
            index=1,
        )

        with self.assertRaises(ReadingResourceNotFoundError):
            resolve_reading_resource(
                user=self.user,
                resource_type="user",
                resource_id=other_resource.id,
            )

    @patch("apps.reading.services.prepare_reading_analysis.delay")
    def test_create_analysis_queues_after_commit(
        self,
        mock_delay,
    ):
        with self.captureOnCommitCallbacks(execute=True):
            analysis, created = get_or_create_reading_analysis(
                user=self.user,
                resource=(self.system_resource),
            )

        self.assertTrue(created)

        self.assertEqual(
            analysis.system_resource_id,
            self.system_resource.id,
        )

        self.assertIsNone(analysis.user_resource_id)

        self.assertEqual(
            analysis.status,
            ReadingAnalysis.STATUS_PENDING,
        )

        mock_delay.assert_called_once_with(analysis.id)

    @patch("apps.reading.services.prepare_reading_analysis.delay")
    def test_same_active_resource_is_reused(
        self,
        mock_delay,
    ):
        existing = create_analysis(
            user=self.user,
            resource=self.system_resource,
            status=(ReadingAnalysis.STATUS_PROCESSING),
        )

        analysis, created = get_or_create_reading_analysis(
            user=self.user,
            resource=self.system_resource,
        )

        self.assertFalse(created)

        self.assertEqual(
            analysis.id,
            existing.id,
        )

        mock_delay.assert_not_called()

    def test_different_resource_conflicts(
        self,
    ):
        create_analysis(
            user=self.user,
            resource=self.system_resource,
            status=(ReadingAnalysis.STATUS_PROCESSING),
        )

        other_resource = create_system_resource(index=2)

        with self.assertRaises(ActiveReadingConflictError) as ctx:
            get_or_create_reading_analysis(
                user=self.user,
                resource=other_resource,
            )

        self.assertIsNotNone(ctx.exception.analysis_id)

    @patch("apps.reading.services.prepare_reading_analysis.delay")
    def test_completed_analysis_is_used_as_cache(
        self,
        mock_delay,
    ):
        completed = ReadingAnalysis.objects.create(
            user=self.user,
            system_resource=(self.system_resource),
            status=(ReadingAnalysis.STATUS_COMPLETED),
            target_level="B1",
            provider="openai",
            model_name="test-model",
            prompt_version=("test-prompt-v1"),
            schema_version=("test-schema-v1"),
            completed_at=timezone.now(),
        )

        analysis, created = get_or_create_reading_analysis(
            user=self.user,
            resource=self.system_resource,
        )

        self.assertFalse(created)

        self.assertEqual(
            analysis.id,
            completed.id,
        )

        mock_delay.assert_not_called()

    def test_direct_foreign_resource_rejected(
        self,
    ):
        other_user = create_user(index=2)

        resource = create_user_resource(
            user=other_user,
            index=1,
        )

        with self.assertRaises(ReadingResourceAccessDeniedError):
            get_or_create_reading_analysis(
                user=self.user,
                resource=resource,
            )

    @patch("apps.reading.services.prepare_reading_analysis.delay")
    def test_retry_failed_creates_new_analysis(
        self,
        mock_delay,
    ):
        failed = create_analysis(
            user=self.user,
            resource=self.system_resource,
            status=(ReadingAnalysis.STATUS_FAILED),
        )

        failed.error_code = "AI_TIMEOUT"
        failed.error_message = "Timed out"
        failed.completed_at = timezone.now()

        failed.save(
            update_fields=[
                "error_code",
                "error_message",
                "completed_at",
            ]
        )

        with self.captureOnCommitCallbacks(execute=True):
            retried = retry_failed_reading_analysis(
                user=self.user,
                analysis=failed,
            )

        self.assertNotEqual(
            retried.id,
            failed.id,
        )

        self.assertEqual(
            retried.status,
            ReadingAnalysis.STATUS_PENDING,
        )

        failed.refresh_from_db()

        self.assertEqual(
            failed.status,
            ReadingAnalysis.STATUS_FAILED,
        )

        mock_delay.assert_called_once_with(retried.id)

    def test_retry_non_failed_rejected(
        self,
    ):
        analysis = create_analysis(
            user=self.user,
            resource=self.system_resource,
            status=(ReadingAnalysis.STATUS_COMPLETED),
        )

        with self.assertRaises(ReadingRetryNotAllowedError):
            retry_failed_reading_analysis(
                user=self.user,
                analysis=analysis,
            )
