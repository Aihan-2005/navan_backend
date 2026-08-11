from decimal import Decimal

from rest_framework import serializers

from apps.listening.choices import (
    CefrLevel,
    ListeningAccent,
    ListeningAnswerSource,
    ListeningContentStatus,
    ListeningContentType,
    ListeningPracticeMode,
    ListeningSourceType,
)
from apps.listening.models import (
    MAX_TRANSCRIPT_LENGTH,
    ListeningAttempt,
    ListeningContent,
)

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
        choices=(ListeningContentStatus.choices),
        required=False,
    )

    practiceMode = serializers.ChoiceField(
        choices=(ListeningPracticeMode.choices),
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
        source=("estimated_practice_minutes"),
        read_only=True,
    )

    averageWordsPerMinute = serializers.IntegerField(
        source=("average_words_per_minute"),
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
            choices=(ListeningPracticeMode.choices),
        ),
        source="available_practice_modes",
        read_only=True,
    )

    isFeatured = serializers.BooleanField(
        source="is_featured",
        read_only=True,
    )

    isCompleted = serializers.SerializerMethodField()

    bestAccuracyScore = serializers.SerializerMethodField()

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
    audioUrl = serializers.SerializerMethodField()

    coverImageUrl = serializers.SerializerMethodField()

    transcriptionLanguage = serializers.CharField(
        source=("transcription_language"),
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
        source=("minimum_transcript_words"),
        read_only=True,
    )

    transcriptAvailable = serializers.BooleanField(
        source="transcript_available",
        read_only=True,
    )

    audioAttribution = serializers.SerializerMethodField()

    class Meta(ListeningContentSummarySerializer.Meta):
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
                    return request.build_absolute_uri(file_url)

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


class ListeningAttemptStartSerializer(
    serializers.Serializer,
):
    contentId = serializers.UUIDField(
        source="content_id",
    )

    practiceMode = serializers.ChoiceField(
        source="practice_mode",
        choices=(ListeningPracticeMode.choices),
    )

    answerSource = serializers.ChoiceField(
        source="answer_source",
        choices=(ListeningAnswerSource.choices),
        default=ListeningAnswerSource.TYPED,
    )


class ListeningAttemptDraftUpdateSerializer(
    serializers.Serializer,
):
    answerSource = serializers.ChoiceField(
        source="answer_source",
        choices=(ListeningAnswerSource.choices),
        required=False,
    )

    transcript = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=False,
        max_length=MAX_TRANSCRIPT_LENGTH,
    )

    currentPositionSeconds = serializers.DecimalField(
        source=("current_position_seconds"),
        required=False,
        max_digits=8,
        decimal_places=3,
        min_value=Decimal("0"),
    )

    playbackRate = serializers.DecimalField(
        source="playback_rate",
        required=False,
        max_digits=3,
        decimal_places=2,
        min_value=Decimal("0.50"),
        max_value=Decimal("2.00"),
    )

    def validate(
        self,
        attrs: dict,
    ) -> dict:
        if not attrs:
            raise serializers.ValidationError("At least one draft field must be provided.")

        return attrs


class ListeningAttemptDraftSerializer(
    serializers.ModelSerializer,
):
    attemptId = serializers.UUIDField(
        source="id",
        read_only=True,
    )

    contentId = serializers.UUIDField(
        source="content_id",
        read_only=True,
    )

    practiceMode = serializers.CharField(
        source="practice_mode",
        read_only=True,
    )

    answerSource = serializers.CharField(
        source="answer_source",
        read_only=True,
    )

    currentPositionSeconds = serializers.FloatField(
        source=("current_position_seconds"),
        read_only=True,
    )

    playbackRate = serializers.FloatField(
        source="playback_rate",
        read_only=True,
    )

    createdAt = serializers.DateTimeField(
        source="created_at",
        read_only=True,
    )

    updatedAt = serializers.DateTimeField(
        source="updated_at",
        read_only=True,
    )

    class Meta:
        model = ListeningAttempt

        fields = (
            "attemptId",
            "contentId",
            "practiceMode",
            "answerSource",
            "transcript",
            "currentPositionSeconds",
            "playbackRate",
            "status",
            "createdAt",
            "updatedAt",
        )

        read_only_fields = fields
