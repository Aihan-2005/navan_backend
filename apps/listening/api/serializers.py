from rest_framework import serializers

from apps.listening.choices import (
    CefrLevel,
    ListeningAccent,
    ListeningContentStatus,
    ListeningContentType,
    ListeningPracticeMode,
    ListeningSourceType,
)
from apps.listening.models import ListeningContent

LISTENING_ORDERING_CHOICES = (
    ("featured", "Featured first"),
    ("newest", "Newest first"),
    ("title", "Title"),
    ("shortest", "Shortest first"),
    ("longest", "Longest first"),
)


class ListeningContentFilterSerializer(
    serializers.Serializer,
):
    contentType = serializers.ChoiceField(
        choices=ListeningContentType.choices,
        required=False,
    )

    sourceType = serializers.ChoiceField(
        choices=ListeningSourceType.choices,
        required=False,
    )

    cefrLevel = serializers.ChoiceField(
        choices=CefrLevel.choices,
        required=False,
    )

    accent = serializers.ChoiceField(
        choices=ListeningAccent.choices,
        required=False,
    )

    status = serializers.ChoiceField(
        choices=ListeningContentStatus.choices,
        required=False,
    )

    practiceMode = serializers.ChoiceField(
        choices=ListeningPracticeMode.choices,
        required=False,
    )

    isFeatured = serializers.BooleanField(
        required=False,
    )

    search = serializers.CharField(
        required=False,
        allow_blank=False,
        trim_whitespace=True,
        max_length=100,
    )

    ordering = serializers.ChoiceField(
        choices=LISTENING_ORDERING_CHOICES,
        required=False,
        default="featured",
    )

    page = serializers.IntegerField(
        required=False,
        min_value=1,
    )

    pageSize = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=50,
    )


class ListeningContentSummarySerializer(
    serializers.ModelSerializer,
):
    description = serializers.SerializerMethodField()

    contentType = serializers.CharField(
        source="content_type",
        read_only=True,
    )

    sourceType = serializers.CharField(
        source="source_type",
        read_only=True,
    )

    cefrLevel = serializers.CharField(
        source="cefr_level",
        read_only=True,
    )

    durationSeconds = serializers.IntegerField(
        source="duration_seconds",
        read_only=True,
    )

    estimatedPracticeMinutes = serializers.IntegerField(
        source="estimated_practice_minutes",
        read_only=True,
    )

    averageWordsPerMinute = serializers.IntegerField(
        source="average_words_per_minute",
        read_only=True,
        allow_null=True,
    )

    speakerCount = serializers.IntegerField(
        source="speaker_count",
        read_only=True,
        allow_null=True,
    )

    topics = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )

    vocabularyPreview = serializers.ListField(
        child=serializers.CharField(),
        source="vocabulary_preview",
        read_only=True,
    )

    availablePracticeModes = serializers.ListField(
        child=serializers.ChoiceField(
            choices=ListeningPracticeMode.choices,
        ),
        source="available_practice_modes",
        read_only=True,
    )

    isFeatured = serializers.BooleanField(
        source="is_featured",
        read_only=True,
    )

    isCompleted = serializers.SerializerMethodField(
        method_name="get_is_completed",
    )

    bestAccuracyScore = serializers.SerializerMethodField(
        method_name="get_best_accuracy_score",
    )

    class Meta:
        model = ListeningContent

        fields = (
            "id",
            "title",
            "description",
            "contentType",
            "sourceType",
            "cefrLevel",
            "accent",
            "durationSeconds",
            "estimatedPracticeMinutes",
            "averageWordsPerMinute",
            "speakerCount",
            "topics",
            "vocabularyPreview",
            "availablePracticeModes",
            "status",
            "isFeatured",
            "isCompleted",
            "bestAccuracyScore",
        )

        read_only_fields = fields

    def get_description(
        self,
        obj: ListeningContent,
    ) -> str | None:
        description = obj.description.strip()
        return description or None

    def get_is_completed(
        self,
        obj: ListeningContent,
    ) -> bool:
        return bool(
            getattr(
                obj,
                "is_completed",
                False,
            )
        )

    def get_best_accuracy_score(
        self,
        obj: ListeningContent,
    ) -> float | None:
        score = getattr(
            obj,
            "best_accuracy_score",
            None,
        )

        if score is None:
            return None

        return float(score)


class ListeningContentDetailSerializer(
    ListeningContentSummarySerializer,
):
    audioUrl = serializers.SerializerMethodField(
        method_name="get_audio_url",
    )

    coverImageUrl = serializers.SerializerMethodField(
        method_name="get_cover_image_url",
    )

    transcriptionLanguage = serializers.CharField(
        source="transcription_language",
        read_only=True,
    )

    instructions = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )

    hintWords = serializers.ListField(
        child=serializers.CharField(),
        source="hint_words",
        read_only=True,
    )

    minimumTranscriptWords = serializers.IntegerField(
        source="minimum_transcript_words",
        read_only=True,
    )

    transcriptAvailable = serializers.BooleanField(
        source="transcript_available",
        read_only=True,
    )

    audioAttribution = serializers.SerializerMethodField(
        method_name="get_audio_attribution",
    )

    class Meta(
        ListeningContentSummarySerializer.Meta,
    ):
        fields = ListeningContentSummarySerializer.Meta.fields + (
            "audioUrl",
            "coverImageUrl",
            "transcriptionLanguage",
            "instructions",
            "hintWords",
            "minimumTranscriptWords",
            "transcriptAvailable",
            "audioAttribution",
        )

        read_only_fields = fields

    def get_audio_url(
        self,
        obj: ListeningContent,
    ) -> str:
        if obj.audio_file:
            try:
                file_url = obj.audio_file.url
            except ValueError:
                file_url = ""

            if file_url:
                request = self.context.get("request")

                if request is not None:
                    return request.build_absolute_uri(
                        file_url,
                    )

                return file_url

        return obj.audio_stream_url

    def get_cover_image_url(
        self,
        obj: ListeningContent,
    ) -> str | None:
        cover_image_url = obj.cover_image_url.strip()

        return cover_image_url or None

    def get_audio_attribution(
        self,
        obj: ListeningContent,
    ) -> str | None:
        attribution = obj.audio_attribution.strip()

        return attribution or None
