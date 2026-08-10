from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken
import secrets
from math import ceil
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from .models import PasswordResetOTP
from .tokens import issue_password_reset_token

User = get_user_model()


def issue_tokens_for_user(user) -> dict[str, str]:
    if not user.is_active:
        raise AuthenticationFailed("حساب کاربری غیرفعال است.")

    refresh = RefreshToken.for_user(user)

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


class OTPStillActiveError(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__("کد قبلی هنوز معتبر است.")


@transaction.atomic
def create_password_reset_otp(user):
    locked_user = User.objects.select_for_update().get(
        pk=user.pk,
    )

    current_otp = PasswordResetOTP.objects.filter(
        user=locked_user,
    ).first()

    if current_otp is not None:
        if not current_otp.is_expired:
            remaining_seconds = ceil(
                (current_otp.expires_at - timezone.now()).total_seconds()
            )

            raise OTPStillActiveError(
                retry_after=max(remaining_seconds, 1),
            )

        current_otp.delete()

    raw_code = f"{secrets.randbelow(1_000_000):06d}"

    otp = PasswordResetOTP(
        user=locked_user,
    )

    otp.set_code(raw_code)
    otp.save()

    return otp, raw_code


def request_password_reset(identifier):
    user = User.objects.filter(
        identifier=identifier,
    ).first()

    if user is None:
        return

    otp, raw_code = create_password_reset_otp(user)

    # send_otp(...)
    print(raw_code)


class InvalidOTPError(Exception):
    def __init__(self):
        super().__init__("کد تأیید نامعتبر است.")


class ExpiredOTPError(Exception):
    def __init__(self):
        super().__init__("کد تأیید منقضی شده است.")


class LockedOTPError(Exception):
    def __init__(self):
        super().__init__("تعداد تلاش‌های مجاز به پایان رسیده است.")


@transaction.atomic
def verify_password_reset_otp(identifier, raw_code):
    user = User.objects.filter(
        identifier=identifier,
    ).first()

    if user is None:
        raise InvalidOTPError()

    otp = PasswordResetOTP.objects.select_for_update().filter(user=user).first()

    if otp is None:
        raise InvalidOTPError()

    if otp.is_expired:
        raise ExpiredOTPError()

    if otp.is_locked:
        raise LockedOTPError()

    if not otp.check_code(raw_code):
        otp.failed_attempts += 1
        otp.save(update_fields=["failed_attempts"])

        raise InvalidOTPError()

    reset_token = issue_password_reset_token(
        user=user,
        otp=otp,
    )

    return reset_token

@transaction.atomic
def reset_user_password(*, user, otp, new_password):
    user.set_password(new_password)
    user.save(update_fields=["password"])

    otp.delete()

    return issue_tokens_for_user(user)