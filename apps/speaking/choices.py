from django.db import models


class SpeakingMode(models.TextChoices):
    ROLEPLAY = "roleplay", "Roleplay"

    PRONUNCIATION = (
        "pronunciation",
        "Pronunciation",
    )

    SHADOWING = "shadowing", "Shadowing"

    QUICK_RESPONSE = (
        "quick_response",
        "Quick response",
    )

    STORYTELLING = (
        "storytelling",
        "Storytelling",
    )

    DEBATE = "debate", "Debate"

    # Kept temporarily for backward
    # compatibility with old local data.
    FREEFORM = "freeform", "Freeform (legacy)"


PUBLIC_SPEAKING_MODES = (
    SpeakingMode.ROLEPLAY,
    SpeakingMode.PRONUNCIATION,
    SpeakingMode.SHADOWING,
    SpeakingMode.QUICK_RESPONSE,
    SpeakingMode.STORYTELLING,
    SpeakingMode.DEBATE,
)


class CefrLevel(models.TextChoices):
    A1 = "A1", "A1"
    A2 = "A2", "A2"
    B1 = "B1", "B1"
    B2 = "B2", "B2"
    C1 = "C1", "C1"
    C2 = "C2", "C2"


class SpeakingCoachStyle(
    models.TextChoices,
):
    SUPPORTIVE = "supportive", "حمایتی"
    BALANCED = "balanced", "متعادل"
    STRICT = "strict", "سخت‌گیرانه"


class SpeakingDifficulty(
    models.TextChoices,
):
    BEGINNER = "beginner", "Beginner"

    INTERMEDIATE = (
        "intermediate",
        "Intermediate",
    )

    ADVANCED = "advanced", "Advanced"


class SpeakingSessionStatus(
    models.TextChoices,
):
    IN_PROGRESS = (
        "in_progress",
        "In progress",
    )

    COMPLETED = "completed", "Completed"

    ABANDONED = "abandoned", "Abandoned"


class SpeakingTurnSpeaker(
    models.TextChoices,
):
    AI = "ai", "AI"
    USER = "user", "User"


class SpeakingTranscriptionStatus(
    models.TextChoices,
):
    NOT_APPLICABLE = "n/a", "N/A"
    QUEUED = "queued", "Queued"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class SpeakingEvaluationStatus(
    models.TextChoices,
):
    QUEUED = "queued", "Queued"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
