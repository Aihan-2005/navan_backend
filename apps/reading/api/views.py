from rest_framework import status
from rest_framework.exceptions import (
    NotFound,
    PermissionDenied,
)
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.reading.exceptions import (
    ActiveReadingConflictError,
    ReadingResourceAccessDeniedError,
    ReadingResourceNotFoundError,
    ReadingRetryNotAllowedError,
)
from apps.reading.services import (
    get_or_create_reading_analysis,
    resolve_reading_resource,
    retry_failed_reading_analysis,
)

from .selectors import (
    get_user_analysis,
    get_user_analysis_section,
    list_user_analysis_sections,
)
from .serializers import (
    ReadingAnalysisCreateSerializer,
    ReadingAnalysisSerializer,
    ReadingSectionDetailSerializer,
    ReadingSectionListSerializer,
)

READING_SERVICE_EXCEPTIONS = (
    ReadingResourceNotFoundError,
    ReadingResourceAccessDeniedError,
    ActiveReadingConflictError,
    ReadingRetryNotAllowedError,
)


def _service_error_response(
    exc: Exception,
) -> Response:

    if isinstance(
        exc,
        ReadingResourceNotFoundError,
    ):
        raise NotFound(str(exc)) from exc

    if isinstance(
        exc,
        ReadingResourceAccessDeniedError,
    ):
        raise PermissionDenied(str(exc)) from exc

    if isinstance(
        exc,
        ActiveReadingConflictError,
    ):
        payload = {
            "detail": str(exc),
            "code": "active_reading_conflict",
        }

        if exc.analysis_id is not None:
            payload["active_analysis_id"] = exc.analysis_id

        return Response(
            payload,
            status=status.HTTP_409_CONFLICT,
        )

    if isinstance(
        exc,
        ReadingRetryNotAllowedError,
    ):
        return Response(
            {
                "detail": str(exc),
                "code": ("reading_retry_not_allowed"),
            },
            status=status.HTTP_409_CONFLICT,
        )

    raise exc


class ReadingAnalysisCreateAPIView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    def post(
        self,
        request: Request,
    ):
        serializer = ReadingAnalysisCreateSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        try:
            resource = resolve_reading_resource(
                user=request.user,
                resource_type=(serializer.validated_data["resource_type"]),
                resource_id=(serializer.validated_data["resource_id"]),
            )

            analysis, created = get_or_create_reading_analysis(
                user=request.user,
                resource=resource,
            )

        except READING_SERVICE_EXCEPTIONS as exc:
            return _service_error_response(exc)

        response_serializer = ReadingAnalysisSerializer(analysis)

        response_status = status.HTTP_202_ACCEPTED if created else status.HTTP_200_OK

        return Response(
            {
                "created": created,
                "reused": not created,
                "analysis": (response_serializer.data),
            },
            status=response_status,
        )


class ReadingAnalysisDetailAPIView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    def get(
        self,
        request: Request,
        analysis_id: int,
    ):
        analysis = get_user_analysis(
            user=request.user,
            analysis_id=analysis_id,
        )

        if analysis is None:
            raise NotFound("Reading analysis not found.")

        serializer = ReadingAnalysisSerializer(analysis)

        return Response(serializer.data)


class ReadingAnalysisSectionListAPIView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    def get(
        self,
        request: Request,
        analysis_id: int,
    ):
        analysis = get_user_analysis(
            user=request.user,
            analysis_id=analysis_id,
        )

        if analysis is None:
            raise NotFound("Reading analysis not found.")

        sections = list_user_analysis_sections(
            user=request.user,
            analysis_id=analysis_id,
        )

        serializer = ReadingSectionListSerializer(
            sections,
            many=True,
        )

        results = serializer.data

        return Response(
            {
                "analysis_id": analysis.id,
                "status": analysis.status,
                "progress_percent": (analysis.progress_percent),
                "count": len(results),
                "results": results,
            }
        )


class ReadingAnalysisSectionDetailAPIView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    def get(
        self,
        request: Request,
        analysis_id: int,
        section_id: int,
    ):
        section = get_user_analysis_section(
            user=request.user,
            analysis_id=analysis_id,
            section_id=section_id,
        )

        if section is None:
            raise NotFound("Reading section not found.")

        serializer = ReadingSectionDetailSerializer(section)

        return Response(serializer.data)


class ReadingAnalysisRetryAPIView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    def post(
        self,
        request: Request,
        analysis_id: int,
    ):
        analysis = get_user_analysis(
            user=request.user,
            analysis_id=analysis_id,
        )

        if analysis is None:
            raise NotFound("Reading analysis not found.")

        try:
            new_analysis = retry_failed_reading_analysis(
                user=request.user,
                analysis=analysis,
            )

        except READING_SERVICE_EXCEPTIONS as exc:
            return _service_error_response(exc)

        serializer = ReadingAnalysisSerializer(new_analysis)

        return Response(
            {
                "retried_from_analysis_id": (analysis.id),
                "analysis": serializer.data,
            },
            status=status.HTTP_202_ACCEPTED,
        )
