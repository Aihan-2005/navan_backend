from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.reading.models import (
    ReadingAnalysis,
    ReadingSection,
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
class ReadingAPITests(
    TemporaryMediaMixin,
    APITestCase,
):
    def setUp(self):
        self.user = create_user(
            index=1,
            level="B1",
        )

        self.other_user = create_user(
            index=2,
            level="B2",
        )

        self.resource = create_system_resource(index=1)

        self.client.force_authenticate(user=self.user)

    def create_url(self):
        return reverse("reading:analysis-create")

    def detail_url(
        self,
        analysis_id,
    ):
        return reverse(
            "reading:analysis-detail",
            kwargs={
                "analysis_id": analysis_id,
            },
        )

    def sections_url(
        self,
        analysis_id,
    ):
        return reverse(
            "reading:analysis-section-list",
            kwargs={
                "analysis_id": analysis_id,
            },
        )

    def section_detail_url(
        self,
        analysis_id,
        section_id,
    ):
        return reverse(
            "reading:analysis-section-detail",
            kwargs={
                "analysis_id": analysis_id,
                "section_id": section_id,
            },
        )

    def retry_url(
        self,
        analysis_id,
    ):
        return reverse(
            "reading:analysis-retry",
            kwargs={
                "analysis_id": analysis_id,
            },
        )

    def test_authentication_required(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.create_url(),
            {
                "resource_type": "system",
                "resource_id": (self.resource.id),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    @patch("apps.reading.services.prepare_reading_analysis.delay")
    def test_create_system_analysis_returns_202(
        self,
        mock_delay,
    ):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                self.create_url(),
                {
                    "resource_type": "system",
                    "resource_id": (self.resource.id),
                },
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_202_ACCEPTED,
        )

        self.assertTrue(response.data["created"])

        self.assertFalse(response.data["reused"])

        self.assertEqual(
            response.data["analysis"]["status"],
            "PENDING",
        )

        analysis = ReadingAnalysis.objects.get(user=self.user)

        self.assertEqual(
            analysis.system_resource_id,
            self.resource.id,
        )

        mock_delay.assert_called_once_with(analysis.id)

    def test_invalid_resource_type_returns_400(
        self,
    ):
        response = self.client.post(
            self.create_url(),
            {
                "resource_type": "invalid",
                "resource_id": self.resource.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_missing_resource_returns_404(
        self,
    ):
        response = self.client.post(
            self.create_url(),
            {
                "resource_type": "system",
                "resource_id": 999999,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_other_users_upload_returns_404(
        self,
    ):
        other_resource = create_user_resource(
            user=self.other_user,
            index=1,
        )

        response = self.client.post(
            self.create_url(),
            {
                "resource_type": "user",
                "resource_id": (other_resource.id),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_same_active_analysis_reused(
        self,
    ):
        existing = create_analysis(
            user=self.user,
            resource=self.resource,
            status=(ReadingAnalysis.STATUS_PROCESSING),
        )

        response = self.client.post(
            self.create_url(),
            {
                "resource_type": "system",
                "resource_id": self.resource.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(response.data["reused"])

        self.assertEqual(
            response.data["analysis"]["id"],
            existing.id,
        )

    def test_different_resource_returns_409(
        self,
    ):
        existing = create_analysis(
            user=self.user,
            resource=self.resource,
            status=(ReadingAnalysis.STATUS_PROCESSING),
        )

        other_resource = create_system_resource(index=2)

        response = self.client.post(
            self.create_url(),
            {
                "resource_type": "system",
                "resource_id": (other_resource.id),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

        self.assertEqual(
            response.data["active_analysis_id"],
            existing.id,
        )

    def test_analysis_detail(
        self,
    ):
        analysis = create_analysis(
            user=self.user,
            resource=self.resource,
            status=(ReadingAnalysis.STATUS_PROCESSING),
        )

        response = self.client.get(self.detail_url(analysis.id))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["id"],
            analysis.id,
        )

    def test_other_users_analysis_hidden(
        self,
    ):
        other_resource = create_system_resource(index=2)

        analysis = create_analysis(
            user=self.other_user,
            resource=other_resource,
            status=(ReadingAnalysis.STATUS_PROCESSING),
        )

        response = self.client.get(self.detail_url(analysis.id))

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_section_list_is_lightweight(
        self,
    ):
        analysis = create_analysis(
            user=self.user,
            resource=self.resource,
            status=(ReadingAnalysis.STATUS_PROCESSING),
        )

        ReadingSection.objects.create(
            analysis=analysis,
            order=1,
            title="First",
            summary="First summary",
            data={"paragraphs": [{"text": "heavy payload"}]},
        )

        ReadingSection.objects.create(
            analysis=analysis,
            order=2,
            title="Second",
            summary="Second summary",
            data={"paragraphs": []},
        )

        response = self.client.get(self.sections_url(analysis.id))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["count"],
            2,
        )

        self.assertNotIn(
            "data",
            response.data["results"][0],
        )

    def test_section_detail_has_full_data(
        self,
    ):
        analysis = create_analysis(
            user=self.user,
            resource=self.resource,
            status=(ReadingAnalysis.STATUS_PROCESSING),
        )

        section = ReadingSection.objects.create(
            analysis=analysis,
            order=1,
            title="First",
            summary="First summary",
            data={
                "paragraphs": [
                    {
                        "text": "Hello",
                        "meaning_fa": "سلام",
                    }
                ],
                "quiz": [],
            },
        )

        response = self.client.get(
            self.section_detail_url(
                analysis.id,
                section.id,
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["data"]["paragraphs"][0]["text"],
            "Hello",
        )

    @patch("apps.reading.services.prepare_reading_analysis.delay")
    def test_retry_failed_returns_new_analysis(
        self,
        mock_delay,
    ):
        failed = create_analysis(
            user=self.user,
            resource=self.resource,
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
            response = self.client.post(
                self.retry_url(failed.id),
                {},
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_202_ACCEPTED,
        )

        self.assertEqual(
            response.data["retried_from_analysis_id"],
            failed.id,
        )

        self.assertNotEqual(
            response.data["analysis"]["id"],
            failed.id,
        )

        self.assertEqual(
            response.data["analysis"]["status"],
            "PENDING",
        )

        mock_delay.assert_called_once()

    def test_retry_completed_returns_409(
        self,
    ):
        completed = create_analysis(
            user=self.user,
            resource=self.resource,
            status=(ReadingAnalysis.STATUS_COMPLETED),
        )

        response = self.client.post(
            self.retry_url(completed.id),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )
