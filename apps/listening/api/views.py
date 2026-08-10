from typing import Any

from django.db.models import QuerySet
from drf_spectacular.utils import (
    extend_schema,
)
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from apps.listening.api.pagination import (
    ListeningContentPagination,
)
from apps.listening.api.serializers import (
    ListeningContentDetailSerializer,
    ListeningContentFilterSerializer,
    ListeningContentSummarySerializer,
)
from apps.listening.models import ListeningContent
from apps.listening.selectors import (
    get_listening_content_details,
    get_listening_contents,
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
        summary="List listening contents",
        description=(
            "Return public platform contents and the authenticated user's own custom contents."
        ),
        parameters=[
            ListeningContentFilterSerializer,
        ],
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
        summary="Retrieve listening content",
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
