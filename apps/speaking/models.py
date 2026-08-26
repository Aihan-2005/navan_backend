import uuid

from django.conf import settings
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models

from apps.speaking.choices import (
    CefrLevel,
    SpeakingCoachStyle,
    SpeakingEvaluationStatus,
    SpeakingMode,
    SpeakingSessionStatus,
    SpeakingTranscriptionStatus,
    SpeakingTurnSpeaker,
)
from apps.speaking.validators import (
    StringListValidator,
)


class SpeakingTag(models.Model):
    name = models.CharField(
        max_length=50,
        unique=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class SpeakingExercise(models.Model):
    """
    A reusable speaking scenario/exercise.

    UUID is the internal database identity.
    `slug` is the stable public identifier
    exposed to frontend routes.
    """

    # Compatibility aliases for older code.
    ExerciseType = SpeakingMode
    CefrLevel = CefrLevel
    CoachingStyle = SpeakingCoachStyle

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    slug = models.SlugField(
        max_length=120,
        unique=True,
        null=True,
        blank=True,
    )

    title = models.CharField(
        max_length=200,
    )

    description = models.TextField()

    exercise_type = models.CharField(
        max_length=24,
        choices=SpeakingMode.choices,
    )

    cefr_level = models.CharField(
        max_length=2,
        choices=CefrLevel.choices,
    )

    coaching_style = models.CharField(
        max_length=20,
        choices=SpeakingCoachStyle.choices,
    )

    estimated_minutes = models.PositiveSmallIntegerField()

    prompt = models.TextField(
        blank=True,
        help_text=("Internal scenario instructions used to guide the speaking task."),
    )

    ai_role = models.CharField(
        max_length=500,
        blank=True,
        help_text=("Role and behavior expected from the AI conversation partner."),
    )

    starter_phrases = models.JSONField(
        default=list,
        blank=True,
        validators=[
            StringListValidator(
                max_items=12,
                max_item_length=180,
            )
        ],
    )

    tags = models.ManyToManyField(
        SpeakingTag,
        blank=True,
        related_name="exercises",
    )

    is_recommended = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    order = models.PositiveIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "order",
            "-created_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "exercise_type",
                    "is_active",
                ]
            ),
            models.Index(fields=["cefr_level"]),
            models.Index(
                fields=[
                    "is_active",
                    "is_recommended",
                ]
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(estimated_minutes__gte=1),
                name=("speaking_exercise_minutes_gte_1"),
            )
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.cefr_level})"


class SpeakingSession(models.Model):
    """
    A single learner speaking session.
    """

    Status = SpeakingSessionStatus

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="speaking_sessions",
    )

    exercise = models.ForeignKey(
        SpeakingExercise,
        on_delete=models.PROTECT,
        related_name="sessions",
    )

    status = models.CharField(
        max_length=20,
        choices=(SpeakingSessionStatus.choices),
        default=(SpeakingSessionStatus.IN_PROGRESS),
    )

    started_at = models.DateTimeField(
        auto_now_add=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    duration_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-started_at"]

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "status",
                ]
            ),
            models.Index(
                fields=[
                    "user",
                    "started_at",
                ]
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} · {self.exercise.title} · {self.status}"


class SpeakingTurn(models.Model):
    """
    One conversational turn.

    User turns may contain audio and require
    transcription. AI turns contain text only.
    """

    Speaker = SpeakingTurnSpeaker
    TranscriptionStatus = SpeakingTranscriptionStatus

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    session = models.ForeignKey(
        SpeakingSession,
        on_delete=models.CASCADE,
        related_name="turns",
    )

    speaker = models.CharField(
        max_length=10,
        choices=SpeakingTurnSpeaker.choices,
    )

    order = models.PositiveIntegerField()

    text = models.TextField(
        blank=True,
    )

    audio_file = models.FileField(
        upload_to="speaking/audio/%Y/%m/",
        null=True,
        blank=True,
    )

    audio_format = models.CharField(
        max_length=10,
        blank=True,
    )

    audio_size_bytes = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    audio_duration_seconds = models.FloatField(
        null=True,
        blank=True,
    )

    transcription_status = models.CharField(
        max_length=20,
        choices=(SpeakingTranscriptionStatus.choices),
        default=(SpeakingTranscriptionStatus.NOT_APPLICABLE),
    )

    transcription_raw = models.JSONField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "session",
            "order",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "session",
                    "order",
                ],
                name=("speaking_unique_session_turn_order"),
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(audio_duration_seconds__isnull=True)
                    | (
                        models.Q(audio_duration_seconds__gt=0)
                        & models.Q(audio_duration_seconds__lte=180)
                    )
                ),
                name=("speaking_turn_duration_valid"),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.session_id} · turn {self.order} · {self.speaker}"


class SpeakingEvaluation(models.Model):
    """
    Persisted evaluation generated after
    a completed speaking session.
    """

    Status = SpeakingEvaluationStatus

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    session = models.OneToOneField(
        SpeakingSession,
        on_delete=models.CASCADE,
        related_name="evaluation",
    )

    status = models.CharField(
        max_length=20,
        choices=(SpeakingEvaluationStatus.choices),
        default=(SpeakingEvaluationStatus.QUEUED),
    )

    score = models.FloatField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
    )

    fluency_score = models.FloatField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
    )

    pronunciation_score = models.FloatField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
    )

    grammar_score = models.FloatField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
    )

    vocabulary_score = models.FloatField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
    )

    analysis = models.JSONField(
        null=True,
        blank=True,
    )

    raw_response = models.JSONField(
        null=True,
        blank=True,
    )

    error_message = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Evaluation for {self.session_id} ({self.status})"
