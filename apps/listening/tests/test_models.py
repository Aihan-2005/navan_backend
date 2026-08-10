from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import (
    SimpleUploadedFile,
)

from apps.listening.choices import (
    CefrLevel,
    ListeningAccent,
    ListeningContentStatus,
    ListeningContentType,
    ListeningPracticeMode,
    ListeningSourceType,
)
from apps.listening.models import ListeningContent
from apps.listening.validators import (
    MAX_AUDIO_SIZE_BYTES,
    validate_audio_file_size,
)

pytestmark = pytest.mark.django_db


def build_content(
    **overrides: object,
) -> ListeningContent:
    values: dict[str, object] = {
        "title": "A day in London",
        "description": ("A short daily-routine podcast."),
        "content_type": (ListeningContentType.PODCAST),
        "source_type": (ListeningSourceType.PLATFORM),
        "cefr_level": CefrLevel.B1,
        "accent": ListeningAccent.BRITISH,
        "status": ListeningContentStatus.READY,
        "transcription_language": "en",
        "audio_file": SimpleUploadedFile(
            "sample.mp3",
            b"fake-audio-content",
            content_type="audio/mpeg",
        ),
        "duration_seconds": 284,
        "estimated_practice_minutes": 14,
        "average_words_per_minute": 128,
        "speaker_count": 1,
        "topics": [
            "daily life",
            "transport",
        ],
        "vocabulary_preview": [
            "commute",
            "neighborhood",
        ],
        "available_practice_modes": [
            ListeningPracticeMode.FULL_DICTATION,
            ListeningPracticeMode.GUIDED_DICTATION,
        ],
        "instructions": [
            "Listen once without pausing.",
        ],
        "hint_words": ["commute"],
        "minimum_transcript_words": 20,
        "reference_transcript": ("This is the reference transcript."),
        "is_published": True,
    }

    values.update(overrides)

    return ListeningContent(**values)


def test_platform_content_is_valid() -> None:
    content = build_content()

    content.full_clean()

    assert content.transcript_available is True
    assert content.owner is None


def test_user_upload_requires_an_owner() -> None:
    content = build_content(
        source_type=(ListeningSourceType.USER_UPLOAD),
        is_published=False,
    )

    with pytest.raises(
        ValidationError,
    ) as exc_info:
        content.full_clean()

    assert "owner" in exc_info.value.message_dict


def test_user_upload_with_owner_is_valid() -> None:
    user = get_user_model().objects.create_user(
        username="listener",
        password="strong-password",
    )

    content = build_content(
        owner=user,
        source_type=(ListeningSourceType.USER_UPLOAD),
        content_type=(ListeningContentType.CUSTOM),
        is_published=False,
    )

    content.full_clean()


def test_external_url_requires_source_url() -> None:
    user = get_user_model().objects.create_user(
        username="listener",
        password="strong-password",
    )

    content = build_content(
        owner=user,
        source_type=(ListeningSourceType.EXTERNAL_URL),
        audio_file=None,
        source_url="",
        is_published=False,
    )

    with pytest.raises(
        ValidationError,
    ) as exc_info:
        content.full_clean()

    assert "source_url" in exc_info.value.message_dict


def test_invalid_practice_mode_is_rejected() -> None:
    content = build_content(
        available_practice_modes=[
            "unsupported-mode",
        ]
    )

    with pytest.raises(
        ValidationError,
    ) as exc_info:
        content.full_clean()

    assert "available_practice_modes" in exc_info.value.message_dict


def test_audio_file_size_limit_matches_frontend_contract() -> None:
    oversized_file = SimpleNamespace(
        size=MAX_AUDIO_SIZE_BYTES + 1,
    )

    with pytest.raises(
        ValidationError,
    ) as exc_info:
        validate_audio_file_size(
            oversized_file,
        )

    assert exc_info.value.code == "audio_file_too_large"
