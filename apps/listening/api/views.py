from typing import Any
from uuid import UUID

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    extend_schema,
)
from rest_framework import generics, status
from rest_framework.exceptions import (
    NotFound,
    ValidationError,
)
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.listening.api.exceptions import (
    ListeningConflict,
)
from apps.listening.api.pagination import (
    ListeningContentPagination,
)
from apps.listening.api.serializers import (
    ListeningAttemptDraftSerializer,
    ListeningAttemptDraftUpdateSerializer,
    ListeningAttemptStartSerializer,
    ListeningContentDetailSerializer,
    ListeningContentFilterSerializer,
    ListeningContentSummarySerializer,
)
from apps.listening.models import (
    ListeningAttempt,
    ListeningContent,
)
from apps.listening.selectors import (
    get_listening_attempts_for_user,
    get_listening_content_details,
    get_listening_contents,
)
from apps.listening.services import (
    ListeningAttemptNotEditableError,
    ListeningDomainError,
    ListeningPositionOutOfRangeError,
    start_or_resume_listening_attempt,
    update_listening_attempt_draft,
)


class ListeningContentListAPIView(
    generics.ListAPIView,
):
    queryset = ListeningContent.objects.none()

    serializer_class = ListeningContentSummarySerializer

    pagination_class = ListeningContentPagination

    permission_classes = (AllowAny,)

    def get_queryset(
        self,
    ) -> QuerySet[ListeningContent]:
        filter_serializer = ListeningContentFilterSerializer(
            data=self.request.query_params,
        )

        filter_serializer.is_valid(
            raise_exception=True,
        )

        return get_listening_contents(
            user=self.request.user,
            filters=(filter_serializer.validated_data),
        )

    @extend_schema(
        summary=("List listening contents"),
        description=(
            "Return public platform contents and the authenticated user's own custom contents."
        ),
        parameters=[ListeningContentFilterSerializer],
        tags=["Listening"],
    )
    def get(
        self,
        request: Request,
        *args: Any,
        **kwargs: Any,
    ) -> Response:
        return super().get(
            request,
            *args,
            **kwargs,
        )


class ListeningContentDetailAPIView(
    generics.RetrieveAPIView,
):
    queryset = ListeningContent.objects.none()

    serializer_class = ListeningContentDetailSerializer

    permission_classes = (AllowAny,)

    lookup_field = "id"
    lookup_url_kwarg = "content_id"

    def get_queryset(
        self,
    ) -> QuerySet[ListeningContent]:
        return get_listening_content_details(
            user=self.request.user,
        )

    @extend_schema(
        summary=("Retrieve listening content"),
        description=("Return one ready and playable listening content."),
        responses=(ListeningContentDetailSerializer),
        tags=["Listening"],
    )
    def get(
        self,
        request: Request,
        *args: Any,
        **kwargs: Any,
    ) -> Response:
        return super().get(
            request,
            *args,
            **kwargs,
        )


class ListeningAttemptStartAPIView(
    APIView,
):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary=("Start or resume a listening attempt"),
        request=(ListeningAttemptStartSerializer),
        responses={
            200: (ListeningAttemptDraftSerializer),
            201: (ListeningAttemptDraftSerializer),
        },
        tags=["Listening"],
    )
    def post(
        self,
        request: Request,
    ) -> Response:
        serializer = ListeningAttemptStartSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        data = serializer.validated_data

        content = get_object_or_404(
            get_listening_content_details(
                user=request.user,
            ),
            id=data["content_id"],
        )

        try:
            (
                attempt,
                created,
            ) = start_or_resume_listening_attempt(
                user=request.user,
                content=content,
                practice_mode=(data["practice_mode"]),
                answer_source=(data["answer_source"]),
            )
        except ListeningDomainError as exc:
            raise ValidationError(
                {
                    "message": str(exc),
                    "code": exc.code,
                }
            ) from exc

        response_serializer = ListeningAttemptDraftSerializer(attempt)

        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK

        return Response(
            response_serializer.data,
            status=response_status,
        )


class ListeningAttemptDraftAPIView(
    APIView,
):
    permission_classes = (IsAuthenticated,)

    def _get_attempt(
        self,
        request: Request,
        attempt_id: UUID,
    ) -> ListeningAttempt:
        return get_object_or_404(
            get_listening_attempts_for_user(
                user=request.user,
            ),
            id=attempt_id,
        )

    @extend_schema(
        summary=("Retrieve a listening attempt draft"),
        responses=(ListeningAttemptDraftSerializer),
        tags=["Listening"],
    )
    def get(
        self,
        request: Request,
        attempt_id: UUID,
    ) -> Response:
        attempt = self._get_attempt(
            request,
            attempt_id,
        )

        serializer = ListeningAttemptDraftSerializer(attempt)

        return Response(serializer.data)

    @extend_schema(
        summary=("Update a listening attempt draft"),
        request=(ListeningAttemptDraftUpdateSerializer),
        responses=(ListeningAttemptDraftSerializer),
        tags=["Listening"],
    )
    def patch(
        self,
        request: Request,
        attempt_id: UUID,
    ) -> Response:
        attempt = self._get_attempt(
            request,
            attempt_id,
        )

        serializer = ListeningAttemptDraftUpdateSerializer(
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            updated_attempt = update_listening_attempt_draft(
                user=request.user,
                attempt_id=attempt.id,
                updates=(serializer.validated_data),
            )
        except ListeningAttempt.DoesNotExist as exc:
            raise NotFound("Listening attempt was not found.") from exc

        except ListeningAttemptNotEditableError as exc:
            raise ListeningConflict(
                detail={
                    "message": str(exc),
                    "code": exc.code,
                }
            ) from exc

        except ListeningPositionOutOfRangeError as exc:
            raise ValidationError(
                {
                    "message": str(exc),
                    "code": exc.code,
                }
            ) from exc

        response_serializer = ListeningAttemptDraftSerializer(updated_attempt)

        return Response(response_serializer.data)
