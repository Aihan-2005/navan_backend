from django.contrib import admin

from .models import ListeningContent


@admin.register(ListeningContent)
class ListeningContentAdmin(
    admin.ModelAdmin,
):
    list_display = (
        "title",
        "content_type",
        "cefr_level",
        "accent",
        "source_type",
        "status",
        "is_featured",
        "is_published",
        "updated_at",
    )

    list_filter = (
        "content_type",
        "cefr_level",
        "accent",
        "source_type",
        "status",
        "is_featured",
        "is_published",
    )

    search_fields = (
        "title",
        "description",
        "reference_transcript",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    autocomplete_fields = ("owner",)
    ordering = ("-updated_at",)

    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "id",
                    "owner",
                    "title",
                    "description",
                    "content_type",
                    "source_type",
                )
            },
        ),
        (
            "Learning metadata",
            {
                "fields": (
                    "cefr_level",
                    "accent",
                    "transcription_language",
                    "topics",
                    "vocabulary_preview",
                    "available_practice_modes",
                    "instructions",
                    "hint_words",
                    "minimum_transcript_words",
                )
            },
        ),
        (
            "Media",
            {
                "fields": (
                    "audio_file",
                    "audio_stream_url",
                    "source_url",
                    "cover_image_url",
                    "audio_attribution",
                    "duration_seconds",
                    "estimated_practice_minutes",
                    "average_words_per_minute",
                    "speaker_count",
                )
            },
        ),
        (
            "Reference answer",
            {
                "fields": ("reference_transcript",),
                "classes": ("collapse",),
            },
        ),
        (
            "Publishing",
            {
                "fields": (
                    "status",
                    "is_featured",
                    "is_published",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )
