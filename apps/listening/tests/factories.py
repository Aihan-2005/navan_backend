from typing import Any

from django.contrib.auth import (
    get_user_model,
)

from apps.listening.choices import (
    CefrLevel,
    ListeningAccent,
    ListeningContentStatus,
    ListeningContentType,
    ListeningPracticeMode,
    ListeningSourceType,
)
from apps.listening.models import (
    ListeningContent,
)


def create_user(
    *,
    identifier: str = ("listener@example.com"),
    name: str = "Listener",
    password: str = "strong-password",
):
    return get_user_model().objects.create_user(
        identifier=identifier,
        name=name,
        password=password,
    )


def build_listening_content(
    **overrides: Any,
) -> ListeningContent:
    values: dict[str, Any] = {
        "title": "Daily life in London",
        "description": ("A short listening exercise."),
        "content_type": (ListeningContentType.PODCAST),
        "source_type": (ListeningSourceType.PLATFORM),
        "cefr_level": CefrLevel.B1,
        "accent": (ListeningAccent.BRITISH),
        "status": (ListeningContentStatus.READY),
        "transcription_language": "en",
        "audio_stream_url": ("https://cdn.example.com/listening/sample.mp3"),
        "duration_seconds": 180,
        "estimated_practice_minutes": 10,
        "average_words_per_minute": 120,
        "speaker_count": 1,
        "topics": [
            "daily life",
        ],
        "vocabulary_preview": [
            "commute",
        ],
        "available_practice_modes": [
            ListeningPracticeMode.FULL_DICTATION,
            ListeningPracticeMode.SHADOWING,
        ],
        "instructions": [
            "Listen before writing.",
        ],
        "hint_words": [
            "commute",
        ],
        "minimum_transcript_words": 20,
        "reference_transcript": ("This is the reference transcript."),
        "is_featured": False,
        "is_published": True,
    }

    values.update(overrides)

    return ListeningContent(**values)


def create_listening_content(
    **overrides: Any,
) -> ListeningContent:
    content = build_listening_content(**overrides)

    content.full_clean()
    content.save()

    return content
