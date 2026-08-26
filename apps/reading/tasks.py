from celery import shared_task

from .models import ReadingAnalysis, ReadingSection
from .ai import analyze_reading_with_ai_stream


@shared_task
def analyze_reading(analysis_id):
    analysis = ReadingAnalysis.objects.select_related(
        "user",
        "system_resource",
        "user_resource",
    ).get(id=analysis_id)

    resource = analysis.system_resource or analysis.user_resource

    try:
        for event in analyze_reading_with_ai_stream(
            file=resource.file,
            user=analysis.user,
        ):

            if event["type"] == "overview":
                analysis.difficulty_profile = event.get(
                    "difficulty_profile",
                    {},
                )
                analysis.vocabulary_profile = event.get(
                    "vocabulary_profile",
                    {},
                )
                analysis.quality_profile = event.get(
                    "quality_profile",
                    {},
                )

                analysis.save(
                    update_fields=[
                        "difficulty_profile",
                        "vocabulary_profile",
                        "quality_profile",
                    ]
                )

            elif event["type"] == "section":
                section_data = event["data"]

                ReadingSection.objects.update_or_create(
                    analysis=analysis,
                    order=section_data["order"],
                    defaults={
                        "title": section_data["title"],
                        "data": {
                            "paragraphs": section_data.get("paragraphs", []),
                            "quiz": section_data.get("quiz", []),
                        },
                    },
                )

        analysis.status = "ACTIVE"
        analysis.save(update_fields=["status"])

    except Exception:
        analysis.status = "FAILED"
        analysis.save(update_fields=["status"])

        raise
