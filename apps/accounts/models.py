from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from .managers import UserManager
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


class User(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(
        max_length=150,
    )
    identifier = models.CharField(
        max_length=254,
        unique=True,
    )
    is_active = models.BooleanField(
        default=True,
    )
    is_staff = models.BooleanField(
        default=False,
    )
    objects = UserManager()

    USERNAME_FIELD = "identifier"
    REQUIRED_FIELDS = ["name"]

    def __str__(self) -> str:
        return self.identifier


class PasswordResetOTP(models.Model):
    TTL = timedelta(minutes=2)
    MAX_FAILED_ATTEMPTS = 5

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_otp",
    )

    code_hash = models.CharField(
        max_length=128,
    )

    failed_attempts = models.PositiveSmallIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def set_code(self, raw_code: str) -> None:
        self.code_hash = make_password(raw_code)

    def check_code(self, raw_code: str) -> bool:
        return check_password(
            raw_code,
            self.code_hash,
        )

    @property
    def expires_at(self):
        return self.created_at + self.TTL

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_locked(self) -> bool:
        return self.failed_attempts >= self.MAX_FAILED_ATTEMPTS

    @property
    def is_usable(self) -> bool:
        return not self.is_expired and not self.is_locked

    def __str__(self) -> str:
        return f"Password reset OTP for " f"{self.user.identifier}"
