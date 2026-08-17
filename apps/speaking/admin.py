# Register your models here.
from django.contrib import admin

from apps.speaking.models import SpeakingExercise, SpeakingSession, SpeakingTag, SpeakingTurn


@admin.register(SpeakingTag)
class SpeakingTagAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(SpeakingExercise)
class SpeakingExerciseAdmin(admin.ModelAdmin):
    list_display = ["title", "exercise_type", "cefr_level", "coaching_style", "is_active", "order"]
    list_filter = ["exercise_type", "cefr_level", "coaching_style", "is_active"]
    search_fields = ["title", "description"]
    filter_horizontal = ["tags"]


class SpeakingTurnInline(admin.TabularInline):
    model = SpeakingTurn
    extra = 0
    readonly_fields = ["created_at"]


@admin.register(SpeakingSession)
class SpeakingSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "exercise", "status", "started_at", "fluency_score"]
    list_filter = ["status"]
    inlines = [SpeakingTurnInline]