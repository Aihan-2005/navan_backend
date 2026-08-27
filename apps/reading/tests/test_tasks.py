from unittest.mock import patch

from django.test import (
    TestCase,
    override_settings,
)

from apps.reading.chunking import (
    TextChunk,
)
from apps.reading.extractors import (
    ExtractedDocument,
)
from apps.reading.models import (
    ReadingAnalysis,
    ReadingSection,
    ReadingSourceChunk,
)
from apps.reading.tasks import (
    analyze_reading_chunk,
    finalize_reading_analysis,
    prepare_reading_analysis,
)

from .helpers import (
    TemporaryMediaMixin,
    build_overview_result,
    build_section_result,
    create_analysis,
    create_system_resource,
    create_user,
)


@override_settings(
    READING_AI_CHUNK_TARGET_CHARS=1000,
    READING_AI_CHUNK_MAX_CHARS=1500,
    READING_AI_MAX_CHUNKS=10,
    READING_AI_KEEP_SOURCE_CHUNKS=False,
)
class ReadingTaskTests(
    TemporaryMediaMixin,
    TestCase,
):
    def setUp(self):
        self.user = create_user(index=1)

        self.resource = create_system_resource(index=1)

    @patch("apps.reading.tasks.chord")
    @patch("apps.reading.tasks.analyze_reading_overview")
    @patch("apps.reading.tasks.chunk_text")
    @patch("apps.reading.tasks.extract_reading_document")
    def test_prepare_analysis(
        self,
        mock_extract,
        mock_chunk_text,
        mock_overview,
        mock_chord,
    ):
        analysis = create_analysis(
            user=self.user,
            resource=self.resource,
            status=(ReadingAnalysis.STATUS_PENDING),
        )

        mock_extract.return_value = ExtractedDocument(
            text="Document text",
            page_count=None,
        )

        mock_chunk_text.return_value = [
            TextChunk(
                order=1,
                text="Chunk one",
            ),
            TextChunk(
                order=2,
                text="Chunk two",
            ),
        ]

        mock_overview.return_value = build_overview_result()

        result = prepare_reading_analysis.run(analysis.id)

        self.assertTrue(result["ok"])

        self.assertEqual(
            result["chunks"],
            2,
        )

        analysis.refresh_from_db()

        self.assertEqual(
            analysis.status,
            ReadingAnalysis.STATUS_PROCESSING,
        )

        self.assertEqual(
            analysis.detected_level,
            "B1",
        )

        self.assertEqual(
            analysis.progress_percent,
            15,
        )

        self.assertEqual(
            analysis.total_tokens,
            150,
        )

        self.assertEqual(
            analysis.overview["title_guess"],
            "Test Book",
        )

        self.assertIsNotNone(analysis.sections_dispatched_at)

        self.assertEqual(
            analysis.source_chunks.count(),
            2,
        )

        mock_chord.assert_called_once()
        mock_chord.return_value.assert_called_once()

    def test_missing_file_marks_failed(
        self,
    ):
        self.resource.file.delete(save=False)

        self.resource.file = ""

        self.resource.save(update_fields=["file"])

        analysis = create_analysis(
            user=self.user,
            resource=self.resource,
            status=(ReadingAnalysis.STATUS_PENDING),
        )

        result = prepare_reading_analysis.run(analysis.id)

        analysis.refresh_from_db()

        self.assertFalse(result["ok"])

        self.assertEqual(
            result["reason"],
            "resource_file_missing",
        )

        self.assertEqual(
            analysis.status,
            ReadingAnalysis.STATUS_FAILED,
        )

        self.assertEqual(
            analysis.error_code,
            "RESOURCE_FILE_MISSING",
        )

    @patch("apps.reading.tasks.analyze_reading_section")
    def test_chunk_creates_section(
        self,
        mock_ai,
    ):
        analysis = create_analysis(
            user=self.user,
            resource=self.resource,
            status=(ReadingAnalysis.STATUS_PROCESSING),
        )

        chunk = ReadingSourceChunk.objects.create(
            analysis=analysis,
            order=1,
            text="Chunk text",
            char_count=10,
        )

        mock_ai.return_value = build_section_result(title="AI Section")

        result = analyze_reading_chunk.run(chunk.id)

        self.assertTrue(result["ok"])

        self.assertFalse(result["reused"])

        section = ReadingSection.objects.get(
            analysis=analysis,
            order=1,
        )

        self.assertEqual(
            section.title,
            "AI Section",
        )

        self.assertEqual(
            section.summary,
            "خلاصه بخش تست",
        )

        analysis.refresh_from_db()

        self.assertEqual(
            analysis.total_tokens,
            120,
        )

        self.assertEqual(
            analysis.progress_percent,
            95,
        )

        self.assertIsNotNone(analysis.first_result_at)

    @patch("apps.reading.tasks.analyze_reading_section")
    def test_chunk_is_idempotent(
        self,
        mock_ai,
    ):
        analysis = create_analysis(
            user=self.user,
            resource=self.resource,
            status=(ReadingAnalysis.STATUS_PROCESSING),
        )

        chunk = ReadingSourceChunk.objects.create(
            analysis=analysis,
            order=1,
            text="Chunk text",
            char_count=10,
        )

        existing = ReadingSection.objects.create(
            analysis=analysis,
            order=1,
            title="Existing",
            summary="Already done",
            data={},
        )

        result = analyze_reading_chunk.run(chunk.id)

        self.assertTrue(result["ok"])

        self.assertTrue(result["reused"])

        self.assertEqual(
            result["section_id"],
            existing.id,
        )

        mock_ai.assert_not_called()

        self.assertEqual(
            ReadingSection.objects.filter(analysis=analysis).count(),
            1,
        )

    def test_finalize_success(
        self,
    ):
        analysis = create_analysis(
            user=self.user,
            resource=self.resource,
            status=(ReadingAnalysis.STATUS_PROCESSING),
        )

        for order in (1, 2):
            (
                ReadingSourceChunk.objects.create(
                    analysis=analysis,
                    order=order,
                    text=f"Chunk {order}",
                    char_count=7,
                )
            )

            ReadingSection.objects.create(
                analysis=analysis,
                order=order,
                title=f"Section {order}",
                summary="",
                data={},
            )

        result = finalize_reading_analysis.run(
            [
                {
                    "ok": True,
                    "order": 1,
                },
                {
                    "ok": True,
                    "order": 2,
                },
            ],
            analysis.id,
        )

        self.assertTrue(result["ok"])

        analysis.refresh_from_db()

        self.assertEqual(
            analysis.status,
            ReadingAnalysis.STATUS_COMPLETED,
        )

        self.assertEqual(
            analysis.progress_percent,
            100,
        )

        self.assertIsNotNone(analysis.completed_at)

        self.assertEqual(
            analysis.source_chunks.count(),
            0,
        )

    def test_finalize_failure(
        self,
    ):
        analysis = create_analysis(
            user=self.user,
            resource=self.resource,
            status=(ReadingAnalysis.STATUS_PROCESSING),
        )

        result = finalize_reading_analysis.run(
            [
                {
                    "ok": False,
                    "error_code": ("AI_INVALID_RESPONSE"),
                    "error_message": ("Bad structured output"),
                }
            ],
            analysis.id,
        )

        self.assertFalse(result["ok"])

        analysis.refresh_from_db()

        self.assertEqual(
            analysis.status,
            ReadingAnalysis.STATUS_FAILED,
        )

        self.assertEqual(
            analysis.error_code,
            "AI_INVALID_RESPONSE",
        )

    def test_finalize_detects_count_mismatch(
        self,
    ):
        analysis = create_analysis(
            user=self.user,
            resource=self.resource,
            status=(ReadingAnalysis.STATUS_PROCESSING),
        )

        ReadingSourceChunk.objects.create(
            analysis=analysis,
            order=1,
            text="Chunk 1",
            char_count=7,
        )

        result = finalize_reading_analysis.run(
            [
                {
                    "ok": True,
                    "order": 1,
                }
            ],
            analysis.id,
        )

        self.assertFalse(result["ok"])

        analysis.refresh_from_db()

        self.assertEqual(
            analysis.status,
            ReadingAnalysis.STATUS_FAILED,
        )

        self.assertEqual(
            analysis.error_code,
            "SECTION_COUNT_MISMATCH",
        )
