from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    text: str
    confidence: float | None = None
    raw: dict | None = None


class BaseTranscriptionProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_file, language: str = "en") -> TranscriptionResult:
        """audio_file: a Django FieldFile / file-like object."""
        raise NotImplementedError


class FakeTranscriptionProvider(BaseTranscriptionProvider):
    """Stand-in until the real STT provider is wired in. Deterministic, no network calls."""

    def transcribe(self, audio_file, language: str = "en") -> TranscriptionResult:
        return TranscriptionResult(
            text="[fake transcription] This is a placeholder response for local testing.",
            confidence=1.0,
            raw={"provider": "fake"},
        )


def get_transcription_provider() -> BaseTranscriptionProvider:
    from django.conf import settings

    provider_name = getattr(settings, "SPEAKING_TRANSCRIPTION_PROVIDER", "fake")
    if provider_name == "fake":
        return FakeTranscriptionProvider()
    raise NotImplementedError(f"Unknown transcription provider: {provider_name!r}")