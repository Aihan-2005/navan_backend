from rest_framework import serializers

from apps.speaking.models import (
    SpeakingEvaluation,
    SpeakingExercise,
    SpeakingSession,
    SpeakingTag,
    SpeakingTurn,
)


class SpeakingTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpeakingTag
        fields = ["id", "name"]


class SpeakingExerciseListSerializer(serializers.ModelSerializer):
    tags = SpeakingTagSerializer(many=True, read_only=True)

    class Meta:
        model = SpeakingExercise
        fields = [
            "id",
            "title",
            "description",
            "exercise_type",
            "cefr_level",
            "coaching_style",
            "estimated_minutes",
            "tags",
            "is_recommended",
        ]


class SpeakingTurnSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpeakingTurn
        fields = [
            "id",
            "speaker",
            "order",
            "text",
            "audio_file",
            "audio_format",
            "audio_size_bytes",
            "audio_duration_seconds",
            "transcription_status",
            "created_at",
        ]
        read_only_fields = ["id", "text", "transcription_status", "created_at"]


class SpeakingSessionListSerializer(serializers.ModelSerializer):
    exercise_title = serializers.CharField(source="exercise.title", read_only=True)

    class Meta:
        model = SpeakingSession
        fields = [
            "id",
            "exercise",
            "exercise_title",
            "status",
            "started_at",
            "completed_at",
            "duration_seconds",
        ]
        read_only_fields = fields


class SpeakingSessionDetailSerializer(SpeakingSessionListSerializer):
    turns = SpeakingTurnSerializer(many=True, read_only=True)

    class Meta(SpeakingSessionListSerializer.Meta):
        fields = SpeakingSessionListSerializer.Meta.fields + ["turns"]


class SpeakingSessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpeakingSession
        fields = ["id", "exercise", "status", "started_at"]
        read_only_fields = ["id", "status", "started_at"]

    def validate_exercise(self, exercise):
        if not exercise.is_active:
            raise serializers.ValidationError("This exercise is not currently available.")
        return exercise


MAX_RECORDING_SECONDS = 180


class SpeakingTurnCreateSerializer(serializers.ModelSerializer):
    audio_duration_seconds = serializers.FloatField(required=True)

    class Meta:
        model = SpeakingTurn
        fields = ["id", "audio_file", "audio_duration_seconds"]
        read_only_fields = ["id"]

    def validate_audio_file(self, audio_file):
        max_size_mb = 15
        if audio_file.size > max_size_mb * 1024 * 1024:
            raise serializers.ValidationError(f"Audio file must be under {max_size_mb}MB.")
        return audio_file

    def validate_audio_duration_seconds(self, duration):
        if duration > MAX_RECORDING_SECONDS:
            raise serializers.ValidationError(
                f"Recording exceeds the maximum of {MAX_RECORDING_SECONDS} seconds."
            )
        return duration


class SpeakingEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpeakingEvaluation
        fields = [
            "id",
            "status",
            "score",
            "analysis",
            "error_message",
            "created_at",
            "completed_at",
        ]
        read_only_fields = fields


class SpeakingStatsSerializer(serializers.Serializer):
    current_streak_days = serializers.IntegerField()
    average_fluency = serializers.FloatField(allow_null=True)
    minutes_this_week = serializers.FloatField()
    total_sessions = serializers.IntegerField()
