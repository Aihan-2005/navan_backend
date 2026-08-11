from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.core.exceptions import (
    ValidationError,
)
from django.core.files.uploadedfile import (
    SimpleUploadedFile,
)

from apps.listening.choices import (
    ListeningAttemptStatus,
    ListeningContentType,
    ListeningPracticeMode,
    ListeningSourceType,
)
from apps.listening.models import (
    ListeningAttempt,
)
from apps.listening.tests.factories import (
    build_listening_content,
    create_listening_content,
    create_user,
)
from apps.listening.validators import (
    MAX_AUDIO_SIZE_BYTES,
    validate_audio_file_size,
)

pytestmark = pytest.mark.django_db


def test_platform_content_is_valid() -> None:
    content = build_listening_content()

    content.full_clean()

    assert content.transcript_available is True
    assert content.owner is None


def test_user_upload_requires_an_owner() -> None:
    content = build_listening_content(
        source_type=(ListeningSourceType.USER_UPLOAD),
        is_published=False,
    )

    with pytest.raises(
        ValidationError,
    ) as exc_info:
        content.full_clean()

    assert "owner" in exc_info.value.message_dict


def test_user_upload_with_owner_is_valid() -> None:
    user = create_user()

    content = build_listening_content(
        owner=user,
        source_type=(ListeningSourceType.USER_UPLOAD),
        content_type=(ListeningContentType.CUSTOM),
        audio_stream_url="",
        audio_file=SimpleUploadedFile(
            "sample.mp3",
            b"fake-audio-content",
            content_type="audio/mpeg",
        ),
        is_published=False,
    )

    content.full_clean()


def test_external_url_requires_source_url() -> None:
    user = create_user()

    content = build_listening_content(
        owner=user,
        source_type=(ListeningSourceType.EXTERNAL_URL),
        content_type=(ListeningContentType.CUSTOM),
        source_url="",
        is_published=False,
    )

    with pytest.raises(
        ValidationError,
    ) as exc_info:
        content.full_clean()

    assert "source_url" in exc_info.value.message_dict


def test_invalid_practice_mode_is_rejected() -> None:
    content = build_listening_content(
        available_practice_modes=[
            "unsupported-mode",
        ],
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
        validate_audio_file_size(oversized_file)

    assert exc_info.value.code == "audio_file_too_large"


def test_attempt_accepts_available_practice_mode() -> None:
    user = create_user()
    content = create_listening_content()

    attempt = ListeningAttempt(
        user=user,
        content=content,
        practice_mode=(ListeningPracticeMode.FULL_DICTATION),
    )

    attempt.full_clean()

    assert attempt.status == ListeningAttemptStatus.DRAFT

    assert attempt.current_position_seconds == Decimal("0")


def test_attempt_rejects_unavailable_practice_mode() -> None:
    user = create_user()

    content = create_listening_content(
        available_practice_modes=[
            ListeningPracticeMode.SHADOWING,
        ],
    )

    attempt = ListeningAttempt(
        user=user,
        content=content,
        practice_mode=(ListeningPracticeMode.FULL_DICTATION),
    )

    with pytest.raises(
        ValidationError,
    ) as exc_info:
        attempt.full_clean()

    assert "practice_mode" in exc_info.value.message_dict


def test_attempt_rejects_position_past_audio_duration() -> None:
    user = create_user()

    content = create_listening_content(
        duration_seconds=60,
    )

    attempt = ListeningAttempt(
        user=user,
        content=content,
        practice_mode=(ListeningPracticeMode.FULL_DICTATION),
        current_position_seconds=(Decimal("61")),
    )

    with pytest.raises(
        ValidationError,
    ) as exc_info:
        attempt.full_clean()

    assert "current_position_seconds" in exc_info.value.message_dict
