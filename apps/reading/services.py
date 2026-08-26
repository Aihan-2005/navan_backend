from rest_framework.exceptions import ValidationError
from .models import (
    ReadingAnalysis,
    ReadingResource,
    UserReadingResource,
)
from .tasks import analyze_reading

def get_or_create_reading_analysis(*, user, resource):
    active_analysis = ReadingAnalysis.objects.filter(
        user=user,
        status__in=["PROCESSING", "ACTIVE"],
    ).first()

    if isinstance(resource, ReadingResource):
        resource_field = "reading_resource"
        resource_id = active_analysis.system_resource_id if active_analysis else None

    elif isinstance(resource, UserReadingResource):
        resource_field = "user_resource"
        resource_id = active_analysis.user_resource_id if active_analysis else None

    else:
        raise ValidationError("Invalid reading resource.")

    if active_analysis:
        if resource_id == resource.id:
            return active_analysis, False

        raise ValidationError("You must finish your current reading first.")

    analysis = ReadingAnalysis.objects.create(
        user=user,
        status="PROCESSING",
        **{resource_field: resource},
    )

    analyze_reading.delay(analysis.id)

    return analysis, True
