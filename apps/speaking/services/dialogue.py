from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class DialogueTurnResult:
    text: str
    is_conversation_complete: bool = False
    raw: dict = field(default_factory=dict)


class BaseDialogueProvider(ABC):
    @abstractmethod
    def generate_opening_turn(self, exercise) -> DialogueTurnResult:
        raise NotImplementedError

    @abstractmethod
    def generate_next_turn(self, session) -> DialogueTurnResult:
        """session: SpeakingSession with .turns prefetched, ordered by `order`.
        Real implementation builds conversation history from session.turns."""
        raise NotImplementedError


class FakeDialogueProvider(BaseDialogueProvider):
    def generate_opening_turn(self, exercise) -> DialogueTurnResult:
        return DialogueTurnResult(
            text=f"[fake AI prompt] Let's begin: {exercise.title}. {exercise.description}",
            raw={"provider": "fake"},
        )

    def generate_next_turn(self, session) -> DialogueTurnResult:
        turn_count = session.turns.count()
        return DialogueTurnResult(
            text=f"[fake AI reply] (turn {turn_count}) That's interesting — tell me more.",
            raw={"provider": "fake"},
        )


def get_dialogue_provider() -> BaseDialogueProvider:
    from django.conf import settings

    provider_name = getattr(settings, "SPEAKING_DIALOGUE_PROVIDER", "fake")
    if provider_name == "fake":
        return FakeDialogueProvider()
    raise NotImplementedError(f"Unknown dialogue provider: {provider_name!r}")