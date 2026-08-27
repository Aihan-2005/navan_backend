from django.db import (
    IntegrityError,
    transaction,
)
from django.test import TestCase

from apps.reading.models import (
    ReadingAnalysis,
    ReadingSection,
)

from .helpers import (
    TemporaryMediaMixin,
    create_analysis,
    create_system_resource,
    create_user,
)


class ReadingModelTests(
    TemporaryMediaMixin,
    TestCase,
):
    def setUp(self):
        self.user = create_user()

        self.resource = create_system_resource()

    def test_analysis_requires_one_resource(
        self,
    ):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                (
                    ReadingAnalysis.objects.create(
                        user=self.user,
                        status=(ReadingAnalysis.STATUS_PENDING),
                        target_level="B1",
                    )
                )

    def test_analysis_cannot_have_two_resources(
        self,
    ):
        from .helpers import (
            create_user_resource,
        )

        user_resource = create_user_resource(user=self.user)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                (
                    ReadingAnalysis.objects.create(
                        user=self.user,
                        system_resource=(self.resource),
                        user_resource=(user_resource),
                        status=(ReadingAnalysis.STATUS_PENDING),
                        target_level="B1",
                    )
                )

    def test_only_one_active_analysis_per_user(
        self,
    ):
        create_analysis(
            user=self.user,
            resource=self.resource,
            status=(ReadingAnalysis.STATUS_PROCESSING),
        )

        second_resource = create_system_resource(index=2)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                create_analysis(
                    user=self.user,
                    resource=second_resource,
                    status=(ReadingAnalysis.STATUS_PENDING),
                )

    def test_completed_analysis_does_not_block_new_one(
        self,
    ):
        create_analysis(
            user=self.user,
            resource=self.resource,
            status=(ReadingAnalysis.STATUS_COMPLETED),
        )

        second_resource = create_system_resource(index=2)

        analysis = create_analysis(
            user=self.user,
            resource=second_resource,
            status=(ReadingAnalysis.STATUS_PENDING),
        )

        self.assertEqual(
            analysis.status,
            ReadingAnalysis.STATUS_PENDING,
        )

    def test_section_order_unique_per_analysis(
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
            title="First section",
            summary="",
            data={},
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                (
                    ReadingSection.objects.create(
                        analysis=analysis,
                        order=1,
                        title=("Duplicate section"),
                        summary="",
                        data={},
                    )
                )

    def test_same_order_allowed_for_different_analyses(
        self,
    ):
        other_user = create_user(index=2)

        other_resource = create_system_resource(index=2)

        first_analysis = create_analysis(
            user=self.user,
            resource=self.resource,
            status=(ReadingAnalysis.STATUS_PROCESSING),
        )

        second_analysis = create_analysis(
            user=other_user,
            resource=other_resource,
            status=(ReadingAnalysis.STATUS_PROCESSING),
        )

        first = ReadingSection.objects.create(
            analysis=first_analysis,
            order=1,
            title="Section",
            summary="",
            data={},
        )

        second = ReadingSection.objects.create(
            analysis=second_analysis,
            order=1,
            title="Section",
            summary="",
            data={},
        )

        self.assertNotEqual(
            first.analysis_id,
            second.analysis_id,
        )
