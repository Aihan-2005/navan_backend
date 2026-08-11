import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.listening.choices import (
    ListeningAttemptStatus,
    ListeningContentType,
    ListeningPracticeMode,
    ListeningSourceType,
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


def test_start_attempt_requires_authentication(
    api_client: APIClient,
) -> None:
    content = create_listening_content()

    response = api_client.post(
        reverse("listening:attempt-start"),
        {
            "contentId": str(content.id),
            "practiceMode": ("full_dictation"),
            "answerSource": "typed",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_start_attempt_matches_frontend_draft_contract(
    api_client: APIClient,
) -> None:
    user = create_user()
    content = create_listening_content()

    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("listening:attempt-start"),
        {
            "contentId": str(content.id),
            "practiceMode": ("full_dictation"),
            "answerSource": "typed",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    assert response.data["attemptId"]

    assert response.data["contentId"] == str(content.id)

    assert response.data["practiceMode"] == "full_dictation"

    assert response.data["answerSource"] == "typed"

    assert response.data["transcript"] == ""

    assert response.data["currentPositionSeconds"] == 0.0

    assert response.data["playbackRate"] == 1.0

    assert response.data["status"] == "draft"

    assert response.data["createdAt"]
    assert response.data["updatedAt"]


def test_start_attempt_resumes_existing_editable_attempt(
    api_client: APIClient,
) -> None:
    user = create_user()
    content = create_listening_content()

    api_client.force_authenticate(user=user)

    payload = {
        "contentId": str(content.id),
        "practiceMode": "full_dictation",
        "answerSource": "typed",
    }

    first_response = api_client.post(
        reverse("listening:attempt-start"),
        payload,
        format="json",
    )

    second_response = api_client.post(
        reverse("listening:attempt-start"),
        payload,
        format="json",
    )

    assert first_response.status_code == status.HTTP_201_CREATED

    assert second_response.status_code == status.HTTP_200_OK

    assert second_response.data["attemptId"] == first_response.data["attemptId"]

    assert ListeningAttempt.objects.count() == 1


def test_start_attempt_rejects_unavailable_practice_mode(
    api_client: APIClient,
) -> None:
    user = create_user()

    content = create_listening_content(
        available_practice_modes=[
            ListeningPracticeMode.SHADOWING,
        ],
    )

    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("listening:attempt-start"),
        {
            "contentId": str(content.id),
            "practiceMode": ("full_dictation"),
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    assert response.data["code"] == "practice_mode_unavailable"


def test_user_cannot_start_attempt_for_another_users_content(
    api_client: APIClient,
) -> None:
    owner = create_user()

    another_user = create_user(
        identifier=("another@example.com"),
        name="Another User",
    )

    content = create_listening_content(
        owner=owner,
        source_type=(ListeningSourceType.EXTERNAL_URL),
        content_type=(ListeningContentType.CUSTOM),
        source_url=("https://example.com/private-audio"),
        is_published=False,
    )

    api_client.force_authenticate(user=another_user)

    response = api_client.post(
        reverse("listening:attempt-start"),
        {
            "contentId": str(content.id),
            "practiceMode": ("full_dictation"),
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_owner_can_retrieve_attempt_draft(
    api_client: APIClient,
) -> None:
    user = create_user()
    content = create_listening_content()

    attempt = ListeningAttempt.objects.create(
        user=user,
        content=content,
        practice_mode=(ListeningPracticeMode.FULL_DICTATION),
        transcript="hello",
    )

    api_client.force_authenticate(user=user)

    response = api_client.get(
        reverse(
            "listening:attempt-draft",
            kwargs={
                "attempt_id": attempt.id,
            },
        )
    )

    assert response.status_code == status.HTTP_200_OK

    assert response.data["attemptId"] == str(attempt.id)

    assert response.data["transcript"] == "hello"


def test_other_user_cannot_retrieve_attempt_draft(
    api_client: APIClient,
) -> None:
    owner = create_user()

    another_user = create_user(
        identifier=("another@example.com"),
        name="Another User",
    )

    content = create_listening_content()

    attempt = ListeningAttempt.objects.create(
        user=owner,
        content=content,
        practice_mode=(ListeningPracticeMode.FULL_DICTATION),
    )

    api_client.force_authenticate(user=another_user)

    response = api_client.get(
        reverse(
            "listening:attempt-draft",
            kwargs={
                "attempt_id": attempt.id,
            },
        )
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_patch_attempt_draft_saves_transcript_and_audio_state(
    api_client: APIClient,
) -> None:
    user = create_user()
    content = create_listening_content()

    attempt = ListeningAttempt.objects.create(
        user=user,
        content=content,
        practice_mode=(ListeningPracticeMode.FULL_DICTATION),
    )

    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse(
            "listening:attempt-draft",
            kwargs={
                "attempt_id": attempt.id,
            },
        ),
        {
            "transcript": ("I heard this sentence."),
            "currentPositionSeconds": (45.25),
            "playbackRate": 1.25,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    assert response.data["transcript"] == "I heard this sentence."

    assert response.data["currentPositionSeconds"] == 45.25

    assert response.data["playbackRate"] == 1.25

    attempt.refresh_from_db()

    assert attempt.transcript == "I heard this sentence."


def test_patch_attempt_rejects_position_past_duration(
    api_client: APIClient,
) -> None:
    user = create_user()

    content = create_listening_content(
        duration_seconds=60,
    )

    attempt = ListeningAttempt.objects.create(
        user=user,
        content=content,
        practice_mode=(ListeningPracticeMode.FULL_DICTATION),
    )

    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse(
            "listening:attempt-draft",
            kwargs={
                "attempt_id": attempt.id,
            },
        ),
        {
            "currentPositionSeconds": 61,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    assert response.data["code"] == "position_out_of_range"


def test_completed_attempt_cannot_be_edited(
    api_client: APIClient,
) -> None:
    user = create_user()
    content = create_listening_content()

    attempt = ListeningAttempt.objects.create(
        user=user,
        content=content,
        practice_mode=(ListeningPracticeMode.FULL_DICTATION),
        status=(ListeningAttemptStatus.COMPLETED),
    )

    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse(
            "listening:attempt-draft",
            kwargs={
                "attempt_id": attempt.id,
            },
        ),
        {
            "transcript": "changed",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_409_CONFLICT

    assert response.data["code"] == "attempt_not_editable"
