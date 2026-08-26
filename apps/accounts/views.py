from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordResetVerifySerializer,
    RegisterSerializer,
)
from .services import (
    ExpiredOTPError,
    InvalidOTPError,
    LockedOTPError,
    issue_tokens_for_user,
    request_password_reset,
    reset_user_password,
    verify_password_reset_otp,
)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request):
        serializer = RegisterSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        user = serializer.save()
        token = issue_tokens_for_user(user)

        return Response(
            {"user": serializer.data, "token": token},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request):
        serializer = LoginSerializer(
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        token = issue_tokens_for_user(user)

        return Response(
            {
                "message": "ورود با موفقیت انجام شد.",
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "identifier": user.identifier,
                },
                "token": token,
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        request_password_reset(serializer.validated_data["identifier"])

        return Response({"message": ("در صورت وجود حساب، کد بازیابی ارسال شده است.")})


class PasswordResetVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetVerifySerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        identifier = serializer.validated_data["identifier"]
        raw_code = serializer.validated_data["otp"]

        try:
            reset_token = verify_password_reset_otp(
                identifier=identifier,
                raw_code=raw_code,
            )
        except (
            InvalidOTPError,
            ExpiredOTPError,
            LockedOTPError,
        ) as exc:
            return Response(
                {"message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "message": "کد با موفقیت تأیید شد.",
                "reset_token": reset_token,
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        tokens = reset_user_password(
            user=serializer.validated_data["user"],
            otp=serializer.validated_data["otp"],
            new_password=serializer.validated_data["password"],
        )

        return Response(
            {
                "message": "رمز عبور با موفقیت تغییر کرد.",
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )


class TestAuthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "message": "توکن معتبر است.",
                "user": {
                    "id": request.user.id,
                    "name": request.user.name,
                    "identifier": request.user.identifier,
                },
            }
        )
