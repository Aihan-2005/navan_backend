from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class EvaluationResult:
    score: float | None
    analysis: list[dict]  # [{"title": str, "content": str}, ...]
    raw: dict = field(default_factory=dict)


class BaseEvaluationProvider(ABC):
    @abstractmethod
    def evaluate_session(self, session) -> EvaluationResult:
        """session: SpeakingSession with .turns prefetched. Real implementation
        should build a prompt that adapts to exercise.exercise_type and
        exercise.cefr_level — role/goals are fixed, specific content is left
        to the model, per the agreed design."""
        raise NotImplementedError


class FakeEvaluationProvider(BaseEvaluationProvider):
    def evaluate_session(self, session) -> EvaluationResult:
        return EvaluationResult(
            score=75.0,
            analysis=[
                {"title": "Grammar", "content": "[fake] A couple of minor tense slips were noted."},
                {
                    "title": "Vocabulary",
                    "content": "[fake] Try varying repeated words like 'good'.",
                },
                {
                    "title": "Fluency",
                    "content": "[fake] Speech was generally smooth with natural pausing.",
                },
            ],
            raw={"provider": "fake"},
        )


def get_evaluation_provider() -> BaseEvaluationProvider:
    from django.conf import settings

    provider_name = getattr(settings, "SPEAKING_EVALUATION_PROVIDER", "fake")
    if provider_name == "fake":
        return FakeEvaluationProvider()
    raise NotImplementedError(f"Unknown evaluation provider: {provider_name!r}")
