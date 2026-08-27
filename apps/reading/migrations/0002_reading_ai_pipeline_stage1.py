import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_reading_ai_fields(apps, schema_editor):
    ReadingAnalysis = apps.get_model(
        "reading",
        "ReadingAnalysis",
    )
    ReadingResource = apps.get_model(
        "reading",
        "ReadingResource",
    )
    ReadingSection = apps.get_model(
        "reading",
        "ReadingSection",
    )

    ReadingResource.objects.filter(
        level__isnull=True
    ).update(
        level=""
    )

    ReadingAnalysis.objects.filter(
        queued_at__isnull=True
    ).update(
        queued_at=models.F("started_at")
    )

    ReadingAnalysis.objects.filter(
        status="ACTIVE"
    ).update(
        status="COMPLETED",
        completed_at=models.F(
            "started_at"
        ),
    )

    duplicate_active_users = (
        ReadingAnalysis.objects
        .filter(
            status__in=[
                "PENDING",
                "PROCESSING",
            ]
        )
        .values(
            "user_id"
        )
        .annotate(
            total=models.Count("id")
        )
        .filter(
            total__gt=1
        )
    )

    for group in (
        duplicate_active_users.iterator()
    ):
        active_ids = list(
            ReadingAnalysis.objects
            .filter(
                user_id=group["user_id"],
                status__in=[
                    "PENDING",
                    "PROCESSING",
                ],
            )
            .order_by("-id")
            .values_list(
                "id",
                flat=True,
            )
        )

        stale_ids = active_ids[1:]

        if stale_ids:
            (
                ReadingAnalysis.objects
                .filter(
                    id__in=stale_ids
                )
                .update(
                    status="FAILED",
                    error_code=(
                        "MIGRATION_DUPLICATE_ACTIVE"
                    ),
                    error_message=(
                        "Marked failed while "
                        "enforcing one active "
                        "reading analysis per user."
                    ),
                    completed_at=models.F(
                        "started_at"
                    ),
                )
            )

    ReadingSection.objects.filter(
        updated_at__isnull=True
    ).update(
        updated_at=models.F(
            "created_at"
        )
    )

    duplicate_sections = (
        ReadingSection.objects
        .values(
            "analysis_id",
            "order",
        )
        .annotate(
            total=models.Count("id")
        )
        .filter(
            total__gt=1
        )
    )

    for group in (
        duplicate_sections.iterator()
    ):
        section_ids = list(
            ReadingSection.objects
            .filter(
                analysis_id=(
                    group["analysis_id"]
                ),
                order=group["order"],
            )
            .order_by("-id")
            .values_list(
                "id",
                flat=True,
            )
        )

        stale_ids = section_ids[1:]

        if stale_ids:
            (
                ReadingSection.objects
                .filter(
                    id__in=stale_ids
                )
                .delete()
            )


class Migration(migrations.Migration):
    dependencies = [
        (
            "reading",
            "0001_initial",
        ),
        migrations.swappable_dependency(
            settings.AUTH_USER_MODEL
        ),
    ]

    operations = [

        migrations.AlterField(
            model_name="readinganalysis",
            name="status",
            field=models.CharField(
                choices=[
                    (
                        "PENDING",
                        "Pending",
                    ),
                    (
                        "PROCESSING",
                        "Processing",
                    ),
                    (
                        "COMPLETED",
                        "Completed",
                    ),
                    (
                        "FAILED",
                        "Failed",
                    ),
                ],
                db_index=True,
                default="PENDING",
                max_length=20,
            ),
        ),

        migrations.AlterField(
            model_name="readinganalysis",
            name="user",
            field=models.ForeignKey(
                on_delete=(
                    django.db.models
                    .deletion.CASCADE
                ),
                related_name=(
                    "reading_analyses"
                ),
                to=settings.AUTH_USER_MODEL,
            ),
        ),

        migrations.AlterField(
            model_name="readinganalysis",
            name="system_resource",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=(
                    django.db.models
                    .deletion.CASCADE
                ),
                related_name="analyses",
                to="reading.readingresource",
            ),
        ),

        migrations.AlterField(
            model_name="readinganalysis",
            name="user_resource",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=(
                    django.db.models
                    .deletion.CASCADE
                ),
                related_name="analyses",
                to=(
                    "reading."
                    "userreadingresource"
                ),
            ),
        ),

        migrations.AddField(
            model_name="readinganalysis",
            name="target_level",
            field=models.CharField(
                choices=[
                    ("A1", "A1"),
                    ("A2", "A2"),
                    ("B1", "B1"),
                    ("B2", "B2"),
                    ("C1", "C1"),
                    ("C2", "C2"),
                ],
                default="B1",
                max_length=2,
            ),
        ),

        migrations.AddField(
            model_name="readinganalysis",
            name="detected_level",
            field=models.CharField(
                blank=True,
                choices=[
                    ("A1", "A1"),
                    ("A2", "A2"),
                    ("B1", "B1"),
                    ("B2", "B2"),
                    ("C1", "C1"),
                    ("C2", "C2"),
                ],
                default="",
                max_length=2,
            ),
        ),

        migrations.AddField(
            model_name="readinganalysis",
            name="progress_percent",
            field=(
                models.PositiveSmallIntegerField(
                    default=0
                )
            ),
        ),

        migrations.AddField(
            model_name="readinganalysis",
            name="overview",
            field=models.JSONField(
                blank=True,
                default=dict,
            ),
        ),

        migrations.AddField(
            model_name="readinganalysis",
            name="provider",
            field=models.CharField(
                blank=True,
                default="",
                max_length=32,
            ),
            preserve_default=False,
        ),

        migrations.AddField(
            model_name="readinganalysis",
            name="model_name",
            field=models.CharField(
                blank=True,
                default="",
                max_length=100,
            ),
            preserve_default=False,
        ),

        migrations.AddField(
            model_name="readinganalysis",
            name="prompt_version",
            field=models.CharField(
                blank=True,
                default="",
                max_length=50,
            ),
            preserve_default=False,
        ),

        migrations.AddField(
            model_name="readinganalysis",
            name="schema_version",
            field=models.CharField(
                blank=True,
                default="",
                max_length=50,
            ),
            preserve_default=False,
        ),

        migrations.AddField(
            model_name="readinganalysis",
            name="input_tokens",
            field=(
                models.PositiveBigIntegerField(
                    default=0
                )
            ),
        ),

        migrations.AddField(
            model_name="readinganalysis",
            name="output_tokens",
            field=(
                models.PositiveBigIntegerField(
                    default=0
                )
            ),
        ),

        migrations.AddField(
            model_name="readinganalysis",
            name="total_tokens",
            field=(
                models.PositiveBigIntegerField(
                    default=0
                )
            ),
        ),

        migrations.AddField(
            model_name="readinganalysis",
            name="error_code",
            field=models.CharField(
                blank=True,
                default="",
                max_length=64,
            ),
            preserve_default=False,
        ),

        migrations.AddField(
            model_name="readinganalysis",
            name="error_message",
            field=models.TextField(
                blank=True,
                default="",
            ),
            preserve_default=False,
        ),

        migrations.AddField(
            model_name="readinganalysis",
            name="queued_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
            ),
        ),

        migrations.AddField(
            model_name="readinganalysis",
            name="first_result_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
            ),
        ),

        migrations.AddField(
            model_name="readinganalysis",
            name="sections_dispatched_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
            ),
        ),

        migrations.AddField(
            model_name="readinganalysis",
            name="completed_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
            ),
        ),

        migrations.AlterField(
            model_name="readinganalysis",
            name="started_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
            ),
        ),

        migrations.AlterField(
            model_name="readingsection",
            name="data",
            field=models.JSONField(
                default=dict
            ),
        ),

        migrations.AddField(
            model_name="readingsection",
            name="updated_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
            ),
        ),

        migrations.CreateModel(
            name="ReadingSourceChunk",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "order",
                    models.PositiveIntegerField(),
                ),
                (
                    "text",
                    models.TextField(),
                ),
                (
                    "char_count",
                    models.PositiveIntegerField(
                        default=0
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True
                    ),
                ),
                (
                    "analysis",
                    models.ForeignKey(
                        on_delete=(
                            django.db.models
                            .deletion.CASCADE
                        ),
                        related_name=(
                            "source_chunks"
                        ),
                        to=(
                            "reading."
                            "readinganalysis"
                        ),
                    ),
                ),
            ],
            options={
                "ordering": [
                    "order",
                ],
            },
        ),

        migrations.RunPython(
            backfill_reading_ai_fields,
            migrations.RunPython.noop,
        ),


        migrations.AlterField(
            model_name="readingresource",
            name="level",
            field=models.CharField(
                blank=True,
                choices=[
                    ("A1", "A1"),
                    ("A2", "A2"),
                    ("B1", "B1"),
                    ("B2", "B2"),
                    ("C1", "C1"),
                    ("C2", "C2"),
                ],
                default="",
                max_length=2,
            ),
        ),


        migrations.AlterField(
            model_name="readinganalysis",
            name="queued_at",
            field=models.DateTimeField(
                auto_now_add=True
            ),
        ),

        migrations.AlterField(
            model_name="readingsection",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True
            ),
        ),


        migrations.AddConstraint(
            model_name="readinganalysis",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    status__in=[
                        "PENDING",
                        "PROCESSING",
                    ]
                ),
                fields=(
                    "user",
                ),
                name=(
                    "reading_one_active_"
                    "analysis_per_user"
                ),
            ),
        ),

        migrations.AddConstraint(
            model_name="readingsection",
            constraint=models.UniqueConstraint(
                fields=(
                    "analysis",
                    "order",
                ),
                name=(
                    "reading_section_"
                    "unique_order"
                ),
            ),
        ),

        migrations.AddConstraint(
            model_name="readingsourcechunk",
            constraint=models.UniqueConstraint(
                fields=(
                    "analysis",
                    "order",
                ),
                name=(
                    "reading_source_chunk_"
                    "unique_order"
                ),
            ),
        ),

        migrations.AddIndex(
            model_name="readinganalysis",
            index=models.Index(
                fields=[
                    "user",
                    "status",
                ],
                name=(
                    "reading_rea_"
                    "user_id_8ab520_idx"
                ),
            ),
        ),

        migrations.AddIndex(
            model_name="readinganalysis",
            index=models.Index(
                fields=[
                    "system_resource",
                    "status",
                ],
                name=(
                    "reading_rea_"
                    "system__5e558e_idx"
                ),
            ),
        ),

        migrations.AddIndex(
            model_name="readinganalysis",
            index=models.Index(
                fields=[
                    "user_resource",
                    "status",
                ],
                name=(
                    "reading_rea_"
                    "user_re_a6c339_idx"
                ),
            ),
        ),
    ]