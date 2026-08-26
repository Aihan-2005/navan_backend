import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.listening.choices import (
    ListeningPracticeMode,
)
from apps.listening.tests.factories import (
    create_listening_content,
    create_user,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def test_user_can_start_listen_only_attempt(
    api_client: APIClient,
) -> None:
    user = create_user()

    content = create_listening_content(
        available_practice_modes=[
            ListeningPracticeMode.LISTEN_ONLY,
            ListeningPracticeMode.FULL_DICTATION,
        ],
    )

    api_client.force_authenticate(
        user=user,
    )

    response = api_client.post(
        reverse("listening:attempt-start"),
        {
            "contentId": str(content.id),
            "practiceMode": ("listen_only"),
            "answerSource": "typed",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    assert response.data["practiceMode"] == "listen_only"

    assert response.data["status"] == "draft"

    assert response.data["transcript"] == ""
