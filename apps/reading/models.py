from django.conf import settings
from django.db import models

RESOURCE_TYPE_CHOICES = [
    ("ARTICLE", "Article"),
    ("BOOK", "Book"),
    ("LESSON", "Lesson"),
    ("STORY", "Story"),
]


CEFR_LEVEL_CHOICES = [
    ("A1", "A1"),
    ("A2", "A2"),
    ("B1", "B1"),
    ("B2", "B2"),
    ("C1", "C1"),
    ("C2", "C2"),
]


class ReadingResource(models.Model):
    CEFR_LEVEL_CHOICES = CEFR_LEVEL_CHOICES

    title = models.CharField(max_length=255)

    author = models.CharField(
        max_length=255,
        blank=True,
    )

    file = models.FileField(upload_to="reading/resources/")

    level = models.CharField(
        max_length=2,
        choices=CEFR_LEVEL_CHOICES,
        blank=True,
        default="",
    )

    category = models.CharField(
        max_length=100,
        choices=RESOURCE_TYPE_CHOICES,
    )

    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class UserReadingResource(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reading_uploads",
    )

    title = models.CharField(max_length=255)

    file = models.FileField(upload_to="reading/user_resources/")

    category = models.CharField(
        max_length=20,
        choices=RESOURCE_TYPE_CHOICES,
    )

    page_count = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.title


class ReadingAnalysis(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_PROCESSING = "PROCESSING"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_FAILED = "FAILED"

    STATUS_CHOICES = [
        (
            STATUS_PENDING,
            "Pending",
        ),
        (
            STATUS_PROCESSING,
            "Processing",
        ),
        (
            STATUS_COMPLETED,
            "Completed",
        ),
        (
            STATUS_FAILED,
            "Failed",
        ),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reading_analyses",
    )

    system_resource = models.ForeignKey(
        ReadingResource,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="analyses",
    )

    user_resource = models.ForeignKey(
        UserReadingResource,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="analyses",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )

    target_level = models.CharField(
        max_length=2,
        choices=CEFR_LEVEL_CHOICES,
        default="B1",
    )

    detected_level = models.CharField(
        max_length=2,
        choices=CEFR_LEVEL_CHOICES,
        blank=True,
        default="",
    )

    progress_percent = models.PositiveSmallIntegerField(default=0)

    difficulty_profile = models.JSONField(
        default=dict,
        blank=True,
    )

    vocabulary_profile = models.JSONField(
        default=dict,
        blank=True,
    )

    quality_profile = models.JSONField(
        default=dict,
        blank=True,
    )

    overview = models.JSONField(
        default=dict,
        blank=True,
    )

    provider = models.CharField(
        max_length=32,
        blank=True,
    )

    model_name = models.CharField(
        max_length=100,
        blank=True,
    )

    prompt_version = models.CharField(
        max_length=50,
        blank=True,
    )

    schema_version = models.CharField(
        max_length=50,
        blank=True,
    )

    input_tokens = models.PositiveBigIntegerField(default=0)

    output_tokens = models.PositiveBigIntegerField(default=0)

    total_tokens = models.PositiveBigIntegerField(default=0)

    error_code = models.CharField(
        max_length=64,
        blank=True,
    )

    error_message = models.TextField(blank=True)

    queued_at = models.DateTimeField(auto_now_add=True)

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    first_result_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    sections_dispatched_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        system_resource__isnull=False,
                        user_resource__isnull=True,
                    )
                    | models.Q(
                        system_resource__isnull=True,
                        user_resource__isnull=False,
                    )
                ),
                name=("reading_analysis_exactly_one_resource"),
            ),
            models.UniqueConstraint(
                fields=[
                    "user",
                ],
                condition=models.Q(
                    status__in=[
                        "PENDING",
                        "PROCESSING",
                    ]
                ),
                name=("reading_one_active_analysis_per_user"),
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "status",
                ]
            ),
            models.Index(
                fields=[
                    "system_resource",
                    "status",
                ]
            ),
            models.Index(
                fields=[
                    "user_resource",
                    "status",
                ]
            ),
        ]

    def __str__(self):
        return f"ReadingAnalysis<{self.pk}> {self.status}"

    @property
    def resource(self):
        return self.system_resource or self.user_resource


class ReadingSourceChunk(models.Model):
    analysis = models.ForeignKey(
        ReadingAnalysis,
        on_delete=models.CASCADE,
        related_name="source_chunks",
    )

    order = models.PositiveIntegerField()

    text = models.TextField()

    char_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = [
            "order",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "analysis",
                    "order",
                ],
                name=("reading_source_chunk_unique_order"),
            )
        ]

    def __str__(self):
        return f"Chunk {self.order} for analysis {self.analysis_id}"


class ReadingSection(models.Model):
    analysis = models.ForeignKey(
        ReadingAnalysis,
        on_delete=models.CASCADE,
        related_name="sections",
    )

    title = models.CharField(max_length=255)

    summary = models.TextField(blank=True)

    data = models.JSONField(default=dict)

    order = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [
            "order",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "analysis",
                    "order",
                ],
                name=("reading_section_unique_order"),
            )
        ]

    def __str__(self):
        return self.title


class ReadingProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reading_progresses",
    )

    system_resource = models.ForeignKey(
        ReadingResource,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    user_resource = models.ForeignKey(
        UserReadingResource,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    completed_sections = models.ManyToManyField(
        ReadingSection,
        blank=True,
        related_name=("completed_by_users"),
    )

    is_completed = models.BooleanField(default=False)

    started_at = models.DateTimeField(auto_now_add=True)

    finished_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        system_resource__isnull=False,
                        user_resource__isnull=True,
                    )
                    | models.Q(
                        system_resource__isnull=True,
                        user_resource__isnull=False,
                    )
                ),
                name=("reading_progress_exactly_one_resource"),
            ),
        ]

    def __str__(self):
        return f"ReadingProgress<{self.pk}> user={self.user_id}"


class NotebookItem(models.Model):
    ITEM_TYPE_CHOICES = [
        (
            "VOCABULARY",
            "Vocabulary",
        ),
        (
            "GRAMMAR",
            "Grammar",
        ),
        (
            "PHRASE",
            "Phrase",
        ),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notebook_items",
    )

    system_resource = models.ForeignKey(
        ReadingResource,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    user_resource = models.ForeignKey(
        UserReadingResource,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    item_type = models.CharField(
        max_length=20,
        choices=ITEM_TYPE_CHOICES,
    )

    data = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        system_resource__isnull=False,
                        user_resource__isnull=True,
                    )
                    | models.Q(
                        system_resource__isnull=True,
                        user_resource__isnull=False,
                    )
                ),
                name=("reading_notebook_exactly_one_resource"),
            ),
        ]

    def __str__(self):
        return f"NotebookItem<{self.pk}> {self.item_type}"


class ReadingSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    progress = models.ForeignKey(
        ReadingProgress,
        on_delete=models.CASCADE,
        related_name="sessions",
    )

    started_at = models.DateTimeField()

    ended_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    duration = models.PositiveIntegerField(
        default=0,
        help_text="Duration in seconds",
    )

    def __str__(self):
        return f"ReadingSession<{self.pk}> user={self.user_id}"
