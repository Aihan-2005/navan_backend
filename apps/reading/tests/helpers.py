import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import (
    SimpleUploadedFile,
)
from django.test import override_settings

from apps.reading.ai_client import (
    AIUsage,
    StructuredAIResult,
)
from apps.reading.models import (
    ReadingAnalysis,
    ReadingResource,
    UserReadingResource,
)
from apps.reading.schemas import (
    ReadingOverview,
    ReadingSectionAnalysis,
)


class TemporaryMediaMixin:
    """
    Use a temporary MEDIA_ROOT during tests.

    This prevents tests from writing files into the real
    development media directory.
    """

    @classmethod
    def setUpClass(cls):
        cls._temp_media = tempfile.TemporaryDirectory()

        cls._media_override = override_settings(MEDIA_ROOT=Path(cls._temp_media.name))

        cls._media_override.enable()

        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()

        finally:
            cls._media_override.disable()
            cls._temp_media.cleanup()


def create_user(
    *,
    index: int = 1,
    level: str = "B1",
):
    User = get_user_model()

    return User.objects.create_user(
        identifier=(f"reading-user-{index}@example.com"),
        name=(f"Reading User {index}"),
        password="StrongPass123!",
        level=level,
    )


def create_system_resource(
    *,
    index: int = 1,
) -> ReadingResource:
    return ReadingResource.objects.create(
        title=f"System Book {index}",
        author="Test Author",
        file=SimpleUploadedFile(
            f"system-book-{index}.txt",
            (b"This is a test reading document.\n\nThis is the second paragraph."),
            content_type="text/plain",
        ),
        level="B1",
        category="BOOK",
        description=("Reading test resource"),
    )


def create_user_resource(
    *,
    user,
    index: int = 1,
) -> UserReadingResource:
    return UserReadingResource.objects.create(
        user=user,
        title=f"User Book {index}",
        file=SimpleUploadedFile(
            f"user-book-{index}.txt",
            (b"This is a user uploaded reading document."),
            content_type="text/plain",
        ),
        category="BOOK",
    )


def create_analysis(
    *,
    user,
    resource,
    status: str = (ReadingAnalysis.STATUS_PENDING),
    target_level: str | None = None,
) -> ReadingAnalysis:
    kwargs = {
        "user": user,
        "status": status,
        "target_level": (target_level or user.level or "B1"),
        "provider": "openai",
        "model_name": "test-model",
        "prompt_version": ("test-prompt-v1"),
        "schema_version": ("test-schema-v1"),
    }

    if isinstance(
        resource,
        ReadingResource,
    ):
        kwargs["system_resource"] = resource

    elif isinstance(
        resource,
        UserReadingResource,
    ):
        kwargs["user_resource"] = resource

    else:
        raise TypeError("Unsupported reading resource.")

    return ReadingAnalysis.objects.create(**kwargs)


def build_overview_result() -> StructuredAIResult[ReadingOverview]:
    overview = ReadingOverview.model_validate(
        {
            "detected_level": "B1",
            "title_guess": "Test Book",
            "summary_fa": "خلاصه تست",
            "learning_objectives_fa": [
                "هدف اول",
                "هدف دوم",
            ],
            "difficulty_profile": {
                "cefr_level": "B1",
                "score": 5,
                "sentence_complexity": ("medium"),
                "grammar_complexity": ("medium"),
                "notes_fa": "متوسط",
            },
            "vocabulary_profile": {
                "cefr_level": "B1",
                "density": "MEDIUM",
                "notable_domains": [
                    "general",
                ],
                "notes_fa": ("واژگان متوسط"),
            },
            "quality_profile": {
                "readability": "GOOD",
                "coherence": "GOOD",
                "extraction_quality": ("GOOD"),
                "warnings_fa": [],
            },
        }
    )

    return StructuredAIResult(
        data=overview,
        usage=AIUsage(
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        ),
        request_id=("req-overview-test"),
    )


def build_section_result(
    *,
    title: str = "Section 1",
) -> StructuredAIResult[ReadingSectionAnalysis]:
    section = ReadingSectionAnalysis.model_validate(
        {
            "title": title,
            "summary_fa": ("خلاصه بخش تست"),
            "paragraphs": [],
            "quiz": [],
        }
    )

    return StructuredAIResult(
        data=section,
        usage=AIUsage(
            input_tokens=80,
            output_tokens=40,
            total_tokens=120,
        ),
        request_id=("req-section-test"),
    )
