from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models
from django.db.models import Q

from .choices import (
    CefrLevel,
    ListeningAccent,
    ListeningContentStatus,
    ListeningContentType,
    ListeningSourceType,
)
from .validators import (
    PracticeModesValidator,
    StringListValidator,
    validate_audio_file_size,
)

MAX_AUDIO_DURATION_SECONDS = 20 * 60

ALLOWED_AUDIO_EXTENSIONS = (
    "mp3",
    "wav",
    "m4a",
    "ogg",
    "webm",
)


def listening_audio_upload_to(
    instance: "ListeningContent",
    filename: str,
) -> str:
    extension = Path(filename).suffix.lower()

    owner_directory = str(instance.owner_id) if instance.owner_id else "platform"

    return f"listening/audio/{owner_directory}/{instance.id}{extension}"


class ListeningContentQuerySet(models.QuerySet):
    def published(
        self,
    ) -> "ListeningContentQuerySet":
        return self.filter(is_published=True)

    def ready(
        self,
    ) -> "ListeningContentQuerySet":
        return self.filter(
            status=ListeningContentStatus.READY,
        )

    def visible_to(
        self,
        user: object,
    ) -> "ListeningContentQuerySet":
        visibility_filter = Q(
            source_type=ListeningSourceType.PLATFORM,
            is_published=True,
        )

        if getattr(user, "is_authenticated", False):
            visibility_filter |= Q(owner=user)

        return self.filter(visibility_filter)


class ListeningContent(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid4,
        editable=False,
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listening_contents",
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    content_type = models.CharField(
        max_length=20,
        choices=ListeningContentType.choices,
    )

    source_type = models.CharField(
        max_length=20,
        choices=ListeningSourceType.choices,
        default=ListeningSourceType.PLATFORM,
    )

    cefr_level = models.CharField(
        max_length=2,
        choices=CefrLevel.choices,
    )

    accent = models.CharField(
        max_length=16,
        choices=ListeningAccent.choices,
        default=ListeningAccent.UNKNOWN,
    )

    status = models.CharField(
        max_length=16,
        choices=ListeningContentStatus.choices,
        default=ListeningContentStatus.PROCESSING,
    )

    transcription_language = models.CharField(
        max_length=10,
        default="en",
        validators=[
            RegexValidator(
                regex=r"^[a-z]{2}(?:-[A-Z]{2})?$",
                message=("Use a language code such as en or en-US."),
            )
        ],
    )

    # فایل صوتی ذخیره‌شده در storage پروژه
    audio_file = models.FileField(
        upload_to=listening_audio_upload_to,
        max_length=255,
        blank=True,
        validators=[
            FileExtensionValidator(
                ALLOWED_AUDIO_EXTENSIONS,
            ),
            validate_audio_file_size,
        ],
    )

    # لینک قابل پخش؛ برای CDN یا Object Storage
    audio_stream_url = models.URLField(
        max_length=2048,
        blank=True,
    )

    # لینکی که محتوای خارجی از آن import شده است
    source_url = models.URLField(
        max_length=2048,
        blank=True,
    )

    cover_image_url = models.URLField(
        max_length=2048,
        blank=True,
    )

    audio_attribution = models.TextField(
        blank=True,
    )

    duration_seconds = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(
                MAX_AUDIO_DURATION_SECONDS,
            ),
        ]
    )

    estimated_practice_minutes = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
    )

    average_words_per_minute = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )

    speaker_count = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )

    topics = models.JSONField(
        default=list,
        blank=True,
        validators=[
            StringListValidator(
                max_items=20,
                max_item_length=80,
            )
        ],
    )

    vocabulary_preview = models.JSONField(
        default=list,
        blank=True,
        validators=[
            StringListValidator(
                max_items=30,
                max_item_length=120,
            )
        ],
    )

    available_practice_modes = models.JSONField(
        default=list,
        validators=[PracticeModesValidator()],
    )

    instructions = models.JSONField(
        default=list,
        blank=True,
        validators=[
            StringListValidator(
                max_items=20,
                max_item_length=500,
            )
        ],
    )

    hint_words = models.JSONField(
        default=list,
        blank=True,
        validators=[
            StringListValidator(
                max_items=50,
                max_item_length=120,
            )
        ],
    )

    minimum_transcript_words = models.PositiveSmallIntegerField(
        default=20,
        validators=[MinValueValidator(1)],
    )

    # پاسخ صحیح برای مقایسه با Transcript کاربر
    # این فیلد مستقیم به فرانت ارسال نمی‌شود.
    reference_transcript = models.TextField(
        blank=True,
    )

    is_featured = models.BooleanField(
        default=False,
    )

    is_published = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    objects = ListeningContentQuerySet.as_manager()

    class Meta:
        db_table = "listening_contents"

        ordering = (
            "-is_featured",
            "cefr_level",
            "title",
        )

        indexes = [
            models.Index(
                fields=(
                    "is_published",
                    "status",
                    "cefr_level",
                ),
                name="listen_public_level_idx",
            ),
            models.Index(
                fields=(
                    "content_type",
                    "cefr_level",
                ),
                name="listen_type_level_idx",
            ),
            models.Index(
                fields=(
                    "owner",
                    "source_type",
                ),
                name="listen_owner_source_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(duration_seconds__gt=0)
                    & Q(duration_seconds__lte=(MAX_AUDIO_DURATION_SECONDS))
                ),
                name="listen_duration_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    estimated_practice_minutes__gt=0,
                ),
                name="listen_practice_minutes_gt_0",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        source_type=(ListeningSourceType.PLATFORM),
                        owner__isnull=True,
                    )
                    | (~Q(source_type=(ListeningSourceType.PLATFORM)) & Q(owner__isnull=False))
                ),
                name="listen_owner_matches_source",
            ),
            models.CheckConstraint(
                condition=(Q(is_published=False) | Q(source_type=(ListeningSourceType.PLATFORM))),
                name="listen_only_platform_published",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.cefr_level})"

    @property
    def transcript_available(self) -> bool:
        return bool(self.reference_transcript.strip())

    @property
    def audio_url(self) -> str | None:
        if self.audio_file:
            try:
                return self.audio_file.url
            except ValueError:
                return None

        return self.audio_stream_url or None

    def clean(self) -> None:
        super().clean()

        errors: dict[str, str] = {}

        if self.source_type == ListeningSourceType.PLATFORM and self.owner_id is not None:
            errors["owner"] = "Platform content cannot have an owner."

        if self.source_type != ListeningSourceType.PLATFORM and self.owner_id is None:
            errors["owner"] = "User-provided content must have an owner."

        if self.source_type == ListeningSourceType.USER_UPLOAD and not self.audio_file:
            errors["audio_file"] = "Uploaded content must include an audio file."

        if self.source_type == ListeningSourceType.EXTERNAL_URL and not self.source_url:
            errors["source_url"] = "External content must include its source URL."

        if self.status == ListeningContentStatus.READY and not self.audio_url:
            errors["status"] = "Ready content must have a playable audio source."

        if self.is_published and self.source_type != ListeningSourceType.PLATFORM:
            errors["is_published"] = "Only platform content can be published."

        if errors:
            raise ValidationError(errors)
