from drf_spectacular.utils import (
    extend_schema,
)
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.listening.api.overview_serializers import (
    ListeningOverviewSerializer,
)
from apps.listening.overview import (
    build_listening_overview,
)


class ListeningOverviewAPIView(
    APIView,
):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary=("Retrieve listening overview"),
        description=("Return personalized Listening dashboard data for the authenticated user."),
        responses=(ListeningOverviewSerializer),
        tags=["Listening"],
    )
    def get(
        self,
        request: Request,
    ) -> Response:
        overview = build_listening_overview(
            user=request.user,
        )

        serializer = ListeningOverviewSerializer(
            instance=overview,
            context={
                "request": request,
            },
        )

        return Response(serializer.data)
