from rest_framework import serializers

from apps.reading.models import (
    ReadingAnalysis,
    ReadingResource,
    ReadingSection,
)


class ReadingAnalysisCreateSerializer(serializers.Serializer):
    RESOURCE_SYSTEM = "system"
    RESOURCE_USER = "user"

    RESOURCE_TYPE_CHOICES = [
        (
            RESOURCE_SYSTEM,
            "System resource",
        ),
        (
            RESOURCE_USER,
            "User resource",
        ),
    ]

    resource_type = serializers.ChoiceField(choices=RESOURCE_TYPE_CHOICES)

    resource_id = serializers.IntegerField(min_value=1)


class ReadingResourceSummarySerializer(serializers.Serializer):
    type = serializers.SerializerMethodField()

    id = serializers.IntegerField(read_only=True)

    title = serializers.CharField(read_only=True)

    category = serializers.CharField(read_only=True)

    author = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()

    def get_type(self, obj) -> str:
        if isinstance(obj, ReadingResource):
            return "system"

        return "user"

    def get_author(self, obj):
        return getattr(obj, "author", "") or None

    def get_level(self, obj):
        return getattr(
            obj,
            "level",
            None,
        )


class ReadingAnalysisSerializer(serializers.ModelSerializer):
    resource = serializers.SerializerMethodField()
    sections = serializers.SerializerMethodField()
    error = serializers.SerializerMethodField()

    class Meta:
        model = ReadingAnalysis

        fields = [
            "id",
            "status",
            "target_level",
            "detected_level",
            "progress_percent",
            "resource",
            "overview",
            "difficulty_profile",
            "vocabulary_profile",
            "quality_profile",
            "sections",
            "error",
            "queued_at",
            "started_at",
            "first_result_at",
            "completed_at",
        ]

        read_only_fields = fields

    def get_resource(self, obj):
        resource = obj.resource

        if resource is None:
            return None

        return ReadingResourceSummarySerializer(resource).data

    def get_sections(self, obj) -> dict:
        """
        source_chunks exist during processing.

        When analysis is completed they may be deleted,
        therefore total falls back to ready section count.
        """

        ready = getattr(
            obj,
            "ready_sections_count",
            None,
        )

        if ready is None:
            ready = obj.sections.count()

        source_chunks = getattr(
            obj,
            "source_chunks_count",
            None,
        )

        if source_chunks is None:
            source_chunks = obj.source_chunks.count()

        if source_chunks > 0:
            total = source_chunks
        else:
            total = ready

        return {
            "ready": ready,
            "total": total,
        }

    def get_error(self, obj):
        if not obj.error_code and not obj.error_message:
            return None

        return {
            "code": (obj.error_code or "READING_ANALYSIS_ERROR"),
            "message": (obj.error_message or "Reading analysis failed."),
        }


class ReadingSectionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadingSection

        fields = [
            "id",
            "order",
            "title",
            "summary",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class ReadingSectionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadingSection

        fields = [
            "id",
            "order",
            "title",
            "summary",
            "data",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields
