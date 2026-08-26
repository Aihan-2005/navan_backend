from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.listening.choices import (
    ListeningAttemptStatus,
    ListeningPracticeMode,
)
from apps.listening.models import (
    ListeningAttempt,
)
from apps.listening.tests.factories import (
    create_listening_content,
    create_user,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def test_overview_requires_authentication(
    api_client: APIClient,
) -> None:
    response = api_client.get(reverse("listening:overview"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_overview_matches_frontend_contract(
    api_client: APIClient,
) -> None:
    user = create_user()

    featured_content = create_listening_content(
        title="Featured podcast",
        is_featured=True,
    )

    recommended_content = create_listening_content(
        title="Recommended podcast",
        is_featured=False,
    )

    ListeningAttempt.objects.create(
        user=user,
        content=recommended_content,
        practice_mode=(ListeningPracticeMode.FULL_DICTATION),
        current_position_seconds=(Decimal("45.500")),
        playback_rate=(Decimal("1.00")),
        status=(ListeningAttemptStatus.DRAFT),
    )

    api_client.force_authenticate(
        user=user,
    )

    response = api_client.get(reverse("listening:overview"))

    assert response.status_code == status.HTTP_200_OK

    assert response.data["stats"] == {
        "totalSessions": 0,
        "weeklyMinutes": 0,
        "averageAccuracyScore": 0.0,
        "bestAccuracyScore": 0.0,
        "currentStreakDays": 0,
    }

    assert response.data["continueListening"]["contentId"] == str(recommended_content.id)

    assert response.data["continueListening"]["currentPositionSeconds"] == 45

    assert response.data["continueListening"]["practiceMode"] == "full_dictation"

    assert response.data["featuredContents"][0]["id"] == str(featured_content.id)

    recommended_ids = {item["id"] for item in response.data["recommendedContents"]}

    assert str(recommended_content.id) in recommended_ids

    assert response.data["primaryInsight"] is None

    assert response.data["recentActivities"] == []


def test_overview_reports_completed_sessions(
    api_client: APIClient,
) -> None:
    user = create_user()

    content = create_listening_content(
        duration_seconds=180,
    )

    ListeningAttempt.objects.create(
        user=user,
        content=content,
        practice_mode=(ListeningPracticeMode.FULL_DICTATION),
        status=(ListeningAttemptStatus.COMPLETED),
        submitted_at=timezone.now(),
        completed_at=timezone.now(),
    )

    api_client.force_authenticate(
        user=user,
    )

    response = api_client.get(reverse("listening:overview"))

    assert response.status_code == status.HTTP_200_OK

    stats = response.data["stats"]

    assert stats["totalSessions"] == 1
    assert stats["weeklyMinutes"] == 3

    assert stats["currentStreakDays"] == 1
