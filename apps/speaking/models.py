import uuid

from django.conf import settings
from django.db import models


class SpeakingTag(models.Model):
    """Skill tags shown as pills on exercise cards, e.g. 'ریتم', 'استرس کلمه'."""
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class SpeakingExercise(models.Model):
    """Catalog entry / template — the cards on the speaking page."""

    class ExerciseType(models.TextChoices):
        ROLEPLAY = "roleplay", "Roleplay"
        FREEFORM = "freeform", "Freeform"
        STORYTELLING = "storytelling", "Storytelling"
        SHADOWING = "shadowing", "Shadowing"
        PRONUNCIATION = "pronunciation", "Pronunciation Drill"

    class CefrLevel(models.TextChoices):
        A1 = "A1", "A1"
        A2 = "A2", "A2"
        B1 = "B1", "B1"
        B2 = "B2", "B2"
        C1 = "C1", "C1"
        C2 = "C2", "C2"

    class CoachingStyle(models.TextChoices):
        SUPPORTIVE = "supportive", "حمایتی"
        BALANCED = "balanced", "متعادل"
        STRICT = "strict", "سخت‌گیرانه"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    exercise_type = models.CharField(max_length=20, choices=ExerciseType.choices)
    cefr_level = models.CharField(max_length=2, choices=CefrLevel.choices)
    coaching_style = models.CharField(max_length=20, choices=CoachingStyle.choices)
    estimated_minutes = models.PositiveSmallIntegerField()
    tags = models.ManyToManyField(SpeakingTag, blank=True, related_name="exercises")
    is_recommended = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "-created_at"]
        indexes = [
            models.Index(fields=["exercise_type", "is_active"]),
            models.Index(fields=["cefr_level"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.cefr_level})"


class SpeakingSession(models.Model):
    """One user's attempt at an exercise. Holds multiple turns."""

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        ABANDONED = "abandoned", "Abandoned"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="speaking_sessions"
    )
    exercise = models.ForeignKey(
        SpeakingExercise, on_delete=models.PROTECT, related_name="sessions"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IN_PROGRESS
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    # Filled in once assessment runs on completion
    fluency_score = models.FloatField(null=True, blank=True)
    pronunciation_score = models.FloatField(null=True, blank=True)
    grammar_score = models.FloatField(null=True, blank=True)
    feedback = models.JSONField(null=True, blank=True)  # structured AI feedback

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["user", "started_at"]),
        ]

    def __str__(self):
        return f"{self.user_id} · {self.exercise.title} · {self.status}"


class SpeakingTurn(models.Model):
    """A single turn in a session's conversation (AI prompt or user reply)."""

    class Speaker(models.TextChoices):
        AI = "ai", "AI"
        USER = "user", "User"

    class TranscriptionStatus(models.TextChoices):
        NOT_APPLICABLE = "n/a", "N/A"  # AI turns don't need transcription
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        SpeakingSession, on_delete=models.CASCADE, related_name="turns"
    )
    speaker = models.CharField(max_length=10, choices=Speaker.choices)
    order = models.PositiveIntegerField()
    text = models.TextField(blank=True)  # AI prompt text, or user's transcript
    audio_file = models.FileField(upload_to="speaking/audio/%Y/%m/", null=True, blank=True)
    audio_duration_seconds = models.FloatField(null=True, blank=True)
    transcription_status = models.CharField(
        max_length=20,
        choices=TranscriptionStatus.choices,
        default=TranscriptionStatus.NOT_APPLICABLE,
    )
    transcription_raw = models.JSONField(null=True, blank=True)  # raw provider response
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["session", "order"]
        unique_together = [["session", "order"]]

    def __str__(self):
        return f"{self.session_id} · turn {self.order} · {self.speaker}"