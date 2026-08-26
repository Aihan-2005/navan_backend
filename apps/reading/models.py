from django.db import models
from django.conf import settings

RESOURCE_TYPE_CHOICES = [
    ("ARTICLE", "Article"),
    ("BOOK", "Book"),
    ("LESSON", "Lesson"),
    ("STORY", "Story"),
]


class ReadingResource(models.Model):
    CEFR_LEVEL_CHOICES = [
        ("A1", "A1"),
        ("A2", "A2"),
        ("B1", "B1"),
        ("B2", "B2"),
        ("C1", "C1"),
        ("C2", "C2"),
    ]
    title = models.CharField(max_length=255)

    author = models.CharField(max_length=255, blank=True)

    file = models.FileField(upload_to="reading/resources/")

    level = models.CharField(
        max_length=2, choices=CEFR_LEVEL_CHOICES, null=True, blank=True
    )

    category = models.CharField(max_length=100, choices=RESOURCE_TYPE_CHOICES)

    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


class UserReadingResource(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reading_uploads",
    )

    title = models.CharField(
        max_length=255,
    )

    file = models.FileField(
        upload_to="reading/user_resources/",
    )

    category = models.CharField(
        max_length=20,
        choices=RESOURCE_TYPE_CHOICES,
    )

    page_count = models.PositiveIntegerField(
        null=True,
        blank=True,
    )


class ReadingAnalysis(models.Model):

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    system_resource = models.ForeignKey(
        ReadingResource, null=True, blank=True, on_delete=models.CASCADE
    )

    user_resource = models.ForeignKey(
        UserReadingResource, null=True, blank=True, on_delete=models.CASCADE
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PROCESSING",
    )

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

    started_at = models.DateTimeField(
        auto_now_add=True,
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
                name="reading_analysis_exactly_one_resource",
            ),
        ]


class ReadingSection(models.Model):

    analysis = models.ForeignKey(
        ReadingAnalysis,
        on_delete=models.CASCADE,
        related_name="sections",
    )

    title = models.CharField(
        max_length=255,
    )

    summary = models.TextField(
        blank=True,
    )

    data = models.JSONField()

    order = models.PositiveIntegerField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class ReadingProgress(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reading_progresses",
    )

    system_resource = models.ForeignKey(
        ReadingResource, null=True, blank=True, on_delete=models.CASCADE
    )

    user_resource = models.ForeignKey(
        UserReadingResource, null=True, blank=True, on_delete=models.CASCADE
    )

    completed_sections = models.ManyToManyField(
        ReadingSection,
        blank=True,
        related_name="completed_by_users",
    )

    is_completed = models.BooleanField(
        default=False,
    )

    started_at = models.DateTimeField(
        auto_now_add=True,
    )

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
                name="reading_progress_exactly_one_resource",
            ),
        ]


class NotebookItem(models.Model):

    ITEM_TYPE_CHOICES = [
        ("VOCABULARY", "Vocabulary"),
        ("GRAMMAR", "Grammar"),
        ("PHRASE", "Phrase"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notebook_items",
    )

    system_resource = models.ForeignKey(
        ReadingResource, null=True, blank=True, on_delete=models.CASCADE
    )

    user_resource = models.ForeignKey(
        UserReadingResource, null=True, blank=True, on_delete=models.CASCADE
    )

    item_type = models.CharField(
        max_length=20,
        choices=ITEM_TYPE_CHOICES,
    )

    data = models.JSONField()

    created_at = models.DateTimeField(
        auto_now_add=True,
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
                name="reading_notebook_exactly_one_resource",
            ),
        ]


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

    duration = models.PositiveIntegerField(default=0, help_text="Duration in seconds")
