from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AssessmentResult:
    fluency_score: float
    pronunciation_score: float
    grammar_score: float
    feedback: dict = field(default_factory=dict)


class BaseAssessmentProvider(ABC):
    @abstractmethod
    def assess_session(self, session) -> AssessmentResult:
        """session: a SpeakingSession instance with turns prefetched."""
        raise NotImplementedError


class FakeAssessmentProvider(BaseAssessmentProvider):
    def assess_session(self, session) -> AssessmentResult:
        return AssessmentResult(
            fluency_score=75.0,
            pronunciation_score=70.0,
            grammar_score=80.0,
            feedback={
                "summary": "Fake feedback — replace once the real assessment provider is wired in.",
                "corrections": [],
            },
        )


def get_assessment_provider() -> BaseAssessmentProvider:
    from django.conf import settings

    provider_name = getattr(settings, "SPEAKING_ASSESSMENT_PROVIDER", "fake")
    if provider_name == "fake":
        return FakeAssessmentProvider()
    raise NotImplementedError(f"Unknown assessment provider: {provider_name!r}")