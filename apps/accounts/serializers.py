from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import (
    validate_password,
)
from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import (
    TokenError,
)

from .models import PasswordResetOTP, User
from .tokens import PasswordResetToken
from .validators import (
    normalize_identifier,
    validate_identifier,
)


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=150,
        allow_blank=False,
        trim_whitespace=True,
    )

    identifier = serializers.CharField(
        max_length=254,
        allow_blank=False,
        trim_whitespace=True,
    )

    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate_identifier(
        self,
        value: str,
    ) -> str:
        normalized_identifier = normalize_identifier(value)

        try:
            validate_identifier(normalized_identifier)
        except ValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

        if User.objects.filter(identifier=normalized_identifier).exists():
            raise serializers.ValidationError("کاربری با این ایمیل یا شماره تلفن وجود دارد.")

        return normalized_identifier

    def validate(
        self,
        attrs: dict,
    ) -> dict:
        password = attrs["password"]
        password_confirm = attrs["password_confirm"]

        if password != password_confirm:
            raise serializers.ValidationError(
                {"password_confirm": ("تکرار رمز عبور با رمز عبور مطابقت ندارد.")}
            )

        try:
            validate_password(password)
        except ValidationError as exc:
            raise serializers.ValidationError(
                {
                    "password": exc.messages,
                }
            ) from exc

        return attrs

    def create(
        self,
        validated_data: dict,
    ) -> User:
        validated_data.pop("password_confirm")

        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(
        max_length=254,
        allow_blank=False,
        trim_whitespace=True,
    )

    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate_identifier(
        self,
        value: str,
    ) -> str:
        normalized_identifier = normalize_identifier(value)

        try:
            validate_identifier(normalized_identifier)
        except ValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

        return normalized_identifier

    def validate(
        self,
        attrs: dict,
    ) -> dict:
        identifier = attrs["identifier"]
        password = attrs["password"]

        user = authenticate(
            request=self.context.get("request"),
            username=identifier,
            password=password,
        )

        if user is None:
            raise serializers.ValidationError("شناسه یا رمز عبور اشتباه است.")

        if not user.is_active:
            raise serializers.ValidationError("حساب کاربری غیرفعال است.")

        attrs["user"] = user

        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    identifier = serializers.CharField(
        max_length=254,
        allow_blank=False,
        trim_whitespace=True,
    )

    def validate_identifier(
        self,
        value: str,
    ) -> str:
        identifier = normalize_identifier(value)

        try:
            validate_identifier(identifier)
        except ValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

        return identifier


class PasswordResetVerifySerializer(serializers.Serializer):
    identifier = serializers.CharField(
        max_length=254,
        allow_blank=False,
        trim_whitespace=True,
    )

    otp = serializers.RegexField(
        regex=r"^\d{6}$",
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            "invalid": ("کد تأیید باید ۶ رقم باشد."),
        },
    )

    def validate_identifier(
        self,
        value: str,
    ) -> str:
        identifier = normalize_identifier(value)

        try:
            validate_identifier(identifier)
        except ValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

        return identifier


class PasswordResetConfirmSerializer(serializers.Serializer):
    reset_token = serializers.CharField(
        write_only=True,
    )

    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(
        self,
        attrs: dict,
    ) -> dict:
        password = attrs["password"]
        password_confirm = attrs["password_confirm"]

        if password != password_confirm:
            raise serializers.ValidationError(
                {"password_confirm": ("تکرار رمز عبور مطابقت ندارد.")}
            )

        try:
            token = PasswordResetToken(attrs["reset_token"])
        except TokenError as exc:
            raise serializers.ValidationError(
                {"reset_token": ("توکن بازیابی نامعتبر یا منقضی شده است.")}
            ) from exc

        otp_id = token.get("otp_id")
        user_id = token.get("user_id")

        if otp_id is None or user_id is None:
            raise serializers.ValidationError({"reset_token": ("توکن بازیابی نامعتبر است.")})

        otp = (
            PasswordResetOTP.objects.select_related("user")
            .filter(
                pk=otp_id,
                user_id=user_id,
            )
            .first()
        )

        if otp is None:
            raise serializers.ValidationError({"reset_token": ("توکن بازیابی دیگر معتبر نیست.")})

        user = otp.user

        try:
            validate_password(
                password,
                user=user,
            )
        except ValidationError as exc:
            raise serializers.ValidationError(
                {
                    "password": exc.messages,
                }
            ) from exc

        attrs["user"] = user
        attrs["otp"] = otp

        return attrs
