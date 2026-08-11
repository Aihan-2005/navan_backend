import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.listening.choices import (
    CefrLevel,
    ListeningAttemptStatus,
    ListeningContentStatus,
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


def test_anonymous_user_only_sees_public_content(
    api_client: APIClient,
) -> None:
    public_content = create_listening_content()

    create_listening_content(
        title=("Unpublished platform content"),
        is_published=False,
    )

    owner = create_user()

    create_listening_content(
        title="Private user content",
        owner=owner,
        source_type=(ListeningSourceType.EXTERNAL_URL),
        content_type=(ListeningContentType.CUSTOM),
        source_url=("https://example.com/audio"),
        is_published=False,
    )

    response = api_client.get(reverse("listening:content-list"))

    assert response.status_code == status.HTTP_200_OK

    assert response.data["count"] == 1

    result = response.data["results"][0]

    assert result["id"] == str(public_content.id)

    assert result["contentType"] == "podcast"

    assert result["sourceType"] == "platform"

    assert result["cefrLevel"] == "B1"
    assert result["isCompleted"] is False

    assert result["bestAccuracyScore"] is None

    assert "content_type" not in result

    assert "reference_transcript" not in result

    assert "referenceTranscript" not in result


def test_authenticated_user_sees_own_content(
    api_client: APIClient,
) -> None:
    create_listening_content(
        title="Public content",
    )

    owner = create_user()

    another_user = create_user(
        identifier=("another@example.com"),
        name="Another User",
    )

    own_content = create_listening_content(
        title="My custom content",
        owner=owner,
        source_type=(ListeningSourceType.EXTERNAL_URL),
        content_type=(ListeningContentType.CUSTOM),
        source_url=("https://example.com/my-audio"),
        is_published=False,
    )

    create_listening_content(
        title="Another user's content",
        owner=another_user,
        source_type=(ListeningSourceType.EXTERNAL_URL),
        content_type=(ListeningContentType.CUSTOM),
        source_url=("https://example.com/other-audio"),
        is_published=False,
    )

    api_client.force_authenticate(user=owner)

    response = api_client.get(reverse("listening:content-list"))

    returned_ids = {item["id"] for item in response.data["results"]}

    assert response.data["count"] == 2

    assert str(own_content.id) in returned_ids


def test_content_detail_matches_frontend_contract(
    api_client: APIClient,
) -> None:
    content = create_listening_content(
        cover_image_url="",
        audio_attribution="",
    )

    response = api_client.get(
        reverse(
            "listening:content-detail",
            kwargs={
                "content_id": content.id,
            },
        )
    )

    assert response.status_code == status.HTTP_200_OK

    assert response.data["id"] == str(content.id)

    assert response.data["audioUrl"] == ("https://cdn.example.com/listening/sample.mp3")

    assert response.data["coverImageUrl"] is None

    assert response.data["audioAttribution"] is None

    assert response.data["transcriptAvailable"] is True

    assert response.data["minimumTranscriptWords"] == 20

    assert "referenceTranscript" not in response.data

    assert "reference_transcript" not in response.data


def test_private_content_is_only_visible_to_owner(
    api_client: APIClient,
) -> None:
    owner = create_user()

    content = create_listening_content(
        owner=owner,
        source_type=(ListeningSourceType.EXTERNAL_URL),
        content_type=(ListeningContentType.CUSTOM),
        source_url=("https://example.com/private-audio"),
        is_published=False,
    )

    url = reverse(
        "listening:content-detail",
        kwargs={
            "content_id": content.id,
        },
    )

    anonymous_response = api_client.get(url)

    assert anonymous_response.status_code == status.HTTP_404_NOT_FOUND

    api_client.force_authenticate(user=owner)

    owner_response = api_client.get(url)

    assert owner_response.status_code == status.HTTP_200_OK


def test_non_ready_content_has_no_detail_page(
    api_client: APIClient,
) -> None:
    content = create_listening_content(
        status=(ListeningContentStatus.COMING_SOON),
        audio_stream_url="",
    )

    list_response = api_client.get(reverse("listening:content-list"))

    assert list_response.data["count"] == 1

    detail_response = api_client.get(
        reverse(
            "listening:content-detail",
            kwargs={
                "content_id": content.id,
            },
        )
    )

    assert detail_response.status_code == status.HTTP_404_NOT_FOUND


def test_content_filters_are_applied(
    api_client: APIClient,
) -> None:
    matching_content = create_listening_content(
        title="Shadowing podcast",
        content_type=(ListeningContentType.PODCAST),
        cefr_level=CefrLevel.B2,
        duration_seconds=90,
        is_featured=True,
        available_practice_modes=[
            ListeningPracticeMode.SHADOWING,
        ],
    )

    create_listening_content(
        title="Comprehension story",
        content_type=(ListeningContentType.STORY),
        cefr_level=CefrLevel.A2,
        duration_seconds=240,
        available_practice_modes=[
            ListeningPracticeMode.COMPREHENSION,
        ],
    )

    response = api_client.get(
        reverse("listening:content-list"),
        {
            "contentType": "podcast",
            "cefrLevel": "B2",
            "practiceMode": "shadowing",
            "isFeatured": "true",
            "ordering": "shortest",
        },
    )

    assert response.status_code == status.HTTP_200_OK

    assert response.data["count"] == 1

    assert response.data["results"][0]["id"] == str(matching_content.id)


def test_invalid_filter_returns_bad_request(
    api_client: APIClient,
) -> None:
    response = api_client.get(
        reverse("listening:content-list"),
        {
            "contentType": ("invalid-type"),
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    assert "contentType" in response.data


def test_content_list_is_paginated(
    api_client: APIClient,
) -> None:
    for index in range(3):
        create_listening_content(
            title=f"Content {index}",
        )

    response = api_client.get(
        reverse("listening:content-list"),
        {
            "pageSize": 2,
        },
    )

    assert response.status_code == status.HTTP_200_OK

    assert response.data["count"] == 3

    assert len(response.data["results"]) == 2

    assert response.data["next"] is not None

    assert response.data["previous"] is None


def test_completed_attempt_marks_content_as_completed(
    api_client: APIClient,
) -> None:
    user = create_user()

    content = create_listening_content()

    ListeningAttempt.objects.create(
        user=user,
        content=content,
        practice_mode=(ListeningPracticeMode.FULL_DICTATION),
        status=(ListeningAttemptStatus.COMPLETED),
    )

    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("listening:content-list"))

    assert response.status_code == status.HTTP_200_OK

    assert response.data["results"][0]["isCompleted"] is True
